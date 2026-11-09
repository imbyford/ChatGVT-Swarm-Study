"""Original physical metrics/supports plus explicitly labelled R1 diagnostics."""
from collections import defaultdict,Counter
from statistics import mean
import json
from integration.draft import load,scoring,analysis
from integration.report_scripted import add_leave_one_out

def welfare(physical):
 data=load();reg=data['registry'];out={'human':{},'animal':{},'contrast_specific_support':{}}
 for split in ('human_development','human_protected'):
  out['human'][split]={};out['contrast_specific_support'][split]={}
  for weight in (.5,1,2):
   b=analysis.human_analysis(list(data['human'].values()),reg,physical['human_commitments'],split,weight)
   ids=b['planned_worlds'];cells={i:{cell:scoring.human_row(data['human'][i],joint,weight) if joint is not None else None for cell,joint in physical['human_commitments'][i].items()} for i in ids};b['case_cells']=cells;out['human'][split][str(weight)]=b
   contrasts={'R_I':{'NI':1,'VI':-1},'R_S':{'NS':1,'VS':-1},'theta':{'NS':1,'VS':-1,'NI':-1,'VI':1}}
   for arm in 'VN':
    for cond in 'IS':contrasts['U-'+arm+'_'+cond]={'U'+cond:1,arm+cond:-1}
   specific={}
   for metric in b['metrics']:
    specific[metric]={label:analysis.summary({i:sum(co*cells[i][c][metric] for c,co in terms.items()) for i in ids if all(cells[i][c] is not None for c in terms)},[r for r in reg if r['split']==split],b['planned_families']) for label,terms in contrasts.items()}
   out['contrast_specific_support'][split][str(weight)]=specific
 for split in ('animal_development','animal_protected'):
  out['animal'][split]={str(w):analysis.animal_analysis(list(data['animal'].values()),reg,physical['animal_trajectories'],split,w) for w in (0,.5,1,2)}
 add_leave_one_out(out);return out

