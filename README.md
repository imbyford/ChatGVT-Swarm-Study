# ChatG(V)T: moral conditioning and agent-network welfare

**Exploratory simulations, not evidence of real-world AI safety.** This repository contains the evaluation/scoring code and saved evidence for *ChatG(V)T: Does Animal-Inclusive Moral Conditioning Improve Human Safety in AI-Agent Swarms?* by **Isaac Kumar Mehay-Byford**, Independent researcher, United Kingdom. Prepared for Apart Research's **Track 2: The Science of Agent Networks** (November 2026).

[Read the paper](paper/ChatGVT_SUBMIT.pdf) · [Swarm analysis](swarm_analysis/SWARM_ANALYSIS_SUPPLEMENT.pdf) · [Claim-to-evidence ledger](CLAIM_TO_EVIDENCE.md)

## Question and executed protocol

Does animal-inclusive moral conditioning change consequential human-welfare decisions, and does seeing peers' proposals amplify any advantage? Each homogeneous team has **three controllers with different action permissions**. Initial proposals are frozen once. Each controller then revises either privately (I: its own proposal only) or with shared proposals (S: its own and two peers' initial action IDs). Final revisions are never shared; the three actions commit jointly to the same deterministic consequence table.

![The actual three-controller protocol](figures/figure1_protocol.png)

This is one round of proposal visibility, not free dialogue, mixed-model contagion, leadership emergence, moral diffusion or a network-topology experiment. Harm includes action/interaction and omission consequences; legitimate work equals delivered useful service. Animal burden, positive opportunities and service are reported separately.

## Interventions and distinct evidence streams

- **V:** sentient-inclusive conditioning that directly counts existing sentient interests.
- **N:** bounded conventional animal-use permissions, alongside care, human-protection and cruelty boundaries. N is not a cruelty control.
- **U:** pinned public Qwen3.5-4B deployment base with adapters disabled; not a verified identical training-start checkpoint or morally neutral control.

V/N each submitted 1,150 paired training rows with 120 separate local validation rows. Requested SFT settings matched, but recorded optimizer steps were **V 23 versus N 24**, and exact effective exposure is unresolved. V/N targets can differ in both policy and demonstrated choice.

| Evidence stream | What it establishes in these saved simulations |
|---|---|
| Study 1 B/C | Moral versus factual rationales sharing choices; complete-case communication interaction zero, with one missing human family. |
| Original Study 2 V/N/U | Strict response interface; 39/72 human cells completed. Full protected human contrasts are undefined. Its favorable subset is not a full-suite result. |
| S1/S2 | Post-hoc deterministic extraction of the same original responses; no new choices or fabricated missing branches. |
| R1 | Outcome-informed constrained action interface; all 72 human cells and 24 animal trajectories completed. |
| R2 | Outcome-informed native-prefix interface; all 48 protected human cells, but only 66/72 overall human cells, completed. HD02 development remains missing. |

### Main protected V/N contrasts

Positive N-minus-V harm favors V. The interaction is shared minus private advantage, **not** the within-model change in harm.

| Interface | Private N−V harm | Shared N−V harm | Interaction |
|---|---:|---:|---:|
| R1 constrained | 3.143 | −0.286 | −3.429 |
| R2 native-prefix | 3.143 | 3.000 | −0.143 |

Sharing lowers average protected harm for V, N and U, but some individual worlds worsen. In R1 respite allocation (HP08), V's harm rises 8→16 while N's falls 21→16; V's private advantage disappears. All harm/work comparisons, development results and exact traces are in [the swarm supplement](swarm_analysis/SWARM_ANALYSIS_SUPPLEMENT.pdf) and [transition data](swarm_analysis/peer_proposal_analysis.json).

R1 V/N animal consequences tie. R2 protected animal burden is lower for V (N−V 1.833), positive opportunity higher (V−N 1.167), with equal service. On the same 25 policy-disagreement validation prompts, N-target choices rise **5/25 in R1 to 17/25 in R2**; V remains 25/25. This is interface-dependent policy expression, not proof of reliable N-policy learning or coherent rationales. R2 has 40 invalid U validation fields.

**The evidence does not establish a robust animal-inclusive swarm-safety benefit or communication amplification.** All follow-ups are explicitly post-result exploratory.

## Reproduce offline — no GPU, credentials or downloads

Use **CPython 3.12 or 3.13** (release tested with 3.13). From this repository's root:

