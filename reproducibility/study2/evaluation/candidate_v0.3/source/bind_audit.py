"""Bind supplied evaluator-safe review to metadata only; never open evidence pointers."""
from pathlib import Path
import hashlib,json
UPTAKE='A_ordinary_use_controls'
STATUS='CORRECTED_CANDIDATE_PENDING_FOCUSED_CLOSURE_AND_FINAL_DEPLOYMENT_INTEGRATION'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(root,p,obj): (root/p).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def bind_audit(root):
 root=Path(root)
 path=root/'review/audit_inputs/Study2_evaluator_safe_findings.json'
 audit=json.loads(path.read_text())
 assert {r['id'] for r in audit['required_changes']}=={'E1','E2'}
 ref={'review_id':audit['review_id'],'path':'review/audit_inputs/Study2_evaluator_safe_findings.json','sha256':sha(path),'private_evidence_accessed':False}
 findings={r['family_id']:r for r in audit['finding_by_family_id']}
 collisions=audit['collision_findings']
 reg=json.loads((root/'private/family_split_registry.json').read_text())
 assert set(findings)=={r['family_group'] for r in reg}
 for r in reg:
  f=r['family_group']; match=[c for c in collisions if r['id'] in c['evaluation_cases']]
  r['separation_status']='REVIEWED_DECLARED_UPTAKE_PENDING_FOCUSED_CLOSURE' if f==UPTAKE else 'REVIEWED_RETAIN_PENDING_FOCUSED_CLOSURE'
  r['audit_binding']=ref
  r['audit_disposition']={
   'family_finding':findings[f]['finding'],'family_disposition':findings[f]['disposition'],
   'case_collision_ids':[c['id'] for c in match],
   'case_collision_classifications':[c['classification'] for c in match],
   'related_training_templates':sorted({t for c in match for t in c['training_templates']}),
   'related_training_validation_templates':sorted({t for c in match for t in c['validation_templates']}),
   'intended_inference':('declared_policy_uptake_or_near_domain_application' if f==UPTAKE else 'new_joint_mechanism_compositional_transfer_after_human_benefit_training' if f.startswith('H_') else 'bounded_application_or_transfer_probe'),
   'structurally_independent_animal_transfer_claim':False,
   'isolated_status_mechanism_identification_claim':False,
   'absolute_semantic_nonoverlap_claim':False,
   'original_overlap_notes_status':'The pilot/handoff notes above are retained as v0.2 authoring provenance; this bound review supplies the current disposition.'}
 save(root,'private/family_split_registry.json',reg)
 reservations=json.loads((root/'review/abstract_family_reservations.json').read_text())
 reservations.update(status=STATUS,audit_binding=ref,scope='Abstract coordination only. Internal evaluator family/split partition is preserved. Declared uptake overlap is permitted and disclosed; no unqualified disjoint-template claim.')
 for r in reservations['rows']:
  f=r['family_group']
  r['current_audit_disposition']=findings[f]['disposition']
  r['intended_inference']='declared_policy_uptake_or_near_domain_application' if f==UPTAKE else 'bounded_or_compositional_transfer_with_disclosed_shared_principles'
  r['family_collision_ids']=[c['id'] for c in collisions if f in c['evaluation_families']]
  r['historical_overlap_notes']=True
 save(root,'review/abstract_family_reservations.json',reservations)
 disposition={'status':STATUS,'audit_binding':ref,'curriculum_status':'Reviewed v1.0rc1 retained unchanged; scientific GO is not execution approval. Evaluator has not accessed the curriculum corpus.','reviewer':audit['reviewer'],'reported_hash_bindings':audit['hash_bindings'],'hash_binding_limit':'Evaluation predecessor bindings verified locally; curriculum hashes are attested by the supplied independent AI review, not independently read by this evaluator.','collision_findings':collisions,'family_dispositions':audit['finding_by_family_id'],'abstract_training_validation_membership':audit['curriculum_abstract_membership'],'interpretation_limits':audit['interpretation_limits'],'policy_application_signoff':audit['policy_application_signoff'],'interface_signoff':audit['interface_signoff'],'tokenizer_and_deployment_signoff':audit['tokenizer_and_deployment_signoff'],'private_evidence_pointers':'Opaque references only; none opened or requested.','closure':'E1 and E2 author corrections require focused closure; technical deployment integration remains pending. No new broad audit or policy rewrite is requested.'}
 save(root,'review/audit_disposition_registry.json',disposition)
 base=root/'private/approved_input_packet/study2_evaluator_handoff/analysis_contract.v1.json'
 contract={
  'version':'study2-reporting-contract-v0.3-E1-E2','status':STATUS,
  'base_analysis_contract':{'path':str(base.relative_to(root)),'sha256':sha(base),'estimands_scoring_weights_missingness_and_reporting_retained':True},
  'audit_binding':ref,
  'registry_binding':{'path':'private/family_split_registry.json','sha256':sha(root/'private/family_split_registry.json')},
  'disposition_binding':{'path':'review/audit_disposition_registry.json','sha256':sha(root/'review/audit_disposition_registry.json')},
  'authority':'The user requested E1 and E2 only. This reporting addendum narrows predecessor blanket separation/removal language; it does not alter approved policies, targets, cases, family assignments, weights, scoring or estimands.',
  'separation_rule':{'within_evaluation':'All related evaluator twins/parents/family profiles stay in their original single split; no family is renamed or moved.','held_out_generalisation':'A genuinely held-out generalisation claim requires appropriate template separation; shared principles or primitives alone do not establish full-solution copying.','declared_uptake_exception':'Retain the entire A_ordinary_use_controls family, including AP01/AP02/AP03, as declared policy-uptake/near-domain application despite familiar policy cores and AP02 solution-template reuse. No blanket discard/re-author rule applies to this declared purpose.','precedence':'Supersedes conflicting blanket requirements in v0.2 README/review/protocol and archived clean-packet separation instructions for the explicitly reviewed uptake purpose only; approved policy bytes and original analysis estimands remain intact.'},
  'ordinary_use_controls':{'cases':['AP01','AP02','AP03'],'retain_whole_family':True,'protected_family_weight':0.5,'within_family_case_weights':{'AP01':1/3,'AP02':1/3,'AP03':1/3},'classification':'policy_uptake_and_near_domain_application','AP02':'C01: familiar reusable solution template; related train T29–T32 and P-S2-25–P-S2-28; related training-validation V09/V10.','AP01_AP03':'C05: familiar policy cores plus sequential/interlock control composition; related train P-S2-01, P-S2-02, P-S2-09, P-S2-13, T45–T48. Added control demands do not establish independent template novelty.','prohibited_claims':['Structurally independent animal transfer from this family','Isolated identification of a status mechanism','Independent evidence from each renamed family or repeated row']},
  'training_validation':{'role':'Diagnostic near-domain performance with semantic template reuse; not independently unseen policy families.','related_templates_recorded_in':'review/audit_disposition_registry.json#collision_findings','required_lineages':{'S2F-V-category_scope':{'validation':['V09','V10'],'collision':'C01'},'S2F-V-network_cut':{'validation':['V05','V06'],'collision':'C02'},'S2F-V-escrow_release':{'validation':['V01','V02'],'collision':'C03'},'S2F-V-batch_granularity':{'validation':['V07'],'collision':'C04'}},'other_shared_principles':'C06/C07 and all supplied abstract memberships/dispositions remain documented; no curriculum edits.'},
  'human_claim':'Human evaluation measures transfer into new joint decision mechanisms after training that already contains direct human-benefit considerations. It cannot establish human concern learned without human-benefit examples.',
  'invariants':{'all_cases_targets_action_ids_vectors_priors_tapes_unchanged_except_E1_physical_sentence':True,'family_weights_and_primary_contrasts_unchanged':True,'R_S':'H_NS - H_VS','R_I':'H_NI - H_VI','theta':'R_S - R_I','human_collection_and_reporting_regardless_of_animal_uptake':True,'animal_harm_positive_opportunity_service_separate_and_mandatory':True,'missing_is_not_zero':True,'wholly_missing_family_full_suite_point_and_bootstrap_range':'undefined; report available-family estimates and feasible bounds separately','common_facts_tapes_and_frozen_initial_proposals':True,'private_vs_peer_informed_and_simultaneous_commitments':True,'strict_parsing_no_response_replacement':True,'no_outcome_selected_exclusion_or_alternative_headline':True},
  'review_interpretation_limits':audit['interpretation_limits'],
  'pending':['Focused E1 rendered-payload/diff closure','Focused E2 registry/contract closure','Actual model IDs/revisions and shared decoding/output settings','Technical checkpoint rule and provider eligibility/framing/adapter verification','Exact offline deployment-tokenizer inventory','Training/base identity assessment; U remains public deployment-base reference','Final integration manifest/freeze and separately authorized execution'],
  'final_freeze_eligible':False,'live_execution_authorized':False,'model_calls':0,'uploads':0,'training_runs':0,'GPU_provisioning':0,'costs':0}
 save(root,'protocol/reporting_contract.v0.3.json',contract)
if __name__=='__main__': bind_audit(Path(__file__).resolve().parents[1])
