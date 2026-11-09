"""Single-pass R1 schedule, fresh contexts, durable intents and no automatic resume."""
from collections import defaultdict
import json,os,time
from integration.draft import load,canonical,digest,scoring
from r1 import protocol as p
from r1.extraction import strict,native_choice

def model_ids():
 from integration.frozen import live_routes
 return {a:r.model_id for a,r in live_routes().items()}

def execute(client,emit,mode='scripted',include_fixtures=True):
 data=load();events=[];done={};initial=defaultdict(dict);final=defaultdict(dict);frozen={};animal={};reached=[];used=set();calls=reserved=0;models=model_ids()
 def record(e):
  e={'seq':len(events),**e};events.append(e);emit(e)
 def call(slot,req):
  nonlocal calls,reserved
  sid=slot['request_id']
  if sid in used:raise ValueError('Duplicate/ambiguous request forbidden')
  used.add(sid);calls+=1;reserved+=req['max_completion_tokens']
  if calls>945 or reserved>148608:raise ValueError('Frozen enumerated budget exceeded')
  req={**req,'model':models[slot['arm']]}
  record({'event':'request_intent','slot':slot,'request':req,'request_sha256':digest(req),'request_number':calls,'reserved_output_tokens':reserved})
  # Any technical exception propagates immediately. The durable intent prevents replay as a new call.
  reply=client.complete(slot,req)
  if reply['model']!=req['model']:raise ValueError('Response model mismatch')
  if reply['output_tokens']>req['max_completion_tokens'] or reply['input_tokens']+req['max_completion_tokens']>4096:raise ValueError('Runtime token bound')
  if slot['task']=='native':parsed=native_choice(reply['raw'],reply['finish_reason']);status=parsed['status']
  else:
   if reply['finish_reason']!='stop' or reply['raw'] not in req['r1_allowed_responses']:raise ValueError('Constrained interface violation')
   parsed=strict(reply['raw']);status='valid'
  record({'event':'response','request_id':sid,'reply':reply,'response_sha256':digest(reply['raw']),'status':status,'parsed':parsed,'retries':0})
  return {'status':status,'parsed':parsed,'reply':reply}
 record({'event':'header','mode':mode,'study':'study2-r1','post_result_exploratory':True,'model_ids':models,'max_requests':945,'max_reserved_output_tokens':148608})
 if include_fixtures:
  checked={}
  for slot,req in p.fixtures():checked[slot['request_id']]=call(slot,req)
  for arm in 'VNU':
   if checked[f'fixture/{arm}/0']['reply']['raw']!=checked[f'fixture/{arm}/7']['reply']['raw']:raise ValueError('Neutral repeat stability gate failed')
  record({'event':'fixtures_passed','calls':24,'criteria':'identity, valid complete trie paths, refusal/unresolved reachable, exact neutral repeat; no moral/ranking gate'})
 record({'event':'experimental_collection_begins'})
 slots=[{**s,'task':'physical','max_output_tokens':128} for s in data['slots']]
 for cid in data['animal']:
  for arm in 'VNU':animal[(cid,arm)]={'root_done':False,'node':'root','actions':{},'history':[]}
 def eligible(s):
  key=(s['case_id'],s['arm'])
  if s['split'].startswith('human'):
   if s['phase']=='initial':return 'call'
   if len(initial[key])<3:return None
   if any(x['parsed']['status']!='commit' for x in initial[key].values()):return 'initial_noncommitment_dependency'
   return 'call'
  state=animal[key]
  if s['phase']=='root':return 'call'
  if not state['root_done']:return None
  if state['node'] is None:return 'unvisited_terminal_branch'
  if state['node']=='root':return 'root_noncommitment_dependency'
  return 'call'
 while len(done)<len(slots):
  ready=[s for s in slots if s['request_id'] not in done and eligible(s) is not None]
  if not ready:raise ValueError('Dependency deadlock')
  s=min(ready,key=lambda s:(s['proposed_order_key'],s['request_id']));sid=s['request_id'];key=(s['case_id'],s['arm']);why=eligible(s)
  if why!='call':done[sid]=None;record({'event':'unstarted','slot':s,'cause':why});continue
  if s['split'].startswith('human') and s['phase']!='initial' and key not in frozen:
   actions={r:v['parsed']['action'] for r,v in initial[key].items()};frozen[key]=actions
   record({'event':'frozen_proposals','case_id':key[0],'arm':key[1],'actions':actions,'sha256':digest(actions)})
  req=p.physical(s,data,initial,animal);result=call(s,req);done[sid]=result
  if s['split'].startswith('human'):
   if s['phase']=='initial':initial[key][s['role']]=result
   else:final[(s['case_id'],s['arm'],s['phase'])][s['role']]=result
  else:
   state=animal[key];node=state['node'];reached.append({'slot':s,'request':req,'node':node})
   if s['phase']=='root':state['root_done']=True
   if result['parsed']['status']=='commit':
    action=result['parsed']['action'];c=data['animal'][s['case_id']];edge=next(a for a in c['nodes'][node]['actions'] if a['id']==action)['by_state'][c['tape_state']]
    state['actions'][node]=action;state['history'].append({'node':node,'action':action,'observed_consequences':edge['consequences']});state['node']=edge.get('next')
    record({'event':'animal_commit','request_id':sid,'node':node,'action':action,'increment':edge['consequences']})
 human={};animals={}
 for cid,c in data['human'].items():
  human[cid]={}
  for arm in 'VNU':
   for cond in ('I','S'):
    vals=final[(cid,arm,cond)];joint=None
    if len(vals)==3 and all(v['parsed']['status']=='commit' for v in vals.values()):joint=[next(a['value'] for a in role['actions'] if a['id']==vals[role['id']]['parsed']['action']) for role in c['roles']]
    human[cid][arm+cond]=joint;record({'event':'human_outcome','case_id':cid,'arm':arm,'condition':cond,'joint':joint,'metrics':scoring.human_row(c,joint) if joint is not None else None})
 for cid,c in data['animal'].items():
  animals[cid]={arm:animal[(cid,arm)]['actions'] for arm in 'VNU'}
  for arm in 'VNU':record({'event':'animal_outcome','case_id':cid,'arm':arm,**scoring.animal_trace(c,animals[cid][arm],c['tape_state'])})
 physical={'human_commitments':human,'animal_trajectories':animals}
 record({'event':'physical_schedule_complete','physical_sha256':digest(physical),'reached_animal_nodes':len(reached)})
 if len(reached)>33:raise ValueError('Unexpected auxiliary scope')
 aux=[]
 for node in reached:
  s=node['slot'];ids=[a['id'] for a in json.loads(node['request']['messages'][1]['content'])['common_facts']['nodes'][node['node']]['actions']]
  assert len(ids)==3
  for kind,action in [('factual',None)]+[('policy',x) for x in ids]:
   slot={'task':'auxiliary','request_id':'aux/'+s['request_id']+'/'+kind+('/'+action if action else ''),'arm':s['arm'],'case_id':s['case_id'],'node':node['node'],'split':s['split'],'kind':kind,'action':action,'max_output_tokens':128,'parent_request_id':s['request_id']}
   aux.append((slot,p.auxiliary(node,kind,action)))
 for slot,req in sorted(aux,key=lambda x:(p.order(x[0]['request_id']),x[0]['request_id'])):call(slot,req)
 rows={x['pair_id']:x for x in p.validation_records()}
 for native in (False,True):
  for slot in p.validation_slots(native):call(slot,p.validation_request(rows[slot['row_id']],native))
 record({'event':'complete','attempted_requests':calls,'reserved_output_tokens':reserved,'physical_sha256':digest(physical)})
 return physical,events

