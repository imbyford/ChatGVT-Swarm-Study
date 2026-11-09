from pathlib import Path
import json,itertools,hashlib,collections
R=Path(__file__).resolve().parents[1]
load=lambda p:json.loads((R/p).read_text())
H=load('model_facing/development/human_development.json')+load('model_facing/protected_draft/human_protected.json')
A=load('private/animal_source_with_tapes.json'); reg=load('private/family_split_registry.json'); byid={r['id']:r for r in reg}
perms=list(itertools.permutations(range(3))); joints=list(itertools.product(range(3),repeat=3))
def sig(c,rank=False):
 p=c['parameters']; vals={tuple(map(int,k.split(','))):(r['service'],r['direct']+r['interaction']) for k,r in p['consequence_table'].items()}
 if rank:
  maps=[{v:i for i,v in enumerate(sorted({r[j] for r in vals.values()}))} for j in range(2)]
  vals={k:tuple(maps[j][r[j]] for j in range(2)) for k,r in vals.items()}
 best=None
 for roleperm in perms:
  for actions in itertools.product(perms,repeat=3):
   seq=[]
   for t in joints:
    original=[0,0,0]
    for j in range(3): original[roleperm[j]]=actions[j][t[j]]
    seq.extend(vals[tuple(original)])
   seq=tuple(seq)
   if best is None or seq<best: best=seq
 return hashlib.sha256(repr(best).encode()).hexdigest()
hsig={c['id']:{'exact_service_action':sig(c),'rank_service_action':sig(c,True)} for c in H}
matches=[]
for a,b in itertools.combinations(H,2):
 for kind in ['exact_service_action','rank_service_action']:
  if hsig[a['id']][kind]==hsig[b['id']][kind]: matches.append({'a':a['id'],'b':b['id'],'kind':kind,'same_split':byid[a['id']]['split']==byid[b['id']]['split']})
graphgroups=collections.defaultdict(list)
for c in A:
 # Coarse graph signature deliberately ignores all moral/content semantics.
 children=sorted(sum(bool(e['next']) for e in a['by_state'].values()) for a in c['nodes']['root']['actions'])
 graphgroups[str(children)].append(c['id'])
report={'status':'LOCAL_SELF_CHECK_ONLY_NOT_FINISHED_CORPUS_AUDIT','data_accessed':'Only newly authored evaluator cases. No curriculum corpus, prompts, completions or target keys accessed.','human_method':'Canonical service/action-harm matrices under all 6 role permutations and 6^3 within-role action permutations; exact and per-column rank-normalized signatures. Auxiliary excluded because it is not verified service.','human_comparisons':66,'human_permutation_maps_per_signature':1296,'human_detected_matches':matches,'human_signatures':hsig,'animal_coarse_graph_groups':dict(graphgroups),'animal_interpretation':'Shared depth/two-state branching is imposed by the interface and is not evidence of an independent solution template. No graph-only claim of separation. Ordinary-use, stochastic-route and unresolved-interest profiles were grouped by substantive solution structure.','cross_split_residuals':['Contingent feedback/maintenance is shared between development A_directional_feedback and protected A_ordinary_use_controls; no copied case or numeric path identified, but separate structural auditor must decide whether the shared decision skeleton requires grouping or replacement.','Human scheduling, compatibility, capacity, approvals, publication, deadlines and role-local authority recur across contexts and in the supplied abstract handoff. Similar primitives are not complete-template clearance.','Burden/benefit comparison, harmful inaction and proportionality recur intentionally across every split.'],'external_audit_status':'PENDING_FULL_CURRICULUM_ABSTRACT_REGISTRY_AND_SEPARATE_FINISHED_CORPUS_REVIEW','limitations':['Exact or rank matrix nonmatches do not rule out semantic paraphrase, threshold variation or reused solution templates.','No full train–test separation conclusion can be drawn.','This was performed by the author, not an independent reviewer.']}
(R/'review/local_structural_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'human_pairs':66,'permutation_maps':1296,'matches':matches,'animal_graph_groups':dict(graphgroups)},indent=2))
