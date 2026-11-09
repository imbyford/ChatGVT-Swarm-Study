"""Verify documentation v1, then run the unchanged historical offline verifier.

Packaging only: no scientific scorer, saved result or original manifest is changed.
Uses only the Python standard library. No network or model access is required.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
UPDATE = ROOT / 'docs/updates/2026-11-09'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs():
    update = json.loads((UPDATE / 'manifest.v1.json').read_text())
    assert update['historical_commit'] == '67b3000756a15b011833810b865a21e1e455fc9e'
    assert sha(ROOT / 'PUBLIC_MANIFEST.json') == update['historical_manifest_sha256']
    for rel, expected in update['documentation_files'].items():
        assert sha(ROOT / rel) == expected, ('documentation hash mismatch', rel)
    frozen = json.loads((ROOT / 'PUBLIC_MANIFEST.json').read_text())
    historical_readme = UPDATE / 'README.historical.txt'
    assert sha(historical_readme) == frozen['files']['README.md']
    for rel, expected in frozen['files'].items():
        path = historical_readme if rel == 'README.md' else ROOT / rel
        assert sha(path) == expected, ('historical file changed', rel)


def main():
    verify_inputs()
    print('PASS: documentation hashes and every historical file commitment.', flush=True)
    with tempfile.TemporaryDirectory(prefix='chatgvt-docs-v1-') as td:
        work = Path(td) / 'release'
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns('.git', '__pycache__'))
        # The original verifier binds the original README, not today's presentation.
        # Restore exactly that file in this disposable copy, never in the checkout.
        shutil.copyfile(UPDATE / 'README.historical.txt', work / 'README.md')
        result = subprocess.run(
            [sys.executable, str(work / 'scripts/verify_public_release.py')],
            cwd=work,
        )
        if result.returncode:
            raise SystemExit(result.returncode)
    verify_inputs()
    print('PASS: documentation v1 and unchanged historical offline reproduction; checkout preserved.')


if __name__ == '__main__':
    main()
