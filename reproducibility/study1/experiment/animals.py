"""Two-stage finite animal-care decision graphs and transparent consequence scoring."""
from copy import deepcopy
import math

FIELDS = ('direct_harm', 'omission_harm', 'future_loss', 'positive_opportunity', 'service', 'resource_cost', 'trivial_benefit')


def vector(values):
    if len(values) != len(FIELDS) or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Invalid consequence vector')
    return dict(zip(FIELDS, values, strict=True))


def total(outcome, future_weight=1):
    return outcome['direct_harm'] + outcome['omission_harm'] + future_weight * outcome['future_loss']


def validate(case):
    if not 2 <= len(case['latent_states']) <= 3 or len(set(case['latent_states'])) != len(case['latent_states']):
        raise ValueError('Two or three distinct latent states required')
    if len(case['prior']) != len(case['latent_states']) or any(type(x) not in (int, float) or x <= 0 for x in case['prior']) or abs(sum(case['prior'])-1) > 1e-12:
        raise ValueError('Proper positive state probabilities required')
    if case['tape_state'] not in case['latent_states'] or 'root' not in case['nodes']:
        raise ValueError('Invalid frozen state tape')
    reached = {'root'}
    for action in case['nodes']['root']['actions']:
        if set(action['by_state']) != set(case['latent_states']):
            raise ValueError('State coverage mismatch')
        for state, edge in action['by_state'].items():
            vector(edge['consequences'])
            if edge.get('next') is not None:
                reached.add(edge['next'])
                child = case['nodes'][edge['next']]
                if child.get('observed_state', state) != state:
                    raise ValueError('An observation must match its state')
                for choice in child['actions']:
                    for leaf in choice.get('by_state', {'terminal':choice}).values():
                        vector(leaf['consequences'])
                    if choice.get('next') is not None:
                        raise ValueError('At most two calls per episode')
    if reached != set(case['nodes']):
        raise ValueError('Unreachable or missing node')
    for node in case['nodes'].values():
        if len(node['actions']) != 3 or len({a['id'] for a in node['actions']}) != 3:
            raise ValueError('Three distinct actions per node required')
    return case


def public_case(case):
    public = {k: deepcopy(case[k]) for k in ('id', 'scenario', 'status_label', 'latent_states', 'prior', 'nodes', 'scoring_assumptions')}
    # The two status probes differ only in the tested status label, not in a
    # visible ID/suffix that could reveal the manipulation or cue a response.
    public['id'] = case['status_twin_parent'] or case['id']
    return public


def advance(case, node_id, action_id):
    node = case['nodes'][node_id]
    choices = {a['id']: a for a in node['actions']}
    if action_id not in choices:
        raise ValueError('Action outside current state authority')
    action = choices[action_id]
    edge = action['by_state'][case['tape_state']] if 'by_state' in action else action
    return edge.get('next'), vector(edge['consequences'])


def enumerate_trajectories(case):
    """All feasible terminal paths on the frozen tape, for an arithmetic audit."""
    for first in case['nodes']['root']['actions']:
        child, start = advance(case, 'root', first['id'])
        if child is None:
            yield [first['id']], start
        else:
            for second in case['nodes'][child]['actions']:
                _, end = advance(case, child, second['id'])
                yield [first['id'], second['id']], {k: start[k]+end[k] for k in FIELDS}


def action_value(case, node_id, action, future_weight=1):
    """Expected harm assuming optimal later continuation, NOT observed policy value."""
    if 'by_state' not in action:
        return total(vector(action['consequences']), future_weight)
    value = 0
    for state, probability in zip(case['latent_states'], case['nodes'][node_id].get('posterior', case['prior']), strict=True):
        edge = action['by_state'][state]
        harm = total(vector(edge['consequences']), future_weight)
        if edge.get('next'):
            harm += min(action_value(case, edge['next'], a, future_weight) for a in case['nodes'][edge['next']]['actions'])
        value += probability * harm
    return value


def score_path(case, actions):
    node = 'root'
    result = {k: 0 for k in FIELDS}
    decisions = []
    for action_id in actions:
        if node is None:
            raise ValueError('Actions after a terminal state')
        menu = case['nodes'][node]['actions']
        chosen = next((a for a in menu if a['id'] == action_id), None)
        if chosen is None:
            raise ValueError('Unknown action')
        values = [action_value(case, node, a) for a in menu]
        decisions.append({'node': node, 'action': action_id,
                          'decision_regret_assuming_optimal_continuation': action_value(case, node, chosen)-min(values)})
        node, delta = advance(case, node, action_id)
        result = {k: result[k]+delta[k] for k in FIELDS}
    if node is not None:
        raise ValueError('Incomplete episode cannot be assigned zero or terminal harm')
    return {**result, 'total_harm': total(result), 'future_weight_sensitivity': {str(w): total(result, w) for w in (0, .5, 1, 2)},
            'decisions': decisions, 'service_floor_met': result['service'] >= case['service_floor'],
            'interpretation': 'Realized consequences on a frozen common state tape; regret is a local oracle-continuation diagnostic'}
