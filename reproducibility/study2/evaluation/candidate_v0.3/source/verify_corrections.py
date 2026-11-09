"""Focused offline E1/E2 verification against the preserved v0.2 artifacts."""
from pathlib import Path
import argparse,copy,difflib,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from prompts import animal_request
from analysis import animal_analysis
SENTENCE='For the two active corridors and their continuations, each unit of direct harm denotes the same amount of animal-time at the same fixed severity, across all bridge states.'
APPEND='\n# Successor reporting metadata: evaluator-safe audit only; no private training evidence.\nimport sys\nsys.path.insert(0,str(ROOT/"source"))\nfrom bind_audit import bind_audit\nbind_audit(ROOT)\n'
parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path,default=ROOT.parent/'Study2_Evaluation_Draft_v0.2');args=parser.parse_args();BASE=args.baseline.resolve()
checks=[]
def check(v,label):
 checks.append({'check':label,'pass':bool(v)})
 if not v: raise AssertionError(label)
def read(root,p):return json.loads((root/p).read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):(ROOT/p).write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n')
def canon(o):return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def unchanged(p):check((ROOT/p).read_bytes()==(BASE/p).read_bytes(),'byte-identical '+p)
def strip_e1(cases):
 cp=copy.deepcopy(cases)
 c=next(c for c in cp if c['id']=='AD03');obs=c['nodes']['root']['observation']
 check(obs.count(SENTENCE)==1,'exact E1 sentence once in AD03 root')
 c['nodes']['root']['observation']=obs.replace(' '+SENTENCE,'')
 return cp
# Prove that the reviewed predecessor is the baseline actually compared.
audit=read(ROOT,'review/audit_inputs/Study2_evaluator_safe_findings.json')
for p,h in audit['hash_bindings']['evaluation_case_files'].items():check(digest(BASE/p)==h,'review predecessor binding '+p)
for p,h in audit['hash_bindings']['evaluation_source'].items():check(digest(BASE/p)==h,'review predecessor binding '+p)
for k,p in [('evaluation_registry','private/family_split_registry.json'),('evaluation_draft_manifest','private/DRAFT_INTEGRITY_MANIFEST.json'),('protocol','protocol/PROTOCOL_AND_ANALYSIS.txt')]:check(digest(BASE/p)==audit['hash_bindings'][k],'review predecessor binding '+k)
check({r['id'] for r in audit['required_changes']}=={'E1','E2'},'exactly E1 and E2')
# Numerical/policy/scoring invariants: exact bytes, not merely equivalent examples.
for p in ['private/animal_keys.json','private/human_keys.json','private/state_tape_draft.json','review/family_balance.json','protocol/request_slots.json','protocol/runtime_ledger_schema.json','source/prompts.py','source/scoring.py','source/analysis.py','source/plan.py','source/validate.py','source/local_overlap.py','private/all_human_commitments.json','private/all_animal_paths.json','private/all_animal_strategies.json','validation/check_report.json']:
 unchanged(p)
for p in sorted((BASE/'private/approved_input_packet').rglob('*')):
 if p.is_file():unchanged(str(p.relative_to(BASE)))
for p in ['model_facing/development/human_development.json','model_facing/protected_draft/human_protected.json','model_facing/protected_draft/animal_protected.json']:
 unchanged(p)
for p in ['model_facing/development/animal_development.json','private/animal_source_with_tapes.json']:
 check(strip_e1(read(ROOT,p))==read(BASE,p),'only AD03 root observation changed in '+p)
oldphrase='The downstream bridge state is revealed only after committing a corridor; no inspection is feasible.'
check((ROOT/'private/build_cases.py').read_text()==(BASE/'private/build_cases.py').read_text().replace(oldphrase,oldphrase+' '+SENTENCE)+APPEND,'authoritative source only E1 sentence and E2 metadata binder')
check((ROOT/'model_facing/CASEBOOK.txt').read_text()==(BASE/'model_facing/CASEBOOK.txt').read_text().replace(oldphrase,oldphrase+' '+SENTENCE),'regenerated casebook only factual clarification')
notes=(BASE/'private/POLICY_APPLICATION_NOTES.txt').read_text()
check('AD01/AD03 use known probabilities and the same severity/duration units.' in notes,'comparability already intended in predecessor author notes')
old=read(BASE,'private/rendered_initial_requests.json');new=read(ROOT,'private/rendered_initial_requests.json')
check(set(old)==set(new),'initial request set unchanged')
for k,p in new.items():
 if k!='AD03/root':check(p==old[k],'unchanged initial payload '+k)
 else:
  check(p['system']==old[k]['system'],'AD03 neutral system unchanged')
  check(p['user'].replace(' '+SENTENCE,'')==old[k]['user'],'AD03 user payload only E1 sentence')
