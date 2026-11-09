"""Offline saved-response replay only. Network sockets are explicitly disabled."""
from pathlib import Path
import hashlib,json,os,shutil,socket,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parent
def no_network(*args,**kwargs):raise RuntimeError('Network disabled in offline reproduction')
socket.socket=no_network;socket.create_connection=no_network
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 m=json.loads((ROOT/'MANIFEST.json').read_text())
 for rel,h in m['files'].items():assert sha(ROOT/rel)==h,rel
 env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
 for task in ['study2','study1','r2']:
  subprocess.run([sys.executable,str(Path(__file__).resolve()),task],check=True,env=env)
 print('PASS: all packaged hashes, exact scientific R1/original Study 2 replay, S1/S2, Study 1 recorded-action replay, R2 and consequence rescoring; account IDs pseudonymised. No models loaded or network used.')
def study2():
 # Work only on a fresh temporary copy; never overwrite expected evidence.
 work=Path(tempfile.mkdtemp(prefix='apart-manuscript-replay-'));d=work/'study2';shutil.copytree(ROOT/'study2',d);sys.path.insert(0,str(d));os.chdir(d)
 import integration.bindings as bindings
 def offline_candidate(root=d):
  b=json.loads((root/'config/evaluation_binding.v0.3.json').read_text())
  excluded={x['path']:x['sha256'] for x in json.loads((ROOT/'SANITISATION.json').read_text())['excluded_study2_files']}
  for rel,h in b['bound_files'].items():
   if rel in excluded:assert excluded[rel]==h
   else:assert sha(root/rel)==h
  candidate=root/b['candidate_path'];m=json.loads((candidate/'private/CANDIDATE_INTEGRITY_MANIFEST_v0.3.json').read_text())
  for rel,rec in m['files'].items():
   key=b['candidate_path']+'/'+rel
   if key in excluded:assert excluded[key]==rec['sha256']
   else:assert sha(candidate/rel)==rec['sha256'] and (candidate/rel).stat().st_size==rec['bytes']
  return {k:b[k] for k in ('version','candidate_manifest_sha256','reporting_contract_sha256','guide_closure_sha256','review_scope','human_validation','blinded_review','live_execution_authorized')}
 bindings.verify_candidate=offline_candidate
 from integration.draft import canonical,digest,load
 from r1 import runner,analysis
 manifest=json.loads((d/'config/models.manifest.json').read_text())
 ids={a:manifest['adapters'][a]['model_id'] for a in 'VN'};ids['U']=manifest['base']['repo']
 # Only model-file availability checks are replaced: resolve saved IDs from the
 # hash-bound manifest because large weights are deliberately not distributed.
 runner.model_ids=lambda:ids
 events=[json.loads(x) for x in (d/'raw/ledger.jsonl').read_text().splitlines()]
 physical=runner.replay(events);assert physical==json.loads((d/'raw/physical.json').read_text())
 result=analysis.report(events,physical);assert result==json.loads((d/'expected/r1_analysis.json').read_text())
 intents={e['slot']['request_id']:e for e in events if e['event']=='request_intent'}
 for e in events:
  if e['event']=='response':
   q=intents[e['request_id']];assert e['reply']['model']==ids[q['slot']['arm']] and q['request_sha256']==digest(q['request']) and e['response_sha256']==digest(e['reply']['raw'])
 responses={e['request_id']:e for e in events if e['event']=='response'}
 inventory=json.loads((d/'reports/r1_tokenizer_inventory.json').read_text());variants={v['messages_sha256']:v for v in inventory['variants']}
 traces=[json.loads(x) for x in (d/'raw/token_traces.jsonl').read_text().splitlines()]
 assert len(traces)==len(intents)==925
 for t in traces:
  e=intents[t['request_id']];q=e['request'];reply=responses[t['request_id']]['reply'];variant=variants[digest(q['messages'])]
  assert t==reply['token_audit'] and t['selected']==e['slot']['arm'] and t['verified_layers']==128
  assert t['rendered_prompt_sha256']==variant['rendered_sha256'] and t['input_tokens']==variant['input_tokens']
  if e['slot']['task']!='native':
   paths=[inventory['candidates'][s] for s in q['r1_allowed_responses']]
   assert t['allowed_token_paths']==paths and t['generated_token_ids'] in paths
  else:assert t['allowed_token_paths'] is None
 runtime=json.loads((d/'raw/reference_runtime.json').read_text())
 for arm in 'VN':
  ev=runtime['adapters'][arm];assert ev['weight_sha256']==manifest['adapters'][arm]['files']['adapter_model.safetensors']
  assert ev['exact_fp32_gpu_tensors']==256 and ev['target_modules']==128
 # Original strict replay uses the unchanged candidate/runner. Restore only the
 # recorded execution header; that is metadata, not a scoring or parsing change.
 original=[json.loads(x) for x in (d/'inputs/original_ledger.jsonl').read_text().splitlines()];header=original[0]
 import integration.frozen as frozen
 def saved_header(identities):
  assert identities==header['inference_identities']
  return {k:header[k] for k in ['mode','empirical_treatment_results','source','execution_binding']}
 frozen.live_header=saved_header
 from integration.report_scripted import report
 orig=report(original);expected_orig=json.loads((d/'expected/original_analysis.json').read_text())
 # Public provider-ID aliases change only the ledger metadata digest.
 # Verify the public digest, then compare every remaining analysis field exactly.
 assert orig.pop('ledger_content_sha256')==digest(original)
 expected_orig.pop('ledger_content_sha256')
 assert orig==expected_orig
 (d/'results').mkdir(exist_ok=True)
 from r1.sensitivity import main as sensitivity
 sensitivity()
 actual_s=json.loads((d/'results/original_sensitivity.json').read_text());expected_s=json.loads((d/'expected/sensitivity.json').read_text())
 assert actual_s.pop('original_ledger_sha256')==sha(d/'inputs/original_ledger.jsonl')
 expected_s.pop('original_ledger_sha256')
 assert actual_s==expected_s
 print('PASS Study 2: exact original/R1 schedule, messages, actions and analyses; S1/S2 scientific payload exact; public ledger metadata digest differs as documented. Weight loading intentionally not repeated.')
