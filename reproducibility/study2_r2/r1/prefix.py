"""Frozen R2 first-nonblank-line stop and exact extraction. No semantic repair."""
import re

def first_line(raw):
 """Return first nonblank line and boundary; trailing bytes are preserved in raw."""
 offset=0
 for part in raw.splitlines(keepends=True):
  text=part.rstrip('\r\n')
  if text.strip():return text,offset+len(part),part.endswith(('\r','\n'))
  offset+=len(part)
 return None,None,False

def should_stop(raw):
 line,end,terminated=first_line(raw)
 return bool(line is not None and terminated)

def parse(raw,finish,allowed,physical=False):
 line,end,terminated=first_line(raw)
 result={'response_status':'invalid','status':'invalid','action':None,'Choice':None,'first_line':line,'decision_boundary':end,'line_terminated':terminated}
 if finish=='length' and not terminated:
  result.update(response_status='truncated',status='truncated');return result
 if line is None:return result
 m=re.fullmatch(r'\s*Choice\s*:\s*(.*?)\s*',line,flags=re.I)
 if not m:return result
 value=m.group(1).strip()
 if value.endswith('.'):value=value[:-1].rstrip()
 if len(value)>1 and value[0]==value[-1] and value[0] in ('"',"'",'`'):value=value[1:-1]
 if value not in allowed:return result
 result.update(response_status='valid',Choice=value,status='valid')
 if physical:
  result.update(status='unresolved' if value=='Unresolved' else 'refuse' if value=='Refuse' else 'commit',action=value if value not in ('Unresolved','Refuse') else None)
 return result

class FirstLineStop:
 """HF-compatible stopping callable. Decodes generated tokens only, batch size one."""
 def __init__(self,tokenizer,prompt_length):self.tokenizer=tokenizer;self.prompt_length=prompt_length
 def __call__(self,input_ids,scores=None,**kwargs):
  return should_stop(self.tokenizer.decode(input_ids[0,self.prompt_length:].tolist(),skip_special_tokens=True))
