# Post-hackathon presentation update — documentation v1

This update changes the repository's presentation and adds the author's supplied working paper. It introduces no experimental evidence, revised scientific commitment or changed historical result.

## Proposed repository About description

Research on animal-inclusive moral conditioning and human safety under changing AI capability and power, with exploratory three-controller simulations and reproducible pilot evidence.

This is proposed text only; preparing this file does not change GitHub's About field.

## Paper and history

- [Current working paper](../../../paper/ChatGVT_Working_Paper_2026-11-09.pdf): *ChatG(V)T: Does Animal-Inclusive Moral Conditioning Improve Human Safety in AI Systems?* The file is a byte-identical copy of the supplied PDF, SHA-256 `9dcab4a29a390e81846877e042a1009112ee0307cd347aedee2b1e8af79c4b06`.
- [Original submission](../../../paper/ChatGVT_SUBMIT.pdf): retained unchanged, SHA-256 `92ee61701fa6d554908ec9026d69c43f2ec40e2ab8704f3ad28c9668e5f04a7a`.
- Historical release: commit `67b3000756a15b011833810b865a21e1e455fc9e`. Its [original README](README.historical.txt), scientific materials, citation metadata and public manifest are preserved. Historical instructions and approvals describe that earlier release, not new authorisation.

The working paper develops the argument and future programme after the hackathon. Original Study 2, R1, R2 and saved-response extraction sensitivities remain distinct. The updated README gives the adverse R1 and favourable R2 comparisons together, keeps useful work beside harm, and reports interface-dependent N acquisition.

## Why the offline entry point is versioned

`PUBLIC_MANIFEST.json` binds the original README as well as the scientific files. Updating that historical manifest would obscure its meaning. The new [documentation manifest](manifest.v1.json) instead binds this update and identifies the unchanged original manifest.

From the repository root, run:

```sh
python3 scripts/verify_documentation_update_v1.py
```

The standard-library wrapper checks every original commitment, resolving only the historical README to its exact saved copy. It also checks the current README, supplied paper and added documentation files. In a disposable temporary copy it restores that exact historical README and executes `scripts/verify_public_release.py` unchanged. Any failed check or replay returns a failure; no observation is repaired or omitted. It then checks the checkout again.

The original command `python3 scripts/verify_public_release.py` still applies directly to commit `67b3000`. Running it directly against the newly presented checkout will intentionally reject the changed README. Use the versioned wrapper above for this checkout; it does not weaken or edit the original verifier.

No scoring or analysis code changes. No changes to saved responses, cases, weights, model identities, scientific manifests, the historical paper or the original claim ledger. Replay verifies saved evidence, not model training, independent output regeneration or the truth of the research hypothesis.

The renamed historical README remains in this directory for hash preservation. Its original relative links were authored for the repository root; consult the original commit for that historical navigation. Current navigation is in the [root README](../../../README.md).