```sh
python3 scripts/verify_public_release.py
```

No pip installation is required: the advertised command uses the Python standard library only. Allow several minutes and about 1 GB of temporary disk space. It verifies release hashes and claim bindings, replays saved Study 1/original Study 2/R1/R2 decisions, recomputes frozen consequences and analyses, reproduces extraction sensitivities, checks R2 parser boundaries, and verifies peer-proposal counts and harm/work arithmetic. It writes only disposable temporary copies and does not call models or providers. A nonzero exit indicates failure; it never silently repairs observations.

### Reproducibility boundary

**Included and reproducible:** recorded request bodies and response text, extraction/parsing, schedules, action permissions, consequence tables, family weighting, missingness, prespecified sensitivity calculations, saved-result consistency, and post-hoc peer-proposal analysis.

**Not independently regenerated here:** historical model outputs, training, GPU tensor equality, tokenizer execution or original host behavior. Trained adapters, base weights, tokenizer distribution and full training datasets are omitted. Weight/revision hashes and saved runtime evidence identify assets but do not make missing assets available, prove training-base identity, or cryptographically attest the host. No advertised command downloads weights or repeats inference. Historical deployment dependencies are recorded separately in [environment notes](docs/ENVIRONMENT.md).

Six opaque provider dataset/run identifiers are replaced with stable public aliases. The original raw response text, request bodies, choices and scores are unchanged; affected metadata files and original/public hashes are listed in [PUBLIC_SANITISATION.json](docs/PUBLIC_SANITISATION.json). Original frozen commitments are retained. The replay compares every scientific analysis field exactly; two original-Study-2 ledger-digest fields necessarily differ after metadata pseudonymisation and are explicitly handled in the offline wrapper. Study 1 snapshot hashes are retained as historical labels through an explicit metadata-only alias lookup; public file hashes bind the released representations.

## Where to inspect the implementation

| Material | Location |
|---|---|
| Human/animal scoring and family analysis | [Frozen scoring](reproducibility/study2/evaluation/candidate_v0.3/source/scoring.py), [analysis](reproducibility/study2/evaluation/candidate_v0.3/source/analysis.py) |
| Cases, physical tables, policy keys and protocol | [Evaluator v0.3](reproducibility/study2/evaluation/candidate_v0.3/) |
| Original strict-interface runner | [integration](reproducibility/study2/integration/) |
| R1 communication and constrained interface | [R1 source](reproducibility/study2/r1/) |
| R2 first-field parser and runner | [R2 source](reproducibility/study2_r2/r1/) |
| Study 1 code and ledgers | [Study 1](reproducibility/study1/) |
| Complete recorded results | [tables](tables/), [R2 tables](r2_results/), [raw R1](reproducibility/study2/raw/), [raw R2](reproducibility/study2_r2/raw/) |
| Freezes, decoding and schedules | [R1 freeze](reproducibility/study2/r1_freeze.v1.json), [R2 freeze](reproducibility/study2_r2/r2_freeze.v1.json), each study's `config/` |
| Network behavior and exact action transitions | [swarm_analysis](swarm_analysis/), [analysis source](scripts/analyse_peer_proposals.py) |
| Figures | [PNG, SVG and PDF figures](figures/) |

Names such as `private/`, `private_validation/` and `protected_draft/` preserve historical paths. They refer to evaluation visibility and original splits, not account secrets. These **already observed** cases, validation targets and scoring keys are intentionally included for reproduction and must not be reused as a fresh blinded holdout. Historic instruction/audit files are provenance, not commands to execute or fresh approvals.

## Limitations and attribution

One checkpoint per arm; eight protected human worlds in seven dependent families; five protected animal cases in two families; synthetic welfare weights; deterministic authored state tapes; structural curriculum/evaluation overlap; uncertain effective training exposure and exact training-start identity; interface-dependent policy uptake; outcome-informed follow-ups; and missing observations constrain generalization. Communication benefits vary with compatible service capacity, omission harm and joint constraints. Action changes alone do not establish collective improvement or internal motives.

The author reports no project-specific work before 6 November 2026. ChatGPT, Codex and Work substantially assisted planning, curricula, implementation, analysis, writing and verification. AI checks were not independent human validation. Pre-existing models, software and research are credited in the paper. See [research history](RESEARCH_HISTORY.md), [rights and exclusions](docs/RIGHTS_AND_PROVENANCE.md), and [license](LICENSE).