case=next(c for c in read(ROOT,'private/animal_source_with_tapes.json') if c['id']=='AD03')
slots=[s for s in read(ROOT,'protocol/request_slots.json') if s['case_id']=='AD03' and s['phase']=='root']
check({s['arm'] for s in slots}=={'V','N','U'},'all three AD03 arm slots present')
arm_payloads=[]
for slot in slots:
 p=animal_request(case,'root');check(p==new[slot['payload_inventory_id']],'arm slot uses actual rendered payload '+slot['arm'])
 parsed=json.loads(p['user']);check(parsed['common_facts']['nodes']['root']['observation'].endswith(SENTENCE),'sentence reaches '+slot['arm'])
 check('tape_state' not in parsed['common_facts'],'no private tape in '+slot['arm'])
 check(all(s not in p['user'] for s in ['2.6','V2/V4','N1/N5','policy_keys','factual_keys','required selection under V']),'no key or expected-value ranking in '+slot['arm'])
 arm_payloads.append({'arm':slot['arm'],'request_id':slot['request_id'],'payload_inventory_id':slot['payload_inventory_id'],'system_sha256':hashlib.sha256(p['system'].encode()).hexdigest(),'user_sha256':hashlib.sha256(p['user'].encode()).hexdigest(),'canonical_payload_sha256':hashlib.sha256(canon(p)).hexdigest(),'model_payload':p})
check(len({r['canonical_payload_sha256'] for r in arm_payloads})==1,'identical system/user bytes across V N U')
check(not any(x in SENTENCE for x in ['north','south','2.6','preferred','required','recommended','V policy','N policy']),'added sentence states physical units not an answer or moral rule')
evidence={'status':'PASS_OFFLINE_RENDERING_NOT_LIVE_ADAPTER','revision_status':'Corrected candidate pending focused closure and final deployment integration','sentence':SENTENCE,'already_intended_physical_premise':{'confirmed':True,'predecessor_source':'private/POLICY_APPLICATION_NOTES.txt','predecessor_quote':'AD01/AD03 use known probabilities and the same severity/duration units.','predecessor_key_basis_retained':True,'discrepancy_found':False},'source_sha256':digest(ROOT/'private/build_cases.py'),'derived_case_sha256':digest(ROOT/'model_facing/development/animal_development.json'),'casebook_sha256':digest(ROOT/'model_facing/CASEBOOK.txt'),'initial_inventory_sha256':digest(ROOT/'private/rendered_initial_requests.json'),'payloads':arm_payloads,'all_arm_bytes_identical':True,'system_unchanged':True,'only_added_payload_content':SENTENCE,'answer_or_expected_ranking_added':False,'policy_instruction_added':False,'private_keys_or_tape_in_payload':False,'continuation_note':'The unchanged renderer includes the complete common facts at child requests too; the same factual sentence therefore also adds bytes to AD03 continuations.','model_calls':0,'provider_adapter_verified':False}
save('validation/E1_rendered_payload_evidence.json',evidence)
# Exact request/inventory delta: six maximum slots (three roots + three continuations).
oldinv={r['slot_id']:r for r in read(BASE,'protocol/prompt_byte_inventory.json')};newinv={r['slot_id']:r for r in read(ROOT,'protocol/prompt_byte_inventory.json')}
check(set(oldinv)==set(newinv),'inventory slot set unchanged');increment=len((' '+SENTENCE).encode())
for k,row in newinv.items():
 expected=copy.deepcopy(oldinv[k])
 if k in ['AD03/root','AD03/continuation']:
  for field in ['system_plus_user_utf8_bytes_min','system_plus_user_utf8_bytes_max']:expected[field]+=increment
 check(row==expected,'only intended byte inventory delta '+k)
