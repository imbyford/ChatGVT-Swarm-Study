"""Bind actual evaluator source/data; whitelist model-facing payloads."""
from pathlib import Path
from copy import deepcopy
import hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1];DRAFT=ROOT/'evaluation/candidate_v0.3'

def load_module(name,file):
    if name in sys.modules:
        m=sys.modules[name]
        if Path(m.__file__).resolve()!=(DRAFT/'source'/file).resolve():raise RuntimeError('Conflicting evaluator module')
        return m
    spec=importlib.util.spec_from_file_location(name,DRAFT/'source'/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
scoring=load_module('scoring','scoring.py');prompts=load_module('draft_prompts','prompts.py');analysis=load_module('draft_analysis','analysis.py')
read=lambda p:json.loads((DRAFT/p).read_text())
canonical=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
digest=lambda x:hashlib.sha256((x if isinstance(x,str) else canonical(x)).encode()).hexdigest()

def load():
    from integration.bindings import verify_candidate
    verify_candidate()
    human=read('model_facing/development/human_development.json')+read('model_facing/protected_draft/human_protected.json')
    animal=read('private/animal_source_with_tapes.json')
    return {'human':{x['id']:x for x in human},'animal':{x['id']:x for x in animal},'registry':read('private/family_split_registry.json'),'keys':read('private/animal_keys.json'),'slots':read('protocol/request_slots.json')}

def human_public(case):
    c={k:deepcopy(case[k]) for k in ('id','family','mechanism','scenario','rules','parameters','roles')}
    c['parameters']={k:deepcopy(case['parameters'][k]) for k in ('demand','omission_weight','consequence_table','service_floor','protection_limit','variant')}
    c['parameters']['consequence_table']={k:{f:v[f] for f in ('service','direct','interaction','auxiliary')} for k,v in c['parameters']['consequence_table'].items()}
    c['roles']=[{'id':r['id'],'module':r['module'],'actions':[{k:a[k] for k in ('id','value','description')} for a in r['actions']]} for r in c['roles']]
    return c

def animal_public(case):
    # Use only declared case fields; private keys/metadata never enter prompts.
    c={k:deepcopy(case[k]) for k in ('id','family','challenge','status_twin_parent','status_label','scenario','scoring_assumptions','latent_states','prior','tape_state','service_floor','nodes','split')}
    c['nodes']={n:{'observation':v['observation'],'factual_probe':v['factual_probe'],
        'actions':[{k:a[k] for k in ('id','description','by_state')} for a in v['actions']]} for n,v in c['nodes'].items()}
    for node in c['nodes'].values():
        for action in node['actions']:
            action['by_state']={state:{k:deepcopy(edge[k]) for k in ('consequences','next') if k in edge} for state,edge in action['by_state'].items()}
            for edge in action['by_state'].values():
                edge['consequences']={k:edge['consequences'][k] for k in scoring.FIELDS}
    return c

def request_for(slot,data,initial,animal_state):
    if slot['split'].startswith('human'):
        c=data['human'][slot['case_id']];key=(slot['case_id'],slot['arm']);phase=slot['phase'];own=peers=None
        if phase!='initial':
            actions={r:v['parsed']['action'] for r,v in initial[key].items()};own=actions[slot['role']]
            if phase=='S':peers={r:a for r,a in actions.items() if r!=slot['role']}
        payload=prompts.human_request(human_public(c),slot['role'],phase,own,peers)
    else:
        c=data['animal'][slot['case_id']];state=animal_state[(slot['case_id'],slot['arm'])]
        node='root' if slot['phase']=='root' else state['node'];history=[] if slot['phase']=='root' else state['history']
        payload=prompts.animal_request(animal_public(c),node,history)
    return {'messages':[{'role':'system','content':payload['system']},{'role':'user','content':payload['user']}],
        'temperature':0,'top_p':1,'seed':20261107,'max_completion_tokens':slot['max_output_tokens'],
        'chat_template_kwargs':{'enable_thinking':False},'stream':False,'n':1}

def parse(slot,data,raw,node=None):
    try:
        obj=scoring.parse_json_strict(raw)
        if slot['split'].startswith('human'):scoring.parse_human(data['human'][slot['case_id']],slot['role'],obj)
        else:scoring.parse_animal(data['animal'][slot['case_id']],node or 'root',obj)
        return {'status':'valid','parsed':obj,'error':None}
    except (ValueError,TypeError,KeyError) as e:return {'status':'invalid','parsed':None,'error':type(e).__name__+': '+str(e)}