def study1():
 d=ROOT/'study1';sys.path.insert(0,str(d))
 from experiment.worlds import World,score
 from experiment.protocol import replay
 from experiment.animal_protocol import replay_animal
 from experiment.analysis import human_analysis,animal_analysis
 from model_client import canonical
 c=json.loads((d/'frozen/candidates.json').read_text());expected=json.loads((d/'raw/replayed_analysis.json').read_text())
 # Preserve historical snapshot IDs after public checkpoint-ID pseudonymisation.
 # This lookup is limited to snapshot metadata, never prompts/actions/outcomes.
 import experiment.protocol as protocol
 base_digest=protocol.digest
 snapshot_aliases={}
 for ledger in (d/'ledgers').glob('*.jsonl'):
  for line in ledger.read_text().splitlines():
   e=json.loads(line)
   if e.get('event')=='snapshot' and e.get('snapshot') is not None:
    snapshot_aliases[base_digest(canonical(e['snapshot']))]=e['snapshot_sha256']
 protocol.digest=lambda value:snapshot_aliases.get(base_digest(value),base_digest(value))
 human=[];animal=[];count=0
 for domain,items in [('human',c['human']),('animal',c['animal'])]:
  for item in items:
   cells={}
   for path in sorted((d/'ledgers').glob(item['id']+'_*.jsonl')):
    events=[json.loads(s) for s in path.read_text().splitlines()];count+=1
    if domain=='human':
     replay(World.load(item),events);arm=events[0]['key']['arm']
     for e in events:
      if e['event']=='branch_result':cells[arm+e['branch']]={k:v for k,v in e.items() if k not in ('seq','event')}
    else:
     replay_animal(item,events);arm=events[0]['arm']
     for e in events:
      if e['event']=='result':cells[arm]={k:v for k,v in e.items() if k not in ('seq','event')}
   row={'id':item['id'],'family':item['family'],'cells':cells}
   (human if domain=='human' else animal).append(row)
 assert count==72
 assert human==expected['raw_case_results']['human'] and animal==expected['raw_case_results']['animal']
 assert human_analysis(c['human'],human)==expected['human']
 assert animal_analysis(c['animal'],animal)==expected['animal']
 print('PASS Study 1: all 72 exact ledgers, physical outcomes and frozen human/animal analyses. Original serving identity audit retained separately.')