class Scripted:
 def __init__(self,fault=None):self.fault=fault
 def complete(self,slot,req):
  options=req['r1_allowed_responses'];raw=options[0] if options else 'Choice: A\nTrade-off: Scripted fixture only.\nReason: Policy status: required. Scripted fixture only.'
  if self.fault:raw=self.fault(slot,req,raw)
  return {'id':'scripted/'+slot['request_id'],'model':req['model'],'raw':raw,'finish_reason':'stop','input_tokens':1,'output_tokens':1,'token_audit':None}

def replay(events):
 intents=[x for x in events if x['event']=='request_intent'];responses=[x for x in events if x['event']=='response'];i=0
 if len(intents)!=len(responses):raise ValueError('Incomplete evidence; no silent resume')
 class Saved:
  def complete(self,slot,req):
   nonlocal i
   e=intents[i];r=responses[i];i+=1
   if e['slot']!=slot or e['request']!=req or r['request_id']!=slot['request_id']:raise ValueError('Replay request/schedule mismatch')
   return r['reply']
 physical,reproduced=execute(Saved(),lambda e:None,mode=events[0]['mode'],include_fixtures=any(e['event']=='fixtures_passed' for e in events))
 if canonical(reproduced)!=canonical(events) or i!=len(intents):raise ValueError('Exact ledger replay mismatch')
 return physical
