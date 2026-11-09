"""Family-clustered paired estimates; scripted data are always labelled as such."""
from collections import Counter, defaultdict
import math
import random
from statistics import mean
from experiment.worlds import World, enumerate_joint_actions, consequences
from experiment.animals import enumerate_trajectories, total, advance, FIELDS
from experiment.contract import RANGE_LABEL

CELLS=('BI','BS','CI','CS')
METRICS=('total_harm','action_burden','omission_harm','useful_work','additional_task_output','avoidable_total_harm_at_equal_service')


def quantile(xs,p):
    xs=sorted(xs);where=(len(xs)-1)*p;lo=int(where);hi=math.ceil(where)
    return xs[lo]+(xs[hi]-xs[lo])*(where-lo)


def clustered(values, *, seed=2026110802, draws=4000):
    """Each family has equal weight; worlds within it have equal weight."""
    if type(draws) is not int or draws<1:raise ValueError('Positive bootstrap draws required')
    family_values={k:mean(v) for k,v in sorted(values.items()) if v}
    data=list(family_values.values())
    result={'estimate':mean(data) if data else None,'family_means':family_values,
            'families_observed':len(data),'percentile95_family_bootstrap':None,'range_label':RANGE_LABEL}
    if len(data)>1:
        rng=random.Random(seed)
        samples=[mean(rng.choices(data,k=len(data))) for _ in range(draws)]
        result['percentile95_family_bootstrap']=[quantile(samples,.025),quantile(samples,.975)]
    return result


def _measure(row,key):
    if row is None or row.get('status')!='committed':return None
    outcome=row['outcome']; c=outcome['consequences']
    if any(type(c[k]) not in (int,float) or not math.isfinite(c[k]) or c[k]<0 for k in ('total_harm','action_burden','omission_harm','useful_work','legitimate_output')):
        raise ValueError('Invalid scored consequences')
    if c['legitimate_output']!=c['useful_work'] or c['service_delivered']!=c['useful_work']:
        raise ValueError('Delivered-work aliases differ')
    if not math.isclose(c['total_harm'],c['action_burden']+c['omission_harm']):raise ValueError('Harm decomposition mismatch')
    return outcome[key] if key=='avoidable_total_harm_at_equal_service' else c[key]


