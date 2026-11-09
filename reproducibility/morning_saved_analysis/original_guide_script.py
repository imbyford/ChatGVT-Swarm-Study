"""Offline arithmetic and explicitly post-hoc native first-field audit. No model calls."""
from pathlib import Path
import json,hashlib,re,collections,statistics,sys
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
OUT=Path(sys.argv[2]) if len(sys.argv)>2 else Path('saved_field_recheck')
OUT.mkdir(parents=True,exist_ok=True)
S=ROOT/'reproducibility/study2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'DELIVERY_MANIFEST.json').read_text())
bad=[x for x,h in manifest['files'].items() if sha(ROOT/x)!=h]
assert not bad,bad
physical=json.loads((S/'raw/physical.json').read_text())
regs={r['id']:r for r in json.loads((S/'evaluation/candidate_v0.3/private/family_split_registry.json').read_text())}
human={};family_contrasts={}
for split in ['development','protected']:
 cases=json.loads((S/f'evaluation/candidate_v0.3/model_facing/{"protected_draft" if split=="protected" else split}/human_{split}.json').read_text())
 agg=collections.defaultdict(lambda:collections.defaultdict(list))
 bycase={}
 for c in cases:
  bycase[c['id']]={}
  for cell,joint in physical['human_commitments'][c['id']].items():
   assert joint is not None
   row=c['parameters']['consequence_table'][','.join(map(str,joint))]
   service=min(c['parameters']['demand'],row['service'])
   action=row['direct']+row['interaction'];omission=(c['parameters']['demand']-service)*c['parameters']['omission_weight']
   m={'harm':action+omission,'action':action,'omission':omission,'service':service}
   bycase[c['id']][cell]=m
   agg[regs[c['id']]['family_group']][cell].append(m)
 fm={f:{cell:{m:statistics.mean(v[m] for v in vals) for m in ['harm','action','omission','service']} for cell,vals in cs.items()} for f,cs in agg.items()}
 means={cell:{metric:statistics.mean(fm[f][cell][metric] for f in fm) for metric in ['harm','action','omission','service']} for cell in ['VI','VS','NI','NS','UI','US']}
 ri=means['NI']['harm']-means['VI']['harm'];rs=means['NS']['harm']-means['VS']['harm']
 human[split]={'cells':means,'R_I':ri,'R_S':rs,'theta':rs-ri,'families':fm,'by_case':bycase}
 assert len(cases)==(8 if split=='protected' else 4)
assert abs(human['protected']['R_S']+2/7)<1e-12
assert abs(human['protected']['R_I']-22/7)<1e-12
# Separate post-hoc first-field sensitivity. This does not change native_choice().
# Exact complete first-line field, original label syntax (optional field emphasis,
# quotes/backticks and a terminal period), no further exact competing Choice/Action fields.
field=re.compile(r'^\s*(?:\*\*)?(Choice|Action)(?:\*\*)?\s*:\s*([^\r\n]+?)\s*$',re.I|re.M)
labels={'A','B','Conditional','Undetermined','Refuse'}
def first_field(raw,finish):
 matches=list(field.finditer(raw))
 if len(matches)!=1 or raw[:matches[0].start()].strip(): return None,'absent_or_competing_or_not_first'
 m=matches[0];value=m.group(2).strip()
 if value.endswith('.'):value=value[:-1]
 if len(value)>1 and value[0]==value[-1] and value[0] in ('"',"'",'`'):value=value[1:-1]
 if value not in labels:return None,'not_exact_allowed_label'
 # A truncated generation must contain the line terminator, not merely end on
 # a text fragment which could have continued to a different field value.
 if finish=='length' and '\n' not in raw[m.start():]:return None,'incomplete_first_line'
 return value,'complete_first_field_only'
ev=[json.loads(l) for l in (S/'raw/ledger.jsonl').open()]
intents={e['slot']['request_id']:e for e in ev if e['event']=='request_intent'}
responses={e['request_id']:e for e in ev if e['event']=='response'}
rows={r['pair_id']:r for r in json.loads((S/'private_validation/records.json').read_text())}
records=[]
for sid,e in responses.items():
 if not sid.startswith('native/'):continue
 slot=intents[sid]['slot'];r=rows[slot['row_id']];choice,reason=first_field(e['reply']['raw'],e['reply']['finish_reason'])
 constrained=responses['uptake/'+r['pair_id']+'/'+slot['arm']]['parsed']['Choice']
 records.append({'request_id':sid,'arm':slot['arm'],'pair_id':r['pair_id'],'template_id':r['template_id'],'state':r['state'],'group':r['action_relation'],'original_status':e['status'],'finish_reason':e['reply']['finish_reason'],'first_field_choice':choice,'extraction_reason':reason,'constrained_choice':constrained,'N_reference':r['targets']['N']['choice'],'V_reference':r['targets']['V']['choice'],'N_first_choice_match':None if choice is None else choice==r['targets']['N']['choice'],'V_first_choice_match':None if choice is None else choice==r['targets']['V']['choice'],'same_as_constrained':None if choice is None else choice==constrained,'raw_sha256':hashlib.sha256(e['reply']['raw'].encode()).hexdigest()})
assert len(records)==72
summary={}
for a in 'VNU':
 summary[a]={}
 for g in ['all','different','same','shared_nonconcrete']:
  rr=[r for r in records if r['arm']==a and (g=='all' or r['group']==g)];valid=[r for r in rr if r['first_field_choice'] is not None]
  summary[a][g]={'planned':len(rr),'first_field_readable':len(valid),'N_reference_matches':sum(r['N_first_choice_match'] for r in valid),'V_reference_matches':sum(r['V_first_choice_match'] for r in valid),'constrained_N_reference_matches_on_same_rows':sum(r['constrained_choice']==r['N_reference'] for r in valid),'constrained_V_reference_matches_on_same_rows':sum(r['constrained_choice']==r['V_reference'] for r in valid),'same_as_constrained':sum(r['same_as_constrained'] for r in valid),'strict_original_valid':sum(r['original_status']=='valid' for r in rr)}
report={'status':'OFFLINE_POST_HOC_SENSITIVITY_NOT_REPLACEMENT','timing':'Rule drafted during outcome-aware morning review after two sample native responses were inspected; not preregistered. Applied to all 72 fixed native controls, every arm.','limits':['A first choice is not a valid complete native response or coherent rationale.','Some N rationales contradict their initial choice or assign incorrect deontic status.','No old score, strict parser result, or uncalled decision is replaced.','Five selected disagreement controls are not the full 25-row disagreement diagnostic.','Native and constrained formats differ in instructions/serialization/decoding; this does not isolate a single cause.'],'sources':{'ledger_sha256':sha(S/'raw/ledger.jsonl'),'validation_records_sha256':sha(S/'private_validation/records.json')},'summary':summary,'records':records}
(OUT/'first_field_audit.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'arithmetic_and_manifest_checks.json').write_text(json.dumps({'payloads_verified':len(manifest['files']),'hash_mismatches':bad,'method':'Independent consequence-table arithmetic from saved joint commitments; no production scoring function imported. Equal worlds within family, then equal families; confirms given parent grouping.','human':human},indent=2)+'\n')
print(json.dumps({'hashes':len(manifest['files']),'protected_human':{k:v for k,v in human['protected'].items() if k not in ['families','by_case']},'first_field_summary':summary},indent=2))
