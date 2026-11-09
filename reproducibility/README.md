# Historical scientific inputs and offline replay

Use the single verified command in the repository-root README. It needs Python 3.12/3.13 standard library only and runs on a disposable copy.

These directories preserve the original evaluation/scoring source, request bodies, raw response text, actions and expected results. Historical freezes retain the original file commitments. The public outer MANIFEST identifies the released files; docs/PUBLIC_SANITISATION.json records metadata pseudonymisation.

The offline wrapper replaces omitted-weight availability checks with hash-bound model labels. It handles the two original-Study-2 ledger-digest fields changed by provider-ID removal, and preserves historical Study 1 snapshot labels through an explicit metadata-only alias lookup. All request bodies, raw responses, actions, outcome vectors and scientific analysis fields are checked exactly. This does not recreate model inference or cryptographically verify the original host.

Weights, tokenizer assets, full training datasets, provider credentials and account/payment/session records are omitted. Historical `private` and `protected` directory labels refer to model-facing visibility and earlier split status. These now-observed cases, validation targets and scoring keys are intended for public reproduction after author approval, not future blinded testing.

Candidate authoring/audit documents are retained as historical provenance bound into the evaluation manifests. Their embedded instructions and old local command examples are not the public reproduction interface or new authorization. Only the root README command is advertised and tested for this distribution.
