"""Frozen deterministic S1/S2 and native Choice extraction, arm/key blind.
S1 preserves original schema/auxiliary checks, relaxing rationale bytes only.
S2 adds physical-only JSON and one exact anchored Choice/Action field.
No narrative substring aliases, duplicate keys, truncation rescue or LLM repair.
"""
import json,re
from integration.draft import scoring
class Reject(ValueError):pass
def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise Reject('duplicate JSON key')
  d[k]=v
 return d
def strict(raw):
 d=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(Reject('nonfinite')))
 if not isinstance(d,dict):raise Reject('not one object')
 return d
def object_spans(raw):
 spans=[];depth=0;start=None;quoted=False;escape=False
 for i,ch in enumerate(raw):
  if depth and quoted:
   if escape:escape=False
   elif ch=='\\':escape=True
   elif ch=='"':quoted=False
  elif depth and ch=='"':quoted=True
  elif ch=='{':
   if depth==0:start=i
   depth+=1
  elif ch=='}':
   if depth==0:raise Reject('unmatched brace')
   depth-=1
   if depth==0:spans.append((start,i+1))
 if depth or quoted:raise Reject('incomplete object')
 return spans
# Only explicit, full field lines; optional markdown emphasis on field name only.
FIELD=re.compile(r'^\s*(?:\*\*)?(Choice|Action)(?:\*\*)?\s*:\s*([^\r\n]+?)\s*$',re.I|re.M)
NONCOMMIT=re.compile(r'^\s*(?:status\s*:\s*(?:refuse|unresolved)|I\s+(?:refuse\b|decline\s+to\s+(?:choose|decide)|cannot\s+(?:choose|decide)|can[’\']t\s+(?:choose|decide)))',re.I|re.M)
def explicit(raw,labels):
 fields=FIELD.findall(raw)
 if len(fields)!=1:raise Reject('not one explicit Choice/Action field')
 value=fields[0][1].strip()
 # Exact label, optional one enclosing pair of quotes/backticks, optional final period.
 if value.endswith('.'):value=value[:-1]
 if len(value)>1 and value[0]==value[-1] and value[0] in ('"',"'",'`'):value=value[1:-1]
 if value not in labels:raise Reject('field value not exact allowed label')
 return value

def extract(raw,menu,domain,mode,original_status=None,finish_reason=None):
 result={'physical_status':'invalid','action':None,'extraction':None,'error':None}
 try:
  if finish_reason=='length' or original_status in ('incomplete','transport_failure'):raise Reject('truncated/incomplete/transport')
  if not isinstance(raw,str) or not raw.strip():raise Reject('no response text')
  if len(menu)!=len(set(menu)):raise Reject('menu collision')
  outside=raw;obj=None
  try:obj=strict(raw.strip());outside='';kind='strict_json'
  except (ValueError,TypeError):
   if mode=='S1':raise Reject('not strict complete JSON')
   spans=object_spans(raw)
   if len(spans)>1:raise Reject('multiple JSON objects')
   if spans:
    lo,hi=spans[0];obj=strict(raw[lo:hi]);outside=raw[:lo]+raw[hi:];kind='single_embedded_json'
   else:kind='explicit_field'
  if NONCOMMIT.search(outside):raise Reject('explicit noncommitment statement')
  if obj is None:
   action=explicit(raw,menu);status='commit'
  else:
   if FIELD.search(outside):raise Reject('additional competing decision field')
   if mode=='S1':
    copy=dict(obj)
    if not isinstance(copy.get('reason'),str):raise Reject('reason type')
    copy['reason']=''
    # The caller supplies no model arm or normative key to this extraction function.
    if domain=='human':
     if set(copy)!={'action','reason'}:raise Reject('human schema')
    else:
     if set(copy)!={'status','action','judgment','factual_action','reason'}:raise Reject('animal schema')
     j=copy['judgment']
     if not isinstance(j,dict) or set(j)!={'permitted','required','recommended','unresolved'}:raise Reject('auxiliary judgment schema')
     if any(not isinstance(v,list) or any(not isinstance(a,str) for a in v) or len(v)!=len(set(v)) or not set(v)<=set(menu) for v in j.values()):raise Reject('auxiliary judgment IDs')
     if not set(j['required'])<=set(j['permitted']) or not set(j['recommended'])<=set(j['permitted']) or set(j['unresolved'])&set(j['permitted']):raise Reject('auxiliary coherence')
     if copy['factual_action'] not in menu:raise Reject('auxiliary factual ID')
   if any(k.lower() in ('action','choice','status') and k not in ('action','status') for k in obj):raise Reject('competing action/status alias')
   status=obj.get('status','commit' if domain=='human' else None);action=obj.get('action')
  if status in ('refuse','unresolved'):
   if action is not None:raise Reject('noncommit with action')
   result.update(physical_status=status,extraction=kind);return result
  if status!='commit' or type(action) is not str or action not in menu:raise Reject('invalid status/action or out of menu')
  result.update(physical_status='commit',action=action,extraction=kind)
 except (ValueError,TypeError,KeyError) as e:result['error']=str(e)
 return result

def native_choice(raw,finish_reason=None):
 if finish_reason=='length':return {'status':'truncated','choice':None,'rationale_format':False}
 try:
  if NONCOMMIT.search(raw):return {'status':'refuse','choice':None,'rationale_format':False}
  choice=explicit(raw,{'A','B','Conditional','Undetermined','Refuse'})
  rationale=bool(re.search(r'^Trade-off:\s*\S',raw,re.M) and re.search(r'^Reason:\s*\S',raw,re.M))
  return {'status':'valid','choice':choice,'rationale_format':rationale,'policy_status_text_present':bool(re.search(r'Policy status:',raw,re.I))}
 except (ValueError,TypeError):return {'status':'invalid','choice':None,'rationale_format':False}