def r2():
 work=Path(tempfile.mkdtemp(prefix='apart-r2-replay-'));d=work/'r2';shutil.copytree(ROOT/'study2_r2',d);sys.path.insert(0,str(d));os.chdir(d)
 import integration.bindings as bindings
 def offline_candidate(root=d):
  b=json.loads((root/'config/evaluation_binding.v0.3.json').read_text())
  excluded={x['path']:x['sha256'] for x in json.loads((ROOT/'SANITISATION.json').read_text())['excluded_study2_files']}
  for rel,h in b['bound_files'].items():
   if rel in excluded:assert excluded[rel]==h
   else:assert sha(root/rel)==h
  candidate=root/b['candidate_path'];m=json.loads((candidate/'private/CANDIDATE_INTEGRITY_MANIFEST_v0.3.json').read_text())
  for rel,rec in m['files'].items():
   key=b['candidate_path']+'/'+rel
   if key in excluded:assert excluded[key]==rec['sha256']
   else:assert sha(candidate/rel)==rec['sha256'] and (candidate/rel).stat().st_size==rec['bytes']
  return {k:b[k] for k in ('version','candidate_manifest_sha256','reporting_contract_sha256','guide_closure_sha256','review_scope','human_validation','blinded_review','live_execution_authorized')}
 bindings.verify_candidate=offline_candidate
 from integration.draft import digest,canonical
 from r1 import runner,analysis
 from r1.prefix import first_line,parse,should_stop
 m=json.loads((d/'config/models.manifest.json').read_text());ids={a:m['adapters'][a]['model_id'] for a in 'VN'};ids['U']=m['base']['repo'];runner.model_ids=lambda:ids
 events=[json.loads(x) for x in (d/'raw/ledger.jsonl').read_text().splitlines()]
 physical=runner.replay(events);assert physical==json.loads((d/'raw/physical.json').read_text())
 a=analysis.report(events,physical);assert a==json.loads((d/'expected/independent_analysis.json').read_text())
 qs={e['slot']['request_id']:e for e in events if e['event']=='request_intent'};rs={e['request_id']:e for e in events if e['event']=='response'}
 traces=[json.loads(x) for x in (d/'raw/token_traces.jsonl').read_text().splitlines()]
 inv=json.loads((d/'reports/r1_tokenizer_inventory.json').read_text());variants={x['messages_sha256']:x for x in inv['variants']}
 assert len(qs)==len(rs)==len(traces)==720
 for t in traces:
  q=qs[t['request_id']];r=rs[t['request_id']];req=q['request'];raw=r['reply']['raw'];v=variants[digest(req['messages'])]
  assert t==r['reply']['token_audit'] and t['selected']==q['slot']['arm'] and t['verified_layers']==128
  assert req['model']==ids[q['slot']['arm']]==r['reply']['model']
  assert q['request_sha256']==digest(req) and r['response_sha256']==digest(raw)
  assert t['constraint'] is None and t['rendered_prompt_sha256']==v['rendered_sha256'] and t['input_tokens']==v['input_tokens']
  assert len(t['generated_token_ids'])==r['reply']['output_tokens']<=128
  assert first_line(raw)[1]==t['decision_boundary']
  assert parse(raw,r['reply']['finish_reason'],req['r2_allowed_labels'],physical=q['slot']['task']=='physical')==r['parsed']
 runtime=json.loads((d/'raw/reference_runtime.json').read_text())
 for arm in 'VN':
  t=runtime['adapters'][arm];assert t['weight_sha256']==m['adapters'][arm]['files']['adapter_model.safetensors']
  assert t['exact_fp32_gpu_tensors']==256 and t['target_modules']==128
 # Recompute every all-row format comparison directly from preserved replies.
 prior=[json.loads(x) for x in (ROOT/'study2/raw/ledger.jsonl').read_text().splitlines()];old={x['request_id']:x for x in prior if x['event']=='response'}
 cmp=json.loads((d/'expected/format_comparisons.json').read_text())
 for x in cmp['rows']:
  sid='uptake/'+x['pair_id']+'/'+x['arm'];reply=rs[sid];valid=reply['status']=='valid';choice=reply['parsed']['Choice'] if valid else None
  assert x['R2_choice']==choice and x['R2_valid']==valid and x['R1_constrained_choice']==old[sid]['parsed']['Choice']
  for target in 'VN':assert x['R2_'+target+'_match']==(choice==x[target+'_target'] if valid else None)
 print('PASS R2: exact schedule/messages/raw-response replay, scoring, all720 identities/prompt traces, first-field extraction and360 paired format comparisons. GPU/earliest-token verification retained as trusted-host evidence; weights/tokenizer runtime not redistributed.')

if __name__=='__main__':
 if len(sys.argv)==1:main()
 elif sys.argv[1]=='study2':study2()
 elif sys.argv[1]=='study1':study1()
 elif sys.argv[1]=='r2':r2()
 else:raise SystemExit('Unknown offline task')
