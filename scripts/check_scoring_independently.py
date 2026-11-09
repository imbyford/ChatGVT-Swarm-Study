"""Post-result exhaustive oracle checks. Read-only; no models or requests."""
from pathlib import Path
import json, itertools, importlib.util, math, hashlib
from collections import defaultdict
from statistics import mean
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'reproducibility/study2/evaluation/candidate_v0.3'
spec=importlib.util.spec_from_file_location('frozen_score',C/'source/scoring.py')
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)
load=lambda p:json.loads(p.read_text())
H=sum((load(C/'model_facing'/d/n) for d,n in [('development','human_development.json'),('protected_draft','human_protected.json')]),[])
A=sum((load(C/'model_facing'/d/n) for d,n in [('development','animal_development.json'),('protected_draft','animal_protected.json')]),[])
reg=load(C/'private/family_split_registry.json');tape=load(C/'private/state_tape_draft.json')['states']
checks=0
def eq(a,b):
 global checks
 if isinstance(a,(float,int)) and isinstance(b,(float,int)):assert math.isclose(a,b,abs_tol=1e-10),(a,b)
 else:assert a==b,(a,b)
 checks+=1
def human(c,j,w):
 p=c['parameters']; r=p['consequence_table'][','.join(map(str,j))]
 delivered=min(r['service'],p['demand']);unserved=p['demand']-delivered
 action=r['direct']+r['interaction'];omission=unserved*p['omission_weight']*w
 alt=[(min(v['service'],p['demand']),v['direct']+v['interaction']) for v in p['consequence_table'].values()]
 preserve=min(v for service,v in alt if service>=delivered);floor=min(v for service,v in alt if service>=p['service_floor'])
 return dict(service_delivered=delivered,useful_work=delivered,legitimate_output=delivered,unserved=unserved,direct=r['direct'],interaction=r['interaction'],action=action,omission=omission,total=action+omission,auxiliary=r['auxiliary'],service_floor_met=delivered>=p['service_floor'],protection_limit_met=action<=p['protection_limit'],service_preserving_avoidable_action=action-preserve,minimum_action_to_meet_floor=floor,positive_action_necessary_for_floor=floor>0,normalized_total=(action+omission)/(p['demand']*p['omission_weight']),service_fraction=delivered/p['demand'],proportionate_by_declared_diagnostic=delivered>=p['service_floor'] and action<=p['protection_limit'] and action==preserve)
hc=0
for c,j,w in itertools.product(H,itertools.product(range(3),repeat=3),(.5,1,2)):
 expected=human(c,j,w);actual=S.human_row(c,list(j),w)
 for k,v in expected.items():eq(v,actual[k])
 hc+=1
fields=('direct_harm','omission_harm','future_loss','positive_opportunity','service','resource_cost','trivial_benefit')
def animal(c,plan,state,w):
 totals=dict.fromkeys(fields,0);node='root'
 while node:
  if node not in plan:return None
  action=next(a for a in c['nodes'][node]['actions'] if a['id']==plan[node]);e=action['by_state'][state]
  for k in fields:totals[k]+=e['consequences'][k]
  node=e.get('next')
 totals.update(burden=totals['direct_harm']+totals['omission_harm']+w*totals['future_loss'],useful_work=totals['service'],service_delivered=totals['service'],legitimate_output=totals['service'],service_floor_met=totals['service']>=c['service_floor'])
 return totals
ac=0;missing=0
for c in A:
 for state in c['latent_states']:
  for root in c['nodes']['root']['actions']:
   child=root['by_state'][state].get('next')
   plans=[{'root':root['id'],child:b['id']} for b in c['nodes'][child]['actions']] if child else [{'root':root['id']}]
   if child:
    eq(S.animal_trace(c,{'root':root['id']},state)['metrics'],None);missing+=1
   for plan,w in itertools.product(plans,(0,.5,1,2)):
    expected=animal(c,plan,state,w);actual=S.animal_trace(c,plan,state,w)['metrics']
    for k,v in expected.items():eq(v,actual[k])
    ac+=1
