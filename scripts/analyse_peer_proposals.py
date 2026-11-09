"""Read-only post-hoc action analysis. No inference, training or network access."""
from pathlib import Path
from collections import defaultdict, Counter
from statistics import mean
import json, hashlib, csv, re, math
P=Path(__file__).resolve().parents[1];R=P/'reproducibility';O=P/'swarm_analysis';O.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
C=R/'study2/evaluation/candidate_v0.3'
cases=sum([read(C/'model_facing'/d/f) for d,f in [('development','human_development.json'),('protected_draft','human_protected.json')]],[])
registry=read(C/'private/family_split_registry.json');reg={r['id']:r for r in registry}
def score(c,values):
 p=c['parameters'];row=p['consequence_table'][','.join(map(str,values))];work=min(p['demand'],row['service']);action=row['direct']+row['interaction'];omission=(p['demand']-work)*p['omission_weight']
 return dict(harm=action+omission,useful_work=work,action_harm=action,direct_harm=row['direct'],interaction_harm=row['interaction'],omission_harm=omission,auxiliary=row['auxiliary'])
def aggregate(values,split):
 fam={r['family_group']:defaultdict(list) for r in registry if r['split']==split}
 for cid,v in values.items():
  r=reg[cid];fam[r['family_group']][r['parent_id']].append(v)
 fm={f:mean(mean(a) for a in parents.values()) if parents else None for f,parents in fam.items()};available=[v for v in fm.values() if v is not None]
 return dict(family_means=fm,full_mean=mean(available) if len(available)==len(fm) else None,available_mean=mean(available) if available else None,observed_worlds=sorted(values),missing_families=[f for f,v in fm.items() if v is None])
def parse(raw,stage,allowed):
 if stage=='R1':
  x=json.loads(raw);a=x.get('action') if x.get('status')=='commit' else None
 else:
  first=next((x for x in raw.splitlines() if x.strip()),'');m=re.fullmatch(r'\s*Choice\s*:\s*([^\r\n]+?)\s*',first,re.I)
  a=m.group(1).strip() if m else None
  if a and a.endswith('.'):a=a[:-1].rstrip()
  if a and len(a)>1 and a[0]==a[-1] and a[0] in ('"',"'",'`'):a=a[1:-1]
 return a if a in allowed else None
