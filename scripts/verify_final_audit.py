"""Post-collection read-only boundary checks. Does not alter frozen parsing."""
from pathlib import Path
import hashlib, importlib.util, json, re
R = Path(__file__).resolve().parents[1]
p = R / 'reproducibility/study2_r2/r1/prefix.py'
spec = importlib.util.spec_from_file_location('frozen_r2_prefix', p)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
checks = []
def check(raw, finish, status, choice=None, stop=None):
    got = m.parse(raw, finish, ['A', 'B', 'Unresolved', 'Refuse'])
    assert (got['response_status'], got['Choice']) == (status, choice), (raw, got)
    if stop is not None: assert m.should_stop(raw) == stop
    checks.append({'raw': raw, 'finish': finish, 'expected_status': status, 'expected_choice': choice, 'passed': True})
for raw in ['Choice:\nA\n', 'Choice: \nA', '\nChoice:\r\nA\r\n', 'Choice:\nChoice: A\n', 'Preamble\nChoice: A\n', 'Choice: A or B\n', 'Choice: A Choice: B\n', 'Choice: A; B\n', 'Choice: AA\n', 'Choice: A Reason: yes\n']:
    check(raw, 'stop', 'invalid')
for raw in ['Choice:', 'Choice: ', 'Choice: "A', '', '\n\n']:
    check(raw, 'stop', 'invalid', stop=False)
    check(raw, 'length', 'truncated', stop=False)
for raw in ['Choice: A\n', '\n \nChoice: A\n', 'Choice: A\r\n', 'choice: `A`.\n', 'Choice: A\nChoice: B\n']:
    check(raw, 'stop', 'valid', 'A', True)
    check(raw, 'length', 'valid', 'A', True)
check('Choice: A', 'stop', 'valid', 'A', False)  # Complete exact field at EOS.
check('Choice: A', 'length', 'truncated', stop=False)
check('Choice:\nA', 'length', 'invalid', stop=True)
check('Choice: B\nChoice: A\n', 'stop', 'valid', 'B', True)
ledger = R / 'reproducibility/study2/raw/ledger.jsonl'
rows = [json.loads(x) for x in ledger.read_text().splitlines()]
u = [x for x in rows if x['event'] == 'response' and x.get('request_id', '').startswith('native/') and x['request_id'].endswith('/U') and x['status'] == 'valid']
incomplete = []
for x in u:
    raw = x['reply']['raw']
    trade = re.search(r'^Trade-off:([^\r\n]*)', raw, re.M)
    if trade is None or not trade.group(1).strip():
        incomplete.append({'request_id': x['request_id'], 'raw': raw, 'historical_parsed': x['parsed'], 'response_sha256': x['response_sha256']})
assert len(u) == 17 and len(incomplete) == 3, (len(u), len(incomplete))
saved = json.loads((R / 'evidence/first_field_audit.json').read_text())
responses = {x['request_id']: x for x in rows if x['event'] == 'response'}
for x in saved['records']:
    if x['first_field_choice'] is not None:
        line = next(y for y in responses[x['request_id']]['reply']['raw'].splitlines() if y.strip())
        exact = re.fullmatch(r'\s*(?:\*\*)?(?:Choice|Action)(?:\*\*)?\s*:\s*([^\r\n]+?)\s*', line, re.I)
        assert exact, x['request_id']
        value = exact.group(1).strip()
        if value.endswith('.'): value = value[:-1]
        if len(value)>1 and value[0]==value[-1] and value[0] in ('"', "'", '`'): value=value[1:-1]
        assert value == x['first_field_choice'], x['request_id']
freeze = json.loads((R / 'evidence/r2_freeze.v1.json').read_text())
assert hashlib.sha256(p.read_bytes()).hexdigest() == freeze['files']['r1/prefix.py']['sha256']
out = {'scope': 'Post-collection offline focused audit; no frozen code, scores or observations changed', 'parser_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'boundary_tests_passed': len(checks), 'boundary_tests': checks, 'multiline_action_rejected': True, 'later_line_conflict_rule': 'First exact field remains irrevocable; later fields are retained but not used. Competing values on the first line are invalid.', 'historical_U_extractor_valid': len(u), 'historical_U_without_complete_Trade_off_field': incomplete, 'historical_scoring_and_model_binding': 'Reviewer reports no historical mismatch; original results retained, not reinterpreted as implementation failure.'}
out.update(parser_matches_precollection_freeze=True, saved_GUIDE_readable_fields_confirmed_on_actual_first_nonblank_line=62, saved_GUIDE_rows_inspected=72)
(R / 'evidence/final_focused_audit_checks.json').write_text(json.dumps(out, indent=2) + '\n')
print('PASS:', len(checks), 'frozen R2 boundary checks; 3/17 extractor-valid U native responses lack a complete Trade-off field.')
