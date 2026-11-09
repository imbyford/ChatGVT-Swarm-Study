"""Read-only binding of the exact candidate and additive, limited AI check."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def verify_candidate(root=ROOT):
    binding=json.loads((root/'config/evaluation_binding.v0.3.json').read_text())
    for rel,expected in binding['bound_files'].items():
        p=root/rel
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()) or sha(p)!=expected:
            raise ValueError('Candidate binding mismatch: '+rel)
    candidate=root/binding['candidate_path']
    manifest=json.loads((candidate/'private/CANDIDATE_INTEGRITY_MANIFEST_v0.3.json').read_text())
    for rel,record in manifest['files'].items():
        p=candidate/rel
        if p.is_symlink() or not p.resolve().is_relative_to(candidate.resolve()) or sha(p)!=record['sha256'] or p.stat().st_size!=record['bytes']:
            raise ValueError('Candidate payload mismatch: '+rel)
    contract=json.loads((candidate/'protocol/reporting_contract.v0.3.json').read_text())
    for field in ('base_analysis_contract','audit_binding','registry_binding','disposition_binding'):
        item=contract[field]
        if sha(candidate/item['path'])!=item['sha256']:raise ValueError('Contract binding mismatch: '+field)
    closure=json.loads((root/binding['closure_path']).read_text())
    if closure['candidate_bindings']!=json.loads((root/binding['digest_path']).read_text()):
        raise ValueError('Guide closure targets another candidate')
    return {k:binding[k] for k in ('version','candidate_manifest_sha256','reporting_contract_sha256','guide_closure_sha256','review_scope','human_validation','blinded_review','live_execution_authorized')}

def reporting_contract():
    verify_candidate()
    return json.loads((ROOT/'evaluation/candidate_v0.3/protocol/reporting_contract.v0.3.json').read_text())
