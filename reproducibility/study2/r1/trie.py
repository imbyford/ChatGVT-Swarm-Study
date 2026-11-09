"""Finite complete-response token trie, independent of arm, key or welfare rank."""
class TokenTrie:
 def __init__(self,tokenizer,candidates,eos=248044,cap=128):
  if not candidates or len(candidates)!=len(set(candidates)):raise ValueError('Empty/duplicate candidates')
  self.paths={};self.next={};self.eos=eos
  for text in candidates:
   ids=tokenizer.encode(text,add_special_tokens=False)
   if not ids or tokenizer.decode(ids,skip_special_tokens=False)!=text or any(x in (248044,248046) for x in ids):raise ValueError('Non-roundtrip or embedded EOS')
   path=tuple(ids+[eos])
   if len(path)>cap or path in self.paths:raise ValueError('Collision or insufficient cap')
   self.paths[path]=text
   for i,t in enumerate(path):self.next.setdefault(path[:i],set()).add(t)
  for path in self.paths:
   for i,t in enumerate(path):
    allowed=self.allowed(path[:i]);assert t in allowed and (eos not in allowed or i==len(path)-1)
  self.longest=max(map(len,self.paths))
 def allowed(self,prefix):
  out=sorted(self.next.get(tuple(prefix),()))
  if not out:raise ValueError('Trie dead end; no default or unconstrained fallback')
  return out
 def callback(self,prompt_ids):
  prompt=tuple(prompt_ids)
  def fn(batch,input_ids):
   ids=tuple(input_ids.tolist())
   if batch!=0 or ids[:len(prompt)]!=prompt:raise ValueError('Wrong batch/prompt boundary')
   return self.allowed(ids[len(prompt):])
  return fn
 def decode(self,ids):
  try:return self.paths[tuple(ids)]
  except KeyError:raise ValueError('Generated path is incomplete or outside grammar')
