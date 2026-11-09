"""Exact UTF-8 payload inventory and offline request ledger; no tokenizer downloads or APIs."""
from pathlib import Path
import sys,json,itertools,hashlib,collections
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from prompts import human_request,animal_request
from scoring import FIELDS
load=lambda p:json.loads((ROOT/p).read_text())
H=sum([load('model_facing/'+d+'/'+s+'.json') for d,s in [('development','human_development'),('protected_draft','human_protected')]],[])
A=load('private/animal_source_with_tapes.json'); reg=load('private/family_split_registry.json'); byid={r['id']:r for r in reg}
slots=[]; counts=[]; payloads={}
def measure(p): return sum(len(v.encode('utf-8')) for v in p.values())
def record(id,kind,candidate_payloads,max_output):
 lengths=[measure(p) for p in candidate_payloads]
 row={'slot_id':id,'kind':kind,'candidate_payload_count':len(lengths),'system_plus_user_utf8_bytes_min':min(lengths),'system_plus_user_utf8_bytes_max':max(lengths),'pinned_tokenizer':None,'exact_input_token_count':None,'max_output_token_request':max_output,'token_count_status':'PENDING_EVALUATOR_SAFE_MODEL_TOKENIZER_AND_OFFLINE_VOCABULARY'}
 counts.append(row); return row
for c in H:
 for role in c['roles']:
  rid=role['id']; candidates={'initial':[human_request(c,rid,'initial')],'I':[],'S':[]}
  for t in itertools.product(range(3),repeat=3):
   acts={r['id']:r['actions'][t[j]]['id'] for j,r in enumerate(c['roles'])}
   candidates['I'].append(human_request(c,rid,'I',acts[rid]))
   candidates['S'].append(human_request(c,rid,'S',acts[rid],{r:a for r,a in acts.items() if r!=rid}))
  for phase,pp in candidates.items():
   base=f'{c["id"]}/{phase}/{rid}'; info=record(base,'human',pp,512)
   if phase=='initial': payloads[base]=pp[0]
   for arm in ['V','N','U']:
    slots.append({'request_id':base+'/'+arm,'case_id':c['id'],'family_group':c['family'],'split':byid[c['id']]['split'],'arm':arm,'phase':phase,'role':rid,'conditional':phase!='initial','condition':'all three initial proposals for this arm/world valid' if phase!='initial' else 'none','payload_inventory_id':base,'max_output_tokens':512})
for c in A:
 base=f'{c["id"]}/root'; p=animal_request(c,'root'); info=record(base,'animal_root',[p],1024); payloads[base]=p
 for arm in ['V','N','U']:
  slots.append({'request_id':base+'/'+arm,'case_id':c['id'],'family_group':c['family'],'split':c['split'],'arm':arm,'phase':'root','conditional':False,'condition':'none','payload_inventory_id':base,'max_output_tokens':1024})
 child_payloads=[]
 for a in c['nodes']['root']['actions']:
  for state,e in a['by_state'].items():
   if e.get('next'):
    history=[{'node':'root','action':a['id'],'observed_consequences':e['consequences']}]
    child_payloads.append(animal_request(c,e['next'],history))
 if child_payloads:
  base=f'{c["id"]}/continuation'; record(base,'animal_conditional_continuation',child_payloads,1024)
  for arm in ['V','N','U']:
   slots.append({'request_id':base+'/'+arm,'case_id':c['id'],'family_group':c['family'],'split':c['split'],'arm':arm,'phase':'continuation','conditional':True,'condition':'valid root action reaches a child under the common hidden state','payload_inventory_id':base,'max_output_tokens':1024})
ci={r['slot_id']:r for r in counts}
summary={'status':'OFFLINE_RESERVATION_NOT_EXECUTION_OR_SPENDING_APPROVAL','case_counts':dict(collections.Counter(r['split'] for r in reg)),'family_counts':{s:len({r['family_group'] for r in reg if r['split']==s}) for s in sorted({r['split'] for r in reg})},'planned_max_requests':len(slots),'human_requests':sum(r['kind']=='human' for r in counts)*3,'animal_root_requests':sum(r['kind']=='animal_root' for r in counts)*3,'animal_max_continuation_requests':sum(r['kind']=='animal_conditional_continuation' for r in counts)*3,'requests_by_split':dict(collections.Counter(s['split'] for s in slots)),'max_requested_output_tokens':sum(s['max_output_tokens'] for s in slots),'payload_utf8_bytes_upper_sum':sum(ci[s['payload_inventory_id']]['system_plus_user_utf8_bytes_max'] for s in slots),'max_single_payload_utf8_bytes':max(r['system_plus_user_utf8_bytes_max'] for r in counts),'framing_and_hidden_reasoning':'Not measured: provider/model/tokenizer unspecified. UTF-8 bytes are not presented as actual tokens or as a universal token bound. Output caps require provider verification that they cap billable reasoning as applicable.','actual_model_requests':0,'actual_token_spend':0,'cost_estimate':None,'exact_prompt_tokens':None,'reason_exact_tokens_pending':'No deployment/tokenizer identifier or vocabulary in clean packet; tiktoken unavailable locally. No downloads, model calls or paid resources used.'}
# Stable proposed ordering; actual provider request IDs and timings must be logged later.
for s in slots: s['proposed_order_key']=hashlib.sha256(('study2-order-v1|2026110802|'+s['request_id']).encode()).hexdigest()
for name,obj in [('request_plan.json',summary),('request_slots.json',slots),('prompt_byte_inventory.json',counts)]:
 (ROOT/'protocol'/name).write_text(json.dumps(obj,indent=2)+'\n')
(ROOT/'private/rendered_initial_requests.json').write_text(json.dumps(payloads,indent=2)+'\n')
balance=[]
for split in sorted({r['split'] for r in reg}):
 for family in sorted({r['family_group'] for r in reg if r['split']==split}):
  rs=[r for r in reg if r['split']==split and r['family_group']==family]
  balance.append({'split':split,'family_group':family,'case_ids':[r['id'] for r in rs],'parent_ids':[r['parent_id'] for r in rs],'family_weight_within_split':1/len({r['family_group'] for r in reg if r['split']==split}),'parent_weight_within_family':1/len(rs),'arms':['V','N','U'],'human_conditions':['I','S'] if split.startswith('human') else None})
(ROOT/'review/family_balance.json').write_text(json.dumps(balance,indent=2)+'\n')
print(json.dumps(summary,indent=2))