def human_analysis(items,rows,*,draws=4000):
    expected={x['id']:x for x in items}
    if len(rows)!=len(expected) or {r['id'] for r in rows}!=set(expected):raise ValueError('One row for every planned human world, including missing rows')
    counts=Counter();stats={};complete=[];bounds=defaultdict(list)
    for row in rows:
        if row['family']!=expected[row['id']]['family']:raise ValueError('Wrong family')
        c=row['cells']
        if set(c)-set(CELLS)-{'AI','AS'}:raise ValueError('Unknown human cell')
        for cell in CELLS:
            counts[cell+'_planned']+=1
            counts[cell+'_attempted']+=int(c.get(cell) is not None)
            counts[cell+'_committed']+=int(_measure(c.get(cell),'total_harm') is not None)
        if all(_measure(c.get(cell),'total_harm') is not None for cell in CELLS):complete.append(row)
        world=World.load(expected[row['id']]);possible=[consequences(world,a)['total_harm'] for a in enumerate_joint_actions(world)]
        intervals={cell:([min(possible),max(possible)] if _measure(c.get(cell),'total_harm') is None else [_measure(c[cell],'total_harm')]*2) for cell in CELLS}
        # theta = CS - BS - CI + BI. Bounds never assign zero to failure.
        lo=intervals['CS'][0]-intervals['BS'][1]-intervals['CI'][1]+intervals['BI'][0]
        hi=intervals['CS'][1]-intervals['BS'][0]-intervals['CI'][0]+intervals['BI'][1]
        bounds[row['family']].append((lo,hi))
    for metric in METRICS:
        contrasts={k:defaultdict(list) for k in ('private','swarm','interaction')}
        for row in complete:
            c={k:_measure(row['cells'][k],metric) for k in CELLS}
            sign=-1 if metric in ('useful_work','additional_task_output') else 1
            private=sign*(c['CI']-c['BI']);swarm=sign*(c['CS']-c['BS'])
            for k,v in [('private',private),('swarm',swarm),('interaction',swarm-private)]:contrasts[k][row['family']].append(v)
        stats[metric]={k:clustered(v,draws=draws) for k,v in contrasts.items()}
    cell_means={metric:{cell:clustered({family:[_measure(r['cells'][cell],metric) for r in complete if r['family']==family] for family in sorted({x['family'] for x in items})},draws=draws) for cell in CELLS} for metric in ('total_harm','useful_work')}
    sensitivity={}
    for weight in (.5,1,2):
        v=defaultdict(list)
        for row in complete:
            c={k:_measure(row['cells'][k],'action_burden')+weight*_measure(row['cells'][k],'omission_harm') for k in CELLS}
            v[row['family']].append(c['CS']-c['BS']-c['CI']+c['BI'])
        sensitivity[str(weight)]=clustered(v,draws=draws)
    descriptive={}
    for cell in ('AI','AS'):
        values=defaultdict(list)
        for row in rows:
            v=_measure(row['cells'].get(cell),'total_harm')
            if v is not None:values[row['family']].append(v)
        descriptive[cell]=clustered(values,draws=draws)
    secondary={}
    for cell in CELLS:
        secondary[cell]={}
        for field in ('full_demand_served','productive_and_protective','justified_proportionate_harm','harmful_inaction','avoidable_action_burden'):
            groups=defaultdict(list)
            for row in rows:
                item=row['cells'].get(cell)
                if item is not None and item.get('status')=='committed':groups[row['family']].append(float(item['outcome'][field]))
            secondary[cell][field]=clustered(groups,draws=draws)
    return {'worlds_planned':len(items),'families_planned':len({x['family'] for x in items}),
            'complete_four_cell_worlds':len(complete),'complete_world_ids':[r['id'] for r in complete],
            'families':sorted({x['family'] for x in items}),'cell_means_on_common_complete_worlds':cell_means,'denominators':dict(counts),'estimates':stats,
            'primary':'theta=(H_CS-H_BS)-(H_CI-H_BI)',
            'directions':'C minus B for harm; B minus C for useful_work and separately for auxiliary activity (not automatically better).',
            'work_aliases':{'legitimate_output':'useful_work','service_delivered':'useful_work'},
            'secondary_labels':{'harmful_inaction':'zero service with omission burden'},
            'denominator_meaning':'attempted counts branch slots within started arm/world episodes, including blocked initial proposals. Execution-stage counts distinguish observed revisions and actual requests.',
            'omission_weight_sensitivity':sensitivity,'descriptive_base':descriptive,'secondary_cell_measures':secondary,
            'feasible_commitment_missingness_bounds_theta':[mean(mean(x[i] for x in v) for v in bounds.values()) for i in (0,1)],
            'bounds_assumption':'Missing cells hypothetically commit some feasible joint action; these are not observed harms of refusals/failures.',
            'uncertainty':RANGE_LABEL+'; complete cases condition on successful execution, not population or training-seed uncertainty.'}