oldplan=read(BASE,'protocol/request_plan.json');newplan=read(ROOT,'protocol/request_plan.json');expected=copy.deepcopy(oldplan)
expected['payload_utf8_bytes_upper_sum']+=6*increment
expected['max_single_payload_utf8_bytes']=max(v['system_plus_user_utf8_bytes_max'] for v in newinv.values())
check(newplan==expected,'request plan only derived input byte totals change')
# Complete E2 binding and no changes to evaluator partition/weights or primary analysis.
reg=read(ROOT,'private/family_split_registry.json');oldreg=read(BASE,'private/family_split_registry.json')
check(len(reg)==len(oldreg)==20,'all cases retained')
findings={f['family_id']:f for f in audit['finding_by_family_id']}
check({r['family_group'] for r in reg}==set(findings) and len(findings)==15,'all 15 families have supplied dispositions')
for oldrow,row in zip(oldreg,reg):
 check({k:v for k,v in row.items() if k not in ['separation_status','audit_binding','audit_disposition']}=={k:v for k,v in oldrow.items() if k!='separation_status'},'registry identity/structure retained '+row['id'])
 check(row['audit_binding']['sha256']==digest(ROOT/'review/audit_inputs/Study2_evaluator_safe_findings.json'),'audit hash bound '+row['id'])
 check(row['audit_disposition']['family_disposition']==findings[row['family_group']]['disposition'],'family disposition bound '+row['id'])
expectedcases={'AP01','AP02','AP03'}
check({r['id'] for r in reg if r['family_group']=='A_ordinary_use_controls'}==expectedcases,'whole ordinary-use family retained')
for r in reg:
 if r['id'] in expectedcases:
  d=r['audit_disposition'];check(d['intended_inference']=='declared_policy_uptake_or_near_domain_application' and not d['structurally_independent_animal_transfer_claim'] and not d['isolated_status_mechanism_identification_claim'],'uptake not independent/status identification '+r['id'])
  check(d['case_collision_ids']==(['C01'] if r['id']=='AP02' else ['C05']),'correct familiar template/core classification '+r['id'])
dispositions=read(ROOT,'review/audit_disposition_registry.json');contract=read(ROOT,'protocol/reporting_contract.v0.3.json')
check(dispositions['collision_findings']==audit['collision_findings'],'all seven collision findings bound unchanged')
check(dispositions['family_dispositions']==audit['finding_by_family_id'],'all family findings bound unchanged')
check(dispositions['abstract_training_validation_membership']==audit['curriculum_abstract_membership'],'all supplied abstract training-validation membership retained')
check(dispositions['interpretation_limits']==audit['interpretation_limits'],'all reviewer interpretation limits retained')
check(contract['registry_binding']['sha256']==digest(ROOT/'private/family_split_registry.json'),'contract binds updated registry')
check(contract['disposition_binding']['sha256']==digest(ROOT/'review/audit_disposition_registry.json'),'contract binds complete disposition')
check(contract['base_analysis_contract']['sha256']==audit['hash_bindings']['analysis_contract'],'original primary analysis contract hash retained')
check(contract['ordinary_use_controls']['protected_family_weight']==0.5 and all(v==1/3 for v in contract['ordinary_use_controls']['within_family_case_weights'].values()),'uptake family/profile weights retained')
check(set(contract['training_validation']['required_lineages'])=={'S2F-V-category_scope','S2F-V-network_cut','S2F-V-escrow_release','S2F-V-batch_granularity'},'four requested validation lineages recorded')
check('already contains direct human-benefit' in contract['human_claim'],'human-benefit training limitation explicit')
for name in ['human_collection_and_reporting_regardless_of_animal_uptake','animal_harm_positive_opportunity_service_separate_and_mandatory','missing_is_not_zero','common_facts_tapes_and_frozen_initial_proposals','private_vs_peer_informed_and_simultaneous_commitments','strict_parsing_no_response_replacement','no_outcome_selected_exclusion_or_alternative_headline']:
 check(contract['invariants'][name] is True,'retained invariant '+name)
