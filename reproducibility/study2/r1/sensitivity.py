"""Read-only S1/S2, rescoring only actual transmitted final/history commitments."""
from pathlib import Path
from collections import Counter
import json,hashlib
from integration.draft import load,canonical,digest
from r1.extraction import extract
from r1.analysis import welfare
ROOT=Path(__file__).resolve().parents[1]
def main():
 rules=json.loads((ROOT/'reports/extraction_rules_preanalysis.json').read_text());assert hashlib.sha256((ROOT/'r1/extraction.py').read_bytes()).hexdigest()==rules['code_sha256']
 data=load();events=[json.loads(x) for x in (ROOT/'inputs/original_ledger.jsonl').read_text().splitlines()];intents={e['slot']['request_id']:e for e in events if e['event']=='request_intent'};responses={e['request_id']:e for e in events if e['event']=='response'};allout={'rules':rules,'original_ledger_sha256':hashlib.sha256((ROOT/'inputs/original_ledger.jsonl').read_bytes()).hexdigest(),'interpretation':'Post-hoc deterministic extraction sensitivity, not a replacement or new model run','modes':{}}
 for mode in ('S1','S2'):
  extracted={};rows=[]
  for sid,e in intents.items():
   s=e['slot'];r=responses[sid];body=json.loads(e['request']['messages'][1]['content']);human=s['split'].startswith('human');menu=[a['id'] for role in body['common_facts']['roles'] if role['id']==s['role'] for a in role['actions']] if human else [a['id'] for a in body['common_facts']['nodes'][body['current_node']]['actions']]
   finish=((r.get('usage') or {}).get('audit') or {}).get('finish_reason');result=extract(r['raw_response'],menu,'human' if human else 'animal',mode,r['status'],finish);extracted[sid]=result
   rows.append({**s,'original_status':r['status'],'original_error':r['error'],'original_raw_sha256':r['response_sha256'],'raw':r['raw_response'],'finish_reason':finish,**result})
  human={};animals={}
  for cid,c in data['human'].items():
   human[cid]={}
   for arm in 'VNU':
    for phase in 'IS':
     found=[s for s in data['slots'] if s['case_id']==cid and s['arm']==arm and s['phase']==phase];joint=None
     if len(found)==3 and all(s['request_id'] in extracted and extracted[s['request_id']]['physical_status']=='commit' for s in found):
      # Every final call and its original frozen peer/own payload must already exist.
      byrole={s['role']:extracted[s['request_id']]['action'] for s in found};joint=[next(a['value'] for a in role['actions'] if a['id']==byrole[role['id']]) for role in c['roles']]
     human[cid][arm+phase]=joint
  for cid,c in data['animal'].items():
   animals[cid]={}
   for arm in 'VNU':
    node='root';actions={};history=[]
    while node:
     found=[e for e in intents.values() if e['slot']['case_id']==cid and e['slot']['arm']==arm and json.loads(e['request']['messages'][1]['content']).get('current_node')==node]
     if not found:break
     if len(found)!=1:raise ValueError('Ambiguous observed animal node')
     e=found[0];body=json.loads(e['request']['messages'][1]['content'])
     if body['observed_history']!=history:break # Never replace actual transmitted history with rescued alternatives.
     result=extracted[e['slot']['request_id']]
     if result['physical_status']!='commit':break
     action=result['action'];actions[node]=action;edge=next(a for a in c['nodes'][node]['actions'] if a['id']==action)['by_state'][c['tape_state']]
     history.append({'node':node,'action':action,'observed_consequences':edge['consequences']});node=edge.get('next')
    animals[cid][arm]=actions
  physical={'human_commitments':human,'animal_trajectories':animals}
  counts={arm:{'started':sum(r['arm']==arm for r in rows),'readable_commits':sum(r['arm']==arm and r['physical_status']=='commit' for r in rows),'newly_readable_original_nonvalid':sum(r['arm']==arm and r['original_status']!='valid' and r['physical_status']=='commit' for r in rows),'recovered_initial_cannot_backfill':sum(r['arm']==arm and r['phase']=='initial' and r['original_status']!='valid' and r['physical_status']=='commit' for r in rows)} for arm in 'VNU'}
  allout['modes'][mode]={'counts_by_arm':counts,'extraction_rows':rows,'physical':physical,'welfare':welfare(physical)}
 target=ROOT/'results/original_sensitivity.json'
 with target.open('x') as f:json.dump(allout,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({m:x['counts_by_arm'] for m,x in allout['modes'].items()},indent=2))
if __name__=='__main__':main()