def report(events,physical):
 from r1.protocol import validation_records
 data=load();out=welfare(physical);intents={e['slot']['request_id']:e for e in events if e['event']=='request_intent'};responses={e['request_id']:e for e in events if e['event']=='response'}
 out.update(study='Study2-R1',interpretation='Post-result exploratory interface follow-up; original strict results unchanged',missingness=[],policy_diagnostics={},uptake={},native_comparison={})
 for sid,e in intents.items():
  r=responses[sid];parsed=r['parsed'];out['missingness'].append({**e['slot'],'started':True,'response_status':r['status'],'substantive_status':parsed.get('status') if isinstance(parsed,dict) else None,'finish_reason':r['reply']['finish_reason'],'input_tokens':r['reply']['input_tokens'],'output_tokens':r['reply']['output_tokens']})
 for e in events:
  if e['event']=='unstarted':out['missingness'].append({**e['slot'],'started':False,'response_status':'unstarted','cause':e['cause']})
 node_data={}
 for sid,e in intents.items():
  s=e['slot']
  if s['task']!='auxiliary':continue
  k=(s['case_id'],s['arm'],s['node']);entry=node_data.setdefault(k,{'case_id':k[0],'arm':k[1],'node':k[2],'factual_answer':None,'classifications':{}})
  r=responses[sid]['parsed']
  if s['kind']=='factual':entry['factual_answer']=r['answer']
  else:entry['classifications'][s['action']]=r
 for k,node in node_data.items():
  cid,arm,name=k;keys=data['keys'][cid];accepted=keys.get('factual_keys',{}).get(name);node['factual_accuracy']=scoring.factual_score(accepted,node['factual_answer']) if node['factual_answer'] not in ('unknown','refuse') else None
  node['policy_agreement']={};parent=next(e for e in intents.values() if e['slot']['task']=='physical' and e['slot']['case_id']==cid and e['slot']['arm']==arm and json.loads(e['request']['messages'][1]['content']).get('current_node')==name)
  decision=responses[parent['slot']['request_id']]['parsed'];node['physical_decision']=decision
  judgment={kind:[aid for aid,flags in node['classifications'].items() if flags[kind]] for kind in ('permitted','required','recommended','unresolved')}
  for target in 'VN':node['policy_agreement'][target]=scoring.fidelity(keys['policy_keys'][target][name],decision['action'],judgment,decision['status'])
 out['animal_auxiliary_nodes']=list(node_data.values())
 for split in ('animal_development','animal_protected'):
  subreg=[r for r in data['registry'] if r['split']==split];families=sorted({r['family_group'] for r in subreg});ids={r['id'] for r in subreg};out['policy_diagnostics'][split]={}
  for arm in 'VNU':
   out['policy_diagnostics'][split][arm]={}
   for target in 'VN':
    comps=defaultdict(lambda:defaultdict(list));nodes=[n for n in node_data.values() if n['case_id'] in ids and n['arm']==arm]
    for n in nodes:
     vals={'factual':n['factual_accuracy'],**{c:n['policy_agreement'][target][c] for c in ('choice_permitted','choice_required','choice_recommended')},**{'classification.'+c:v for c,v in n['policy_agreement'][target]['classification'].items()}}
     for c,v in vals.items():
      if v is not None:comps[c][n['case_id']].append(v)
    out['policy_diagnostics'][split][arm][target]={'own_policy':target==arm,'interpretation':'own-policy fidelity' if target==arm else 'descriptive cross-policy agreement','components':{c:{**scoring.equal_family_mean({cid:mean(vs) for cid,vs in vals.items()},subreg,families),'scoreable_nodes':sum(map(len,vals.values()))} for c,vals in comps.items()},'reached_nodes':len(nodes),'unknown_factual':sum(n['factual_answer']=='unknown' for n in nodes),'refused_factual':sum(n['factual_answer']=='refuse' for n in nodes)}
 rows={r['pair_id']:r for r in validation_records()};diagnostic=[]
 for sid,e in intents.items():
  s=e['slot']
  if s['task'] not in ('uptake','native'):continue
  row=rows[s['row_id']];r=responses[sid];choice=r['parsed'].get('Choice') if s['task']=='uptake' else r['parsed'].get('choice');valid=r['status']=='valid'
  diagnostic.append({**s,'template_id':row['template_id'],'family_group':row['family_group'],'authored_state':row['state'],'group':row['action_relation'],'choice':choice,'valid':valid,'nonconcrete':choice in ('Conditional','Undetermined'),'refuse':choice=='Refuse' or r['status']=='refuse','response_status':r['status'],'rationale_format':r['parsed'].get('rationale_format'),'policy_status_text_present':r['parsed'].get('policy_status_text_present'),'reference_choices':{a:row['targets'][a]['choice'] for a in 'VN'},'agreement':{a:int(choice==row['targets'][a]['choice']) if valid else None for a in 'VN'},'permission_agreement':{a:int(choice in row['targets'][a]['permissible_or_candidate_actions']) if valid and choice in ('A','B') and row['targets'][a]['permission_scope']=='policy-permitted actions' else None for a in 'VN'}})
 out['uptake_rows']=diagnostic
 for task in ('uptake','native'):
  out['uptake'][task]={}
  for group in ('all','different','same','shared_nonconcrete'):
   out['uptake'][task][group]={}
   for arm in 'VNU':
    selected=[r for r in diagnostic if r['task']==task and r['arm']==arm and (group=='all' or r['group']==group)];bytemplate=defaultdict(list)
    for r in selected:bytemplate[r['template_id']].append(r)
    targets={}
    for target in 'VN':
     state_means={tid:{str(state):mean(v) if (v:=[r['agreement'][target] for r in rs if r['authored_state']==state and r['agreement'][target] is not None]) else None for state in sorted({r['authored_state'] for r in rs})} for tid,rs in bytemplate.items()}
     means={tid:mean(v) if (v:=[x for x in states.values() if x is not None]) else None for tid,states in state_means.items()};vals=[v for v in means.values() if v is not None]
     # Equal templates, equal authored states within template, equal variants within state. Full diagnostic mean needs every planned row extractable; conditional summaries retain missingness.
     targets[target]={'template_means':means,'state_means':state_means,'equal_template_mean':mean(vals) if vals and len(vals)==len(means) and all(r['agreement'][target] is not None for r in selected) else None,'available_template_mean':mean(vals) if vals else None,'row_agreement':sum(r['agreement'][target]==1 for r in selected),'scoreable_rows':sum(r['agreement'][target] is not None for r in selected),'planned_rows':len(selected)}
    out['uptake'][task][group][arm]={'targets':targets,'status_counts':{'valid':sum(r['valid'] for r in selected),'nonconcrete':sum(r['nonconcrete'] for r in selected),'refuse':sum(r['refuse'] for r in selected),'invalid_or_truncated':sum(r['response_status'] in ('invalid','truncated') for r in selected),'unextractable_refusal':sum(r['response_status']=='refuse' for r in selected)}}
 lookup={(r['task'],r['row_id'],r['arm']):r for r in diagnostic}
 for arm in 'VNU':
  pairs=[]
  for r in diagnostic:
   if r['task']=='native' and r['arm']==arm:
    other=lookup[('uptake',r['row_id'],arm)];pairs.append({'row_id':r['row_id'],'template_id':r['template_id'],'state':r['authored_state'],'native_choice':r['choice'],'constrained_choice':other['choice'],'both_valid':r['valid'] and other['valid'],'same_choice':r['choice']==other['choice'] if r['valid'] and other['valid'] else None,'native_agreement':r['agreement'],'constrained_agreement':other['agreement'],'native_rationale_format':r['rationale_format']})
  out['native_comparison'][arm]=pairs
 out['counts']={'attempted_requests':len(intents),'reserved_output_tokens':events[-1]['reserved_output_tokens'],'tasks':dict(Counter(e['slot']['task'] for e in intents.values()))}
 add_leave_one_out(out['policy_diagnostics']);return out