empty=animal_analysis(read(ROOT,'private/animal_source_with_tapes.json'),reg,{},'animal_protected')
for channel in ['burden','positive_opportunity','service']:
 s=empty['channels'][channel]['NV_contrast'];check(s['full_suite_mean'] is None and s['family_resampling_95_range'] is None and len(s['missing_families'])==2,'missing-family undefined with required channel '+channel)
check(contract['live_execution_authorized'] is False and contract['final_freeze_eligible'] is False,'candidate is not execution approval or final freeze')
checklist={'status':'PASS_AUTHOR_IMPLEMENTATION_PENDING_FOCUSED_CLOSURE','audit_sha256':digest(ROOT/'review/audit_inputs/Study2_evaluator_safe_findings.json'),'registry_sha256':digest(ROOT/'private/family_split_registry.json'),'reporting_contract_sha256':digest(ROOT/'protocol/reporting_contract.v0.3.json'),'every_family_documented':True,'family_count':15,'protected_human_families':7,'protected_animal_families':2,'family_dispositions':dispositions['family_dispositions'],'collision_dispositions':audit['collision_findings'],'whole_ordinary_family_retained_as_uptake':True,'AP02_familiar_solution_template':'C01','AP01_AP03_familiar_policy_cores':'C05','training_validation_semantic_reuse_documented':True,'human_benefit_training_limitation_explicit':True,'cases_names_splits_weights_primary_contrasts_scoring_targets_preserved':True,'no_policy_reopening':True,'no_case_replacement_or_expansion':True,'blanket_removal_rule_narrowed_to_respect_declared_uptake':True,'mandatory_harm_opportunity_service_and_all_human_outcomes_retained':True,'missing_family_undefined_retained':True,'private_training_evidence_accessed':False,'curriculum_edited':False,'fresh_broad_audit_performed':False,'focused_closure_pending':True,'final_deployment_integration_pending':True,'live_execution_authorized':False}
save('validation/E2_disposition_checklist.json',checklist)
save('validation/correction_check_report.json',{'status':'PASS','scope':'Offline author verification of exactly E1/E2, not independent focused closure or tested provider integration.','checks':checks,'check_count':len(checks),'model_calls':0,'uploads':0,'training':0,'GPUs':0,'costs':0})
# A focused, machine-readable diff plus a concise textual source/fact/contract review.
oldfiles={str(p.relative_to(BASE)):p for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
newfiles={str(p.relative_to(ROOT)):p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
ignore={'validation/focused_diff.json','validation/FOCUSED_DIFF.txt','private/CANDIDATE_INTEGRITY_MANIFEST_v0.3.json','validation/reproduction_report.json'}
changed=[];same=[];added=[];removed=[]
for p in sorted(set(oldfiles)|set(newfiles)):
 if p in ignore:continue
 if p not in oldfiles:added.append({'path':p,'sha256':digest(newfiles[p])})
 elif p not in newfiles:removed.append({'path':p,'sha256':digest(oldfiles[p])})
 elif digest(oldfiles[p])==digest(newfiles[p]):same.append({'path':p,'sha256':digest(newfiles[p])})
 else:changed.append({'path':p,'old_sha256':digest(oldfiles[p]),'new_sha256':digest(newfiles[p])})
allowed={'README.txt','model_facing/README.txt','model_facing/CASEBOOK.txt','model_facing/development/animal_development.json','private/animal_source_with_tapes.json','private/build_cases.py','private/rendered_initial_requests.json','protocol/prompt_byte_inventory.json','protocol/request_plan.json','private/family_split_registry.json','review/abstract_family_reservations.json','protocol/PROTOCOL_AND_ANALYSIS.txt','review/FINAL_REVIEW_REQUIREMENTS.txt','private/POLICY_APPLICATION_NOTES.txt','review/coverage_and_limitations.json','review/local_structural_audit.json','private/INPUT_PROVENANCE.json','private/AUTHORING_CHANGELOG.json'}
check({r['path'] for r in changed}<=allowed,'only intended changed predecessor files')
check([r['path'] for r in removed]==['private/DRAFT_INTEGRITY_MANIFEST.json'],'only old manifest renamed as historical reference')
check((ROOT/'private/V0_2_INTEGRITY_MANIFEST_REFERENCE.json').read_bytes()==(BASE/'private/DRAFT_INTEGRITY_MANIFEST.json').read_bytes(),'historical manifest preserved exact bytes')
save('validation/correction_check_report.json',{'status':'PASS','scope':'Offline author verification of exactly E1/E2, not independent focused closure or tested provider integration.','checks':checks,'check_count':len(checks),'model_calls':0,'uploads':0,'training':0,'GPUs':0,'costs':0})
for item in added: item['sha256']=digest(ROOT/item['path'])
result={'status':'PASS','baseline_directory':str(BASE),'candidate_directory':str(ROOT),'only_case_content_delta':{'case':'AD03','path':'nodes.root.observation','operation':'append one factual sentence','sentence':SENTENCE},'casebook_and_initial_payload_delta':'Same sentence only; all other model-facing task content identical.','inventory_delta':{'AD03_root_utf8_bytes':increment,'AD03_continuation_utf8_bytes':increment,'max_plan_utf8_bytes':6*increment,'request_count':0,'max_output_token_reservation':0},'E2_scope':'Registry, audit dispositions, reporting/claim contract, provenance and review-status reconciliation only.','invariant_files':same,'changed_files':changed,'new_evidence_and_reporting_files':added,'historical_manifest_rename':removed,'excluded_from_self_referential_diff':['This diff JSON and text','Successor candidate manifest','Regeneration/reproduction report'], 'candidate_status':contract['status'],'independent_focused_closure_pending':True}
save('validation/focused_diff.json',result)
lines=['FOCUSED v0.2 -> v0.3 CORRECTION DIFF','PASS — E1/E2 author checks only; focused closure and deployment integration pending.','', 'E1: exactly one physical unit-comparability sentence appended to AD03 root observation.','No other case content, policy key, factual key, action ID, numerical vector, prior or tape changed.','Three rendered root payloads are byte-identical across V/N/U. No expected-value ranking or preferred action was added.',f'AD03 root/continuation payloads each add {increment} UTF-8 bytes; maximum request-plan input increases by {6*increment} bytes. Counts/output caps unchanged.','', 'E2: retain all AP01/AP02/AP03 as one declared policy-uptake/near-domain family.','AP02 C01 familiar template; AP01/AP03 C05 familiar policy cores. C01–C07 and every family disposition are bound.','Training-validation reuse and direct-human-benefit training are explicit. No independent animal-transfer/status-identification claim.','Scoring, primary contrasts, family/profile weights, protected family counts and all missingness/reporting rules are unchanged.','', 'Changed predecessor files:']+[r['path'] for r in changed]+['','Byte-identical invariant files:']+[r['path'] for r in same]+['','Focused source diff:']
lines+=list(difflib.unified_diff((BASE/'private/build_cases.py').read_text().splitlines(),(ROOT/'private/build_cases.py').read_text().splitlines(),fromfile='v0.2/private/build_cases.py',tofile='v0.3/private/build_cases.py',n=2))
lines+=['','Reporting protocol diff:']+list(difflib.unified_diff((BASE/'protocol/PROTOCOL_AND_ANALYSIS.txt').read_text().splitlines(),(ROOT/'protocol/PROTOCOL_AND_ANALYSIS.txt').read_text().splitlines(),fromfile='v0.2/protocol/PROTOCOL_AND_ANALYSIS.txt',tofile='v0.3/protocol/PROTOCOL_AND_ANALYSIS.txt',n=1))
(ROOT/'validation/FOCUSED_DIFF.txt').write_text('\n'.join(lines)+'\n')
save('validation/correction_check_report.json',{'status':'PASS','scope':'Offline author verification of exactly E1/E2, not independent focused closure or tested provider integration.','checks':checks,'check_count':len(checks),'model_calls':0,'uploads':0,'training':0,'GPUs':0,'costs':0})
print(json.dumps({'status':'PASS','focused_checks':len(checks),'changed_predecessor_files':len(changed),'byte_identical_files':len(same),'E1_payload_equal_across_arms':True,'E2_families_bound':len(findings),'max_requests':newplan['planned_max_requests'],'model_calls':0},indent=2))
