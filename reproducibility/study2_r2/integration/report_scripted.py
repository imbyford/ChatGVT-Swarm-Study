"""Replay and analyze offline ledgers; never invokes a model or network client."""
from pathlib import Path
from statistics import mean
from collections import Counter,defaultdict
import argparse,json
from integration.draft import load,scoring,analysis,canonical,digest
from integration.runner import replay
from integration.bindings import verify_candidate, reporting_contract

def add_leave_one_out(value):
    if isinstance(value,dict):
        for x in list(value.values()):add_leave_one_out(x)
        if 'family_means' in value:
            f=value['family_means'];rows={}
            for omit in sorted(f):
                remain={k:v for k,v in f.items() if k!=omit};valid=[v for v in remain.values() if v is not None]
                rows[omit]={'full_remaining_family_mean':mean(valid) if valid and len(valid)==len(remain) else None,
                            'available_remaining_family_mean':mean(valid) if valid else None,'missing_remaining_families':[k for k,v in remain.items() if v is None]}
            value['leave_one_family_out']=rows
    elif isinstance(value,list):
        for x in value:add_leave_one_out(x)

def report(events):
    result=replay(events);data=load();reg=data['registry'];rmap={x['id']:x for x in reg}
    empirical=events[0]['mode']=='real'
    out={'status':'EXPLORATORY_CHECKPOINT_PACKAGE_COMPARISON' if empirical else 'SCRIPTED_ENGINEERING_ONLY_NOT_TREATMENT_RESULTS','empirical_treatment_results':empirical,'exact_replay':True,
         'evaluation_binding':verify_candidate(),'reporting_contract':reporting_contract(),
         'ledger_content_sha256':digest(events),'counts':result['counts'],'human':{},'animal':{},'policy_and_factual':{},'missingness':[]}
    if empirical:out['execution_binding']=events[0]['execution_binding']
    for split in ('human_development','human_protected'):
        out['human'][split]={str(w):analysis.human_analysis(list(data['human'].values()),reg,result['human_commitments'],split,w) for w in (.5,1,2)}
        for w,row in out['human'][split].items():
            row['case_cells']={cid:{cell:scoring.human_row(data['human'][cid],joint,float(w)) if joint is not None else None for cell,joint in cells.items()} for cid,cells in result['human_commitments'].items() if rmap[cid]['split']==split}
            # Every parent/twin is explicitly available for profile-level reporting.
            row['base_profiles']={p:[r['id'] for r in reg if r['split']==split and r['parent_id']==p] for p in sorted({r['parent_id'] for r in reg if r['split']==split})}
    for split in ('animal_development','animal_protected'):
        out['animal'][split]={str(w):analysis.animal_analysis(list(data['animal'].values()),reg,result['animal_trajectories'],split,w) for w in (0,.5,1,2)}
    responses={e['request_id']:e for e in events if e['event']=='response'}
    measurements={e['request_id']:e for e in events if e['event']=='private_animal_measurement'}
    intents={e['slot']['request_id']:e for e in events if e['event']=='request_intent'}
    unstarted={e['slot']['request_id']:e for e in events if e['event']=='unstarted'}
    for s in data['slots']:
        if s['split'] not in result['counts']:continue
        response=responses.get(s['request_id']);miss=unstarted.get(s['request_id'])
        out['missingness'].append({**s,'family':rmap[s['case_id']]['family_group'],'started':response is not None,
            'response_completed':response is not None and response['raw_response'] is not None,
            'valid_response':response is not None and response['status']=='valid','status':response['status'] if response else 'unstarted',
            'cause':response['error'] if response else (miss or {}).get('cause','interrupted'),
            'usage':None if response is None else response['usage']})
    components=['factual','choice_permitted','choice_required','choice_recommended','classification.permitted','classification.required','classification.recommended','classification.unresolved_set_exact']
    for split in ('animal_development','animal_protected'):
        subreg=[r for r in reg if r['split']==split];ids={r['id'] for r in subreg};families=sorted({r['family_group'] for r in subreg});block={}
        for arm in ('V','N','U'):
            targets=[arm] if arm!='U' else ['V','N'];armout={}
            for target in targets:
                values=defaultdict(dict);node_rows=[]
                for cid in sorted(ids):
                    gathered=defaultdict(list)
                    for node in data['animal'][cid]['nodes']:
                        slots=[s for s in data['slots'] if s['case_id']==cid and s['arm']==arm and s['phase']==('root' if node=='root' else 'continuation')]
                        sid=slots[0]['request_id'] if slots else None
                        measure=measurements.get(sid);metrics=measure['metrics'] if measure and measure['node']==node else None
                        vals={c:None for c in components}
                        if metrics:
                            vals['factual']=metrics['factual'];f=metrics['fidelity'].get(target,{})
                            for c in components[1:]:
                                vals[c]=(f.get('classification') or {}).get(c.split('.')[1]) if c.startswith('classification.') else f.get(c)
                        reached=sid in intents and json.loads(intents[sid]['request']['messages'][1]['content'])['current_node']==node
                        node_rows.append({'case_id':cid,'node':node,'request_started':reached,'valid_response':metrics is not None,'key_target':target,
                            'values':vals,'scoreable_component_counts':{c:int(v is not None) for c,v in vals.items()},'applicability':'Null means unvisited, invalid or unmeasured; empty required/recommended sets are not automatic success.'})
                        for c,v in vals.items():
                            if v is not None:gathered[c].append(v)
                    for c,xs in gathered.items():values[c][cid]=mean(xs)
                armout[target]={'interpretation':'own-policy fidelity' if arm!='U' else 'descriptive agreement; U has no approved own-policy target',
                    'components':{c:{**scoring.equal_family_mean(values[c],subreg,families),'scoreable_nodes':sum(n['scoreable_component_counts'][c] for n in node_rows)} for c in components},'nodes':node_rows}
            block[arm]=armout
        out['policy_and_factual'][split]=block
    add_leave_one_out(out)
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('ledger',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    events=[json.loads(x) for x in a.ledger.read_text().splitlines()];value=report(events)
    with a.output.open('x') as f:f.write(json.dumps(value,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'exact_replay':True,'scripted_only':not value['empirical_treatment_results'],'output':str(a.output)}))
if __name__=='__main__':main()
