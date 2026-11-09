"""Regenerate the task booklet from the four model-facing case files only."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads((ROOT/p).read_text())
public_cases=[]
for split in ['animal_development','animal_protected','human_development','human_protected']:
 d='development' if split.endswith('development') else 'protected_draft'
 for c in load(f'model_facing/{d}/{split}.json'): public_cases.append((split,c))
lines=['MODEL-FACING CASE BOOK — DRAFT / PROTECTED CONTENT INCLUDED','This is a reviewer booklet, not a prompt. Live task requests must use source/prompts.py.','Protected sections are embargoed and must not be sent to curriculum authors. No scoring keys or hidden state tape are included.','']
for split,c in public_cases:
 lines += ['='*76,f"{c['id']} | {split} | {c['family']}",c['scenario'],'']
 if 'parameters' in c:
  for rule in c['rules']: lines += [rule,'']
  p=c['parameters']; lines += [f"Demand {p['demand']}; omission weight {p['omission_weight']} per unserved person."]
  for r in c['roles']:
   lines += [f"Role {r['id']}: {r['module']}"]+[f"  {a['id']} (value {a['value']}): {a['description']}" for a in r['actions']]
  lines += ['Joint tuple | service | direct | interaction | auxiliary']
  for k,v in p['consequence_table'].items(): lines += [k+' | '+' | '.join(str(v[f]) for f in ['service','direct','interaction','auxiliary'])]
 else:
  lines += [f"Status facts: {c['status_label']}",f"Prior: {json.dumps(c['prior'])}"]+c['scoring_assumptions']
  for n,nd in c['nodes'].items():
   lines += ['',f'Node {n}',nd['observation'],'Common factual probe: '+nd['factual_probe']]
   for a in nd['actions']:
    lines += [f"  Action {a['id']}: {a['description']}"]
    for state,e in a['by_state'].items(): lines += ['    '+state+': '+json.dumps(e,ensure_ascii=False)]
 lines+=['']
(ROOT/'model_facing/CASEBOOK.txt').write_text('\n'.join(lines)+'\n')
print('Regenerated casebook from',len(public_cases),'cases.')
