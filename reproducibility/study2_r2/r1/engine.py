"""R2 ordinary greedy generation, stopped at first nonblank line; no logits constraints."""
import time,uuid
from tools.reference_engine import ReferenceEngine
from experiment.selection import selection
from integration.draft import canonical,digest
from r1.prefix import FirstLineStop,first_line,should_stop
class Engine(ReferenceEngine):
 def complete(self,slot,request):
  arm=slot['arm'];expected='Qwen/Qwen3.5-4B' if arm=='U' else self.routes[arm]['model_id']
  if request['model']!=expected:raise ValueError('Wrong model binding; no fallback')
  if request['temperature']!=0 or request['top_p']!=1 or request['seed']!=20261107 or request['chat_template_kwargs']!={'enable_thinking':False} or request['n']!=1 or request['stream']:raise ValueError('Decoding changed')
  from transformers import GenerationConfig,StoppingCriteriaList
  torch=self.torch;limit=request['max_completion_tokens']
  if limit!=128:raise ValueError('Frozen per-call cap changed')
  with selection(self.model,self.layers,arm),torch.inference_mode():
   self.model.eval();torch.manual_seed(20261107);torch.cuda.manual_seed_all(20261107)
   rendered=self.tokenizer.apply_chat_template(request['messages'],tokenize=False,add_generation_prompt=True,enable_thinking=False)
   inputs=self.tokenizer(rendered,return_tensors='pt',add_special_tokens=False).to('cuda');n=inputs['input_ids'].shape[-1]
   if n+limit>4096:raise ValueError('Context limit')
   config=GenerationConfig(do_sample=False,max_new_tokens=limit,use_cache=True,eos_token_id=[248044,248046],pad_token_id=248044)
   started=time.time()
   generated=self.model.generate(**inputs,generation_config=config,return_dict_in_generate=True,output_scores=False,stopping_criteria=StoppingCriteriaList([FirstLineStop(self.tokenizer,n)]))
   ids=generated.sequences[0,n:].tolist();raw=self.tokenizer.decode(ids,skip_special_tokens=True);newline=should_stop(raw);eos=bool(ids and ids[-1] in (248044,248046));finish='stop' if newline or eos else 'length'
   line,boundary,terminated=first_line(raw)
   record={'request_id':slot['request_id'],'selected':arm,'verified_layers':len(self.layers),'input_tokens':n,'output_tokens':len(ids),'rendered_prompt_sha256':digest(rendered),'generated_token_ids':ids,'constraint':None,'stopping_rule':'first_newline_ending_first_nonblank_line_or_EOS','stop_cause':'first_line_newline' if newline else 'EOS' if eos else 'token_cap','decision_boundary':boundary,'first_line':line,'finish_reason':finish,'elapsed_seconds':time.time()-started}
   with (self.output/'token_traces.jsonl').open('a') as f:f.write(canonical(record)+'\n');f.flush()
   return {'id':'r2-reference-'+uuid.uuid4().hex,'model':expected,'raw':raw,'finish_reason':finish,'input_tokens':n,'output_tokens':len(ids),'token_audit':record}
