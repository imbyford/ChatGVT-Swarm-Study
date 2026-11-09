"""Exact v0.3 V/N/U scheduler; real execution needs separate bound approval."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,json,os
import experiment
from model_client import Completion
from experiment.permissions import require_operation
from integration.draft import load,canonical,digest,scoring,prompts,request_for,parse
from integration.bindings import verify_candidate

class ScriptedAgent:
    def __init__(self,faults=None):self.faults=faults or {}
    def complete(self,slot,request):
        if slot['request_id'] in self.faults:
            value=self.faults[slot['request_id']]
            if isinstance(value,Exception):raise value
            return value
        body=json.loads(request['messages'][1]['content']);facts=body['common_facts']
        if 'your_role' in body:
            role=next(r for r in facts['roles'] if r['id']==body['your_role'])
            return canonical({'action':role['actions'][0]['id'],'reason':'SCRIPTED ENGINEERING ONLY'})
        menu=facts['nodes'][body['current_node']]['actions'];ids=[a['id'] for a in menu]
        # Exercise a child when available; never reads a private answer key.
        selected=next((a['id'] for a in menu if any(e.get('next') for e in a['by_state'].values())),ids[0])
        return canonical({'status':'commit','action':selected,'judgment':{'permitted':ids,'required':[],'recommended':[selected],'unresolved':[]},'factual_action':ids[0],'reason':'SCRIPTED ENGINEERING ONLY'})


def execute(agent,splits=None,mode='scripted',emit=None):
    if mode not in ('scripted','real'):raise ValueError('Unknown execution mode')
    if mode=='real':
        require_operation('live_inference')
        if splits is not None:raise ValueError('Live release requires the complete frozen schedule')
        if not getattr(agent,'validated_live',False):raise ValueError('Real mode requires the validated reference agent')
    data=load();slots=[s for s in data['slots'] if splits is None or s['split'] in splits]
    if len({s['request_id'] for s in slots})!=len(slots):raise ValueError('Duplicate slot')
    initial=defaultdict(dict);final=defaultdict(dict);animal_state={};frozen={};done={};events=[];calls=0;reserved=0
    for c in data['animal']:
        for a in ('V','N','U'):animal_state[(c,a)]={'root_done':False,'node':'root','actions':{},'history':[]}
    def record(event):
        event={'seq':len(events),**event};events.append(event)
        if emit:emit(event)
    identities=getattr(agent,'identities',{a:'SCRIPTED_ONLY_'+a for a in ('V','N','U')})
    live={}
    if mode=='real':
        from integration.frozen import live_header
        live=live_header(identities)
    record({'event':'header','study':'study2-vnu','mode':mode,'empirical_treatment_results':False,'splits':sorted(set(s['split'] for s in slots)),
        'slots_sha256':digest(slots),'request_ceiling':len(slots),'output_token_ceiling':sum(s['max_output_tokens'] for s in slots),
        'source':'Exact evaluator candidate v0.3; additive focused AI closure; no live approval',
        'evaluation_binding':verify_candidate(),'inference_identities':identities,**live})
    def eligible(s):
        key=(s['case_id'],s['arm'])
        if s['split'].startswith('human'):
            if s['phase']=='initial':return 'call'
            if len(initial[key])<3:return None
            if any(v['status']!='valid' for v in initial[key].values()):return 'initial_dependency_failure'
            return 'call'
        if s['phase']=='root':return 'call'
        state=animal_state[key]
        if not state['root_done']:return None
        if state['node'] is None:return 'no_continuation_after_root'
        if state['node']=='root':return 'invalid_or_noncommit_root'
        return 'call'
    while len(done)<len(slots):
        ready=[s for s in slots if s['request_id'] not in done and eligible(s) is not None]
        if not ready:raise ValueError('Dependency deadlock')
        slot=min(ready,key=lambda s:(s['proposed_order_key'],s['request_id']));sid=slot['request_id'];why=eligible(slot);key=(slot['case_id'],slot['arm'])
        if why!='call':
            done[sid]={'status':'unstarted','cause':why};record({'event':'unstarted','slot':slot,'cause':why});continue
        if slot['split'].startswith('human') and slot['phase']!='initial' and key not in frozen:
            c=data['human'][slot['case_id']];frozen[key]=prompts.freeze_proposals(c,{r:v['parsed'] for r,v in initial[key].items()})
            record({'event':'frozen_proposals','case_id':key[0],'arm':key[1],**frozen[key]})
        request=request_for(slot,data,initial,animal_state);calls+=1;reserved+=slot['max_output_tokens']
        record({'event':'request_intent','slot':slot,'request':request,'request_sha256':digest(request),'selected_identity':identities[slot['arm']],'request_number':calls,'reserved_output_tokens':reserved})
        raw=None;usage=None;error=None;node=animal_state[key]['node'] if key in animal_state else None
        try:
            reply=agent.complete(slot,request)
            if isinstance(reply,Completion):
                raw=reply.text;usage={'input':reply.input_tokens,'output':reply.output_tokens,'audit':reply.audit}
                if reply.status is not None:result={'status':reply.status,'parsed':None,'error':reply.error}
                elif reply.input_tokens is None or reply.output_tokens is None:raise RuntimeError('Missing usage')
                else:result=parse(slot,data,raw,node)
            else:raw=reply;result=parse(slot,data,raw,node)
        except (TimeoutError,OSError) as exc:result={'status':'transport_failure','parsed':None,'error':type(exc).__name__}
        record({'event':'response','request_id':sid,'raw_response':raw,'response_sha256':None if raw is None else digest(raw),**result,'usage':usage,'retries':0})
        done[sid]=result
        if slot['split'].startswith('human'):
            if slot['phase']=='initial':initial[key][slot['role']]=result
            else:final[(slot['case_id'],slot['arm'],slot['phase'])][slot['role']]=result
        else:
            state=animal_state[key];c=data['animal'][slot['case_id']]
            if slot['phase']=='root':state['root_done']=True
            if result['status']=='valid':
                parsed=result['parsed'];metrics=scoring.animal_response_score(c,node,parsed,data['keys'][c['id']])
                record({'event':'private_animal_measurement','request_id':sid,'case_id':c['id'],'family':c['family'],'arm':slot['arm'],'node':node,'metrics':metrics})
                if parsed['status']=='commit':
                    a=next(a for a in c['nodes'][node]['actions'] if a['id']==parsed['action']);edge=a['by_state'][c['tape_state']]
                    state['actions'][node]=parsed['action'];state['history'].append({'node':node,'action':parsed['action'],'observed_consequences':edge['consequences']});state['node']=edge.get('next')
                    record({'event':'animal_commit','request_id':sid,'node':node,'action':parsed['action'],'increment':edge['consequences']})
    human={};animals={};cells=[]
    for cid,c in data['human'].items():
        if not any(s['case_id']==cid for s in slots):continue
        human[cid]={}
        for arm in ('V','N','U'):
            for phase in ('I','S'):
                values=final[(cid,arm,phase)];valid=len(values)==3 and all(v['status']=='valid' for v in values.values())
                joint=[scoring.parse_human(c,r['id'],values[r['id']]['parsed']) for r in c['roles']] if valid else None
                human[cid][arm+phase]=joint
                row={'event':'human_commit' if valid else 'human_missing','case_id':cid,'arm':arm,'condition':phase,'joint':joint,
                    'metrics':None if joint is None else scoring.human_row(c,joint),'frozen_sha256':frozen.get((cid,arm),{}).get('sha256')};record(row);cells.append(row)
    for cid,c in data['animal'].items():
        if not any(s['case_id']==cid for s in slots):continue
        animals[cid]={a:animal_state[(cid,a)]['actions'] for a in ('V','N','U')}
        for a,actions in animals[cid].items():record({'event':'animal_outcome','case_id':cid,'arm':a,**scoring.animal_trace(c,actions,c['tape_state'])})
    counts={split:{'planned':sum(s['split']==split for s in slots),'started':sum(s['split']==split and done[s['request_id']]['status']!='unstarted' for s in slots),
        'valid':sum(s['split']==split and done[s['request_id']]['status']=='valid' for s in slots),'unstarted':sum(s['split']==split and done[s['request_id']]['status']=='unstarted' for s in slots)} for split in sorted({s['split'] for s in slots})}
    record({'event':'complete','attempted_requests':calls,'reserved_output_tokens':reserved,'counts':counts})
    return {'mode':mode,'empirical_treatment_results':mode=='real','human_commitments':human,'animal_trajectories':animals,'counts':counts,'attempted_requests':calls,'reserved_output_tokens':reserved},events


def replay(events):
    if not events or events[0].get('mode') not in ('scripted','real'):raise ValueError('Invalid ledger mode')
    intents=[e for e in events if e['event']=='request_intent'];responses=[e for e in events if e['event']=='response'];index=0
    if len(intents)!=len(responses):raise ValueError('Incomplete intent/response evidence')
    class Recorded:
        identities=events[0]['inference_identities']
        def complete(self,slot,request):
            nonlocal index
            if index>=len(intents) or slot!=intents[index]['slot'] or request!=intents[index]['request']:raise ValueError('Replay request/schedule differs')
            response=responses[index];index+=1
            if response['request_id']!=slot['request_id']:raise ValueError('Wrong response binding')
            if response['status']=='transport_failure':
                if response['error']=='TimeoutError':raise TimeoutError('Recorded failure')
                raise OSError('Recorded failure')
            if response['usage'] is not None:
                u=response['usage'];status=None if response['status'] in ('valid','invalid') else response['status']
                return Completion(response['raw_response'],status,response['error'],u['input'],u['output'],u['audit'])
            return response['raw_response']
    result,reproduced=execute(Recorded(),splits=events[0]['splits'])
    if events[0]['mode']=='real':
        from integration.frozen import live_header
        reproduced[0].update(live_header(events[0]['inference_identities']))
        result.update(mode='real',empirical_treatment_results=True)
    if canonical(events)!=canonical(reproduced) or index!=len(intents):raise ValueError('Exact ledger replay differs')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=['scripted','real'],default='scripted');p.add_argument('--split',action='append',choices=['human_development','human_protected','animal_development','animal_protected']);p.add_argument('--scripted-reference',action='store_true');a=p.parse_args()
    if a.mode!='scripted':raise ValueError('Use python -m tools.run_evaluation for approved real execution; this CLI is scripted only')
    a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    agent=ScriptedAgent()
    if a.scripted_reference:
        from integration.reference_bridge import ReferenceAgent
        agent=ReferenceAgent.offline()
    with (a.output/'ledger.jsonl').open('x') as f:
        def emit(e):f.write(canonical(e)+'\n');f.flush();os.fsync(f.fileno())
        result,events=execute(agent,a.split,emit=emit)
    assert replay(events)==result
    (a.output/'run.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'scripted_requests':result['attempted_requests'],'exact_replay':True,'model_calls':0}))
if __name__=='__main__':main()