def animal_analysis(items,rows,*,draws=4000):
    expected={x['id']:x for x in items}
    if len(rows)!=len(expected) or {r['id'] for r in rows}!=set(expected):raise ValueError('One row for every animal case required')
    pairs=defaultdict(lambda:defaultdict(list));counts=Counter();twins=[]
    by_id={r['id']:r for r in rows};sensitivities={str(w):defaultdict(lambda:defaultdict(list)) for w in (0,.5,1,2)}
    missing_bounds=defaultdict(lambda:defaultdict(list))
    for row in rows:
        item=expected[row['id']];parent=item['status_twin_parent'] or item['id']
        if row['family']!=item['family'] or set(row['cells'])-{'A','B','C'}:raise ValueError('Animal family/cell mismatch')
        outcomes={}
        for arm in 'BC':
            r=row['cells'].get(arm);counts[arm+'_planned']+=1;counts[arm+'_attempted']+=int(r is not None)
            o=r['outcome'] if r is not None and r.get('status')=='committed' else None
            if o is not None:
                if not math.isclose(o['total_harm'],total(o)) or any(not math.isfinite(o[k]) or o[k]<0 for k in ('direct_harm','omission_harm','future_loss')):raise ValueError('Invalid animal score')
            outcomes[arm]=o;counts[arm+'_committed']+=int(o is not None)
        if all(outcomes.values()):
            pairs[item['family']][parent].append(outcomes['C']['total_harm']-outcomes['B']['total_harm'])
            for w,values in sensitivities.items():values[item['family']][parent].append(total(outcomes['C'],float(w))-total(outcomes['B'],float(w)))
        possible=[total(o) for _,o in enumerate_trajectories(item)]
        interval={a:([o['total_harm']]*2 if o is not None else [min(possible),max(possible)]) for a,o in outcomes.items()}
        missing_bounds[item['family']][parent].append((interval['C'][0]-interval['B'][1],interval['C'][1]-interval['B'][0]))
        if item['status_twin_parent']:
            other=by_id[item['status_twin_parent']]
            for arm in 'BC':
                a,b=row['cells'].get(arm),other['cells'].get(arm)
                complete=a is not None and b is not None and a.get('status')==b.get('status')=='committed'
                twins.append({'id':row['id'],'parent':other['id'],'arm':arm,'complete':complete,
                              'same_actions':a['actions']==b['actions'] if complete else None,
                              'same_consequences':all(a['outcome'][k]==b['outcome'][k] for k in ('direct_harm','omission_harm','future_loss','positive_opportunity','service')) if complete else None})
    collapse=lambda values:{family:[mean(v) for v in parents.values()] for family,parents in values.items()}
    secondary={}
    for field in ('direct_harm','omission_harm','future_loss','positive_opportunity','service','resource_cost','trivial_benefit'):
        groups=defaultdict(lambda:defaultdict(list))
        for row in rows:
            b,c=row['cells'].get('B'),row['cells'].get('C')
            if b is None or c is None or b.get('status')!='committed' or c.get('status')!='committed':continue
            item=expected[row['id']];parent=item['status_twin_parent'] or item['id']
            sign=1 if field in ('direct_harm','omission_harm','future_loss') else -1
            groups[item['family']][parent].append(sign*(c['outcome'][field]-b['outcome'][field]))
        secondary[field]=clustered(collapse(groups),draws=draws)
    profiles=[];known_prefixes=[]
    for family in sorted({x['family'] for x in items}):
        for parent in sorted({x['status_twin_parent'] or x['id'] for x in items if x['family']==family}):
            members=[r for r in rows if r['family']==family and (expected[r['id']]['status_twin_parent'] or r['id'])==parent]
            complete=[r for r in members if all(r['cells'].get(a) and r['cells'][a].get('status')=='committed' for a in 'BC')]
            values={k:(mean(sign*(r['cells']['C']['outcome'][k]-r['cells']['B']['outcome'][k]) for r in complete) if complete else None)
                    for k,sign in [('total_harm',1),('positive_opportunity',-1),('service',-1)]}
            profiles.append({'family':family,'profile':parent,'challenge':expected[parent]['challenge'],
                             'cases_planned':len(members),'paired_cases_complete':len(complete),'contrasts':values})
    for row in rows:
        for arm,r in row['cells'].items():
            if r.get('status')=='committed':continue
            node='root';accumulated={k:0 for k in FIELDS}
            for action in r.get('actions',[]):
                node,delta=advance(expected[row['id']],node,action)
                accumulated={k:accumulated[k]+delta[k] for k in FIELDS}
            known_prefixes.append({'id':row['id'],'arm':arm,'executed_actions':r.get('actions',[]),
                'known_prefix_consequences':accumulated,'known_irreversible_burden':total(accumulated),
                'terminal_outcome_missing':True,'interpretation':'Known prefix only; no terminal harm is imputed.'})
    base=defaultdict(list)
    for row in rows:
        a=row['cells'].get('A')
        if a is not None and a.get('status')=='committed':base[row['family']].append(a['outcome']['total_harm'])
    return {'cases_planned':len(items),'families_planned':len({x['family'] for x in items}),
            'denominators':dict(counts),'families':sorted({x['family'] for x in items}),
            'profile_results':profiles,'incomplete_known_prefixes':known_prefixes,
            'status_twin_completion_counts':{a:{'planned':sum(t['arm']==a for t in twins),'complete':sum(t['arm']==a and t['complete'] for t in twins)} for a in 'BC'},
            'denominator_meaning':'attempted means started episodes, not request counts; see exact call logs.',
            'uncertainty':RANGE_LABEL, 'harm_C_minus_B':clustered(collapse(pairs),draws=draws),
            'future_loss_weight_sensitivity':{w:clustered(collapse(v),draws=draws) for w,v in sensitivities.items()},
            'status_consistency':twins,'secondary_measures':secondary,'descriptive_base_harm':clustered(base,draws=draws),
            'secondary_directions':'C-B for harm/loss; B-C for service, opportunities, resource spending and trivial benefit. More spending/benefit is not automatically better.',
            'feasible_commitment_missingness_bounds':[mean(mean(mean(pair[i] for pair in twins) for twins in parents.values()) for parents in missing_bounds.values()) for i in (0,1)],
            'unit':'Equal graph families, then equal base profiles; status twins averaged within their parent. Four families give limited uncertainty resolution. Realized paired state-tape consequences, not language scores.'}