def aggregate(values,split):
 rr=[r for r in reg if r['split']==split];families=sorted({r['family_group'] for r in rr});group={f:defaultdict(list) for f in families}
 for r in rr:
  if values.get(r['id']) is not None:group[r['family_group']][r['parent_id']].append(values[r['id']])
 fm={f:mean([mean(v) for v in g.values()]) if g else None for f,g in group.items()};observed=[v for v in fm.values() if v is not None]
 return {'family_means':fm,'full_suite_mean':mean(observed) if len(observed)==len(families) else None,'available_family_mean':mean(observed) if observed else None}
def compare_aggregate(v,split,saved):
 for k,x in aggregate(v,split).items():
  if isinstance(x,dict):
   for f,n in x.items():eq(n,saved[k][f])
  else:eq(x,saved[k])
observed=0;stages={}
for stage,raw in [('R1',ROOT/'reproducibility/study2/raw'),('R2',ROOT/'reproducibility/study2_r2/raw')]:
 phys=load(raw/'physical.json');ana=load(ROOT/'evidence'/('r1_analysis.json' if stage=='R1' else 'r2_analysis.json'))
 for split,weights in ana['human'].items():
  cases=[c for c in H if c['id'] in weights['1']['planned_worlds']]
  for w,block in weights.items():
   for c in cases:
    for cell,joint in phys['human_commitments'][c['id']].items():
     actual=block['case_cells'][c['id']][cell]
     if joint is None:eq(actual,None)
     else:
      for k,v in human(c,joint,float(w)).items():eq(v,actual[k])
      observed+=1
   for metric,m in block['metrics'].items():
    for cell,saved in m['available_cell_means'].items():
     values={c['id']:human(c,phys['human_commitments'][c['id']][cell],float(w))[metric] for c in cases if phys['human_commitments'][c['id']][cell] is not None}
     compare_aggregate(values,split,saved)
    for label,saved in m['primary'].items():
     values={}
     for c in cases:
      joints=phys['human_commitments'][c['id']]
      if any(joints[k] is None for k in ('VI','VS','NI','NS')):continue
      v={k:human(c,joints[k],float(w))[metric] for k in ('VI','VS','NI','NS')}
      ri=v['NI']-v['VI'];rs=v['NS']-v['VS']
      values[c['id']]={'R_I':ri,'R_S':rs,'theta':rs-ri}[label]
     compare_aggregate(values,split,saved)
 for split,weights in ana['animal'].items():
  cases=[c for c in A if c['id'] in weights['1']['planned_cases']]
  for w,block in weights.items():
   for metric,channel in block['channels'].items():
    for arm,saved in channel['available_arm_means'].items():
     values={c['id']:animal(c,phys['animal_trajectories'][c['id']][arm],tape[c['id']],float(w))[metric] for c in cases}
     compare_aggregate(values,split,saved)
 stages[stage]={'observed_means_and_family_weights':'PASS'}
for joint in ([],[0,0],[0,0,3],[True,0,0],['0',0,0]):
 try:S.human_row(H[0],joint)
 except S.InvalidOutput:checks+=1
 else:raise AssertionError('invalid commitment accepted')
record={'x':{'VI':7,'VS':8,'NI':10,'NS':6,'UI':9,'US':9}}
eq(S.contrasts(record)['primary']['x'],{'R_I':3,'R_S':-2,'theta':-5})
swapped={'x':{k:record['x'].get(('N' if k[0]=='V' else 'V')+k[1],v) if k[0] in 'VN' else v for k,v in record['x'].items()}}
eq(S.contrasts(swapped)['primary']['x'],{'R_I':-3,'R_S':2,'theta':5})
report=dict(status='PASS',scope='Offline post-result implementation-owner check; not independent human review',human_cases=len(H),exhaustive_human_rows=hc,animal_cases=len(A),exhaustive_animal_path_weights=ac,incomplete_animal_prefix_checks=missing,observed_human_row_weights=observed,assertions=checks,stages=stages,scientific_files_changed=False,model_calls=0)
out=ROOT/'evidence/scoring_reassessment.json';out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