case_rows=[];controller_rows=[];summary={};evidence={};visibility=0
for stage,directory in [('R1','study2'),('R2','study2_r2')]:
 root=R/directory;lp=root/'raw/ledger.jsonl';events=[json.loads(x) for x in lp.read_text().splitlines()]
 intents={e['slot']['request_id']:e for e in events if e['event']=='request_intent'};responses={e['request_id']:e for e in events if e['event']=='response'}
 physical=read(root/'raw/physical.json');analysis=read(P/'evidence'/('r1_analysis.json' if stage=='R1' else 'r2_analysis.json'))
 evidence[stage]={'ledger_sha256':sha(lp),'physical_sha256':sha(root/'raw/physical.json'),'saved_analysis_sha256':sha(P/'evidence'/('r1_analysis.json' if stage=='R1' else 'r2_analysis.json'))}
 current=[]
 for c in cases:
  cid=c['id'];split=reg[cid]['split'];roles=c['roles']
  for arm in 'VNU':
   actions={};values={};refs={};statuses={}
   for phase in ('initial','I','S'):
    actions[phase]=[];values[phase]=[];refs[phase]=[];statuses[phase]=[]
    for role in roles:
     rid=f"{cid}/{phase}/{role['id']}/{arm}";q=intents.get(rid);r=responses.get(rid);menu={a['id']:a['value'] for a in role['actions']}
     a=parse(r['reply']['raw'],stage,menu) if r else None
     if r:
      assert hashlib.sha256(r['reply']['raw'].encode()).hexdigest()==r['response_sha256']
      assert hashlib.sha256(json.dumps(q['request'],sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()==q['request_sha256']
      assert (a is not None)==(r['status']=='valid'),rid
      if a is not None:assert a==r['parsed']['action'],rid
     actions[phase].append(a);values[phase].append(menu[a] if a else None);statuses[phase].append(r['status'] if r else 'unstarted')
     refs[phase].append({'request_id':rid,'raw':r['reply']['raw'] if r else None,'raw_text_sha256':hashlib.sha256(r['reply']['raw'].encode()).hexdigest() if r else None,'recorded_request_sha256':q['request_sha256'] if q else None,'recorded_response_sha256':r['response_sha256'] if r else None})
     if q and phase in ('I','S'):
      payload=json.loads(q['request']['messages'][-1]['content']);i=next(i for i,z in enumerate(roles) if z['id']==role['id'])
      assert payload['your_frozen_proposal']==actions['initial'][i]
      if phase=='I':assert 'other_frozen_proposals' not in payload
      else:assert payload['other_frozen_proposals']=={z['id']:actions['initial'][j] for j,z in enumerate(roles) if j!=i}
      visibility+=1
   complete={k:all(a is not None for a in actions[k]) for k in actions}
   if complete['I'] and complete['S']:
    for role in roles:
     qi=intents[f"{cid}/I/{role['id']}/{arm}"]['request'];qs=intents[f"{cid}/S/{role['id']}/{arm}"]['request']
     pi=json.loads(qi['messages'][-1]['content']);ps=json.loads(qs['messages'][-1]['content']);ps.pop('other_frozen_proposals')
     assert pi==ps and qi['messages'][:-1]==qs['messages'][:-1]
     assert {k:v for k,v in qi.items() if k!='messages'}=={k:v for k,v in qs.items() if k!='messages'}
   for phase in ('I','S'):
    expected=values[phase] if complete[phase] else None
    assert expected==physical['human_commitments'][cid][arm+phase],(stage,cid,arm,phase)
   outcomes={k:score(c,values[k]) if complete[k] else None for k in ('I','S')}
   for phase in ('I','S'):
    saved=analysis['human'][split]['1']['case_cells'][cid][arm+phase]
    if outcomes[phase] is not None:
     assert outcomes[phase]['harm']==saved['total'] and outcomes[phase]['useful_work']==saved['useful_work']
   paired=complete['I'] and complete['S'];change=[i for i in range(3) if paired and actions['I'][i]!=actions['S'][i]]
   delta={k:outcomes['S'][k]-outcomes['I'][k] for k in outcomes['I']} if paired else None
   effects=[]
   for i in change:
    hybrid=list(values['I']);hybrid[i]=values['S'][i];counterfactual=score(c,hybrid)
    effects.append({'role':roles[i]['id'],'hypothetical_joint':hybrid,'delta_harm_vs_private':counterfactual['harm']-outcomes['I']['harm'],'delta_work_vs_private':counterfactual['useful_work']-outcomes['I']['useful_work'],'interpretation':'Table-only substitution holding other controllers at private actions; not an observed model response or additive causal attribution.'})
   row=dict(stage=stage,case_id=cid,split=split,family=reg[cid]['family_group'],arm=arm,role_order=[r['id'] for r in roles],actions=actions,values=values,statuses=statuses,complete=complete,outcomes=outcomes,delta_S_minus_I=delta,changed_roles=[roles[i]['id'] for i in change],unilateral_table_substitutions=effects,request_evidence=refs)
   current.append(row);case_rows.append(row)
   for i,role in enumerate(roles):
    initial=actions['initial'][i];ip=actions['I'][i];sp=actions['S'][i]
    controller_rows.append(dict(stage=stage,split=split,case_id=cid,arm=arm,role=role['id'],initial=initial,private=ip,shared=sp,paired=paired,private_vs_shared_changed=(ip!=sp) if paired else None,initial_to_private_changed=(initial!=ip) if initial is not None and ip is not None else None,initial_to_shared_changed=(initial!=sp) if initial is not None and sp is not None else None,joint_delta_harm=delta['harm'] if paired else None,joint_delta_work=delta['useful_work'] if paired else None))
 summary[stage]={}
 for split in ('human_protected','human_development'):
  allr=[r for r in current if r['split']==split];byid={c['id']:{a:next(r for r in allr if r['case_id']==c['id'] and r['arm']==a) for a in 'VNU'} for c in cases if reg[c['id']]['split']==split}
  pairs={p: {'comparable_worlds':[],'identical_initial_worlds':[]} for p in ('VN','VU','NU')}
  for pair,out in pairs.items():
   for cid,r in byid.items():
    a,b=[r[x] for x in pair]
    if a['complete']['initial'] and b['complete']['initial']:
     out['comparable_worlds'].append(cid)
     if a['values']['initial']==b['values']['initial']:out['identical_initial_worlds'].append(cid)
  out={'initial_joint_agreement':pairs,'models':{}}
  for arm in 'VNU':
   rows=[r for r in allr if r['arm']==arm];paired=[r for r in rows if r['delta_S_minus_I'] is not None];cr=[r for r in controller_rows if r['stage']==stage and r['split']==split and r['arm']==arm]
   changes=Counter()
   for r in paired:
    sign='harm_improved' if r['delta_S_minus_I']['harm']<0 else 'harm_worsened' if r['delta_S_minus_I']['harm']>0 else 'harm_tied'
    changes[sign+'_worlds']+=1;changes[sign+'_changed_controllers']+=len(r['changed_roles'])
   metrics={k:aggregate({r['case_id']:r['delta_S_minus_I'][k] for r in paired},split) for k in ('harm','useful_work','action_harm','omission_harm','interaction_harm','direct_harm','auxiliary')}
   means={phase:{k:aggregate({r['case_id']:r['outcomes'][phase][k] for r in paired},split) for k in ('harm','useful_work')} for phase in ('I','S')}
   for phase in ('I','S'):
    for k,savedk in [('harm','total'),('useful_work','useful_work')]:
     saved=analysis['human'][split]['1']['metrics'][savedk]['available_cell_means'][arm+phase]
     assert math.isclose(means[phase][k]['available_mean'],saved['available_family_mean'],abs_tol=1e-10)
   out['models'][arm]={'planned_worlds':len(rows),'paired_worlds':len(paired),'missing_worlds':[r['case_id'] for r in rows if r not in paired],'planned_controller_pairs':3*len(rows),'observed_controller_pairs':3*len(paired),'changed_private_vs_shared':sum(x['private_vs_shared_changed'] is True for x in cr),'initial_to_private_changes':sum(x['initial_to_private_changed'] is True for x in cr),'initial_to_shared_changes':sum(x['initial_to_shared_changed'] is True for x in cr),'joint_action_changed_worlds':sum(bool(r['changed_roles']) for r in paired),'joint_outcome_categories':dict(changes),'means':means,'deltas':metrics}
  summary[stage][split]=out
protected=summary['R1']['human_protected'];assert len(protected['initial_joint_agreement']['VN']['identical_initial_worlds'])==8
assert [protected['models'][a]['changed_private_vs_shared'] for a in 'VNU']==[10,13,6]
report={'status':'PASS','design':'Descriptive post-hoc analysis of existing saved R1/R2 outputs; no new model calls or change to primary estimands.','sign_convention':'Delta = shared minus private. Negative harm and positive useful work indicate improvement.','weighting':'Welfare means use the frozen equal-family/parent/twin rules. Action-change counts are unweighted controller/world counts, not independent observations.','individual_attribution':'Changed controllers are associated with their joint outcome; unilateral substitutions are hypothetical table calculations and are not additive causal effects.','visibility_pairs_checked':visibility,'source_hashes':evidence,'summary':summary,'cases':case_rows}
report['input_hashes']={p.relative_to(P).as_posix():sha(p) for p in [C/'model_facing/development/human_development.json',C/'model_facing/protected_draft/human_protected.json',C/'private/family_split_registry.json']}
report['private_shared_prompt_difference_verified']='Only other_frozen_proposals differs in every complete matched controller pair; all decoding parameters and own initial proposals match.'
(O/'peer_proposal_analysis.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
with (O/'controller_transitions.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(controller_rows[0]));w.writeheader();w.writerows(controller_rows)
flat=[]
for r in case_rows:
 row={k:r[k] for k in ('stage','split','case_id','family','arm')}
 for phase in ('initial','I','S'):row[phase+'_actions']=' | '.join(x or 'MISSING' for x in r['actions'][phase])
 for phase in ('I','S'):
  for k in ('harm','useful_work','action_harm','omission_harm','auxiliary'):row[phase+'_'+k]=r['outcomes'][phase][k] if r['outcomes'][phase] else None
 row['changed_roles']=' | '.join(r['changed_roles']);flat.append(row)
with (O/'joint_transitions.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
for stage,splits in summary.items():
 for split,s in splits.items():
  print(stage,split,'VN initial equal',len(s['initial_joint_agreement']['VN']['identical_initial_worlds']),'/',len(s['initial_joint_agreement']['VN']['comparable_worlds']))
  for arm,m in s['models'].items():print(arm,'changes',m['changed_private_vs_shared'],'/',m['observed_controller_pairs'],'initial I/S',m['initial_to_private_changes'],m['initial_to_shared_changes'],'delta harm/work',m['deltas']['harm']['available_mean'],m['deltas']['useful_work']['available_mean'],m['joint_outcome_categories'])
print('Visibility checks:',visibility)
for r in case_rows:
 if r['case_id'] in ('HP06','HP08'):print(r['stage'],r['case_id'],r['arm'],r['actions'],r['outcomes'],r['unilateral_table_substitutions'])
