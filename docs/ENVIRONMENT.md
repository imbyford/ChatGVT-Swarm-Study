# Environment and scope

The supported public replay uses CPython 3.12/3.13 and the standard library only. The release was tested on CPython 3.13. No GPU, API key, provider connection, model downloads, payment or package installation is needed. Run the single command in the root README. Tests execute on a temporary repository copy so checked evidence is not overwritten.

Historical inference used an NVIDIA A40, a BF16 pinned Qwen/Qwen3.5-4B base (revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`) and FP32 LoRA adapters, Transformers/PEFT reference serving, deterministic algorithms and disabled TF32. Recorded R1/R2 runtime versions include torch 2.14.0, transformers 5.20.2 and peft 0.21.2. Full recorded package inventories are in each `reproducibility/study2*/raw/runtime_packages.txt`.

Those are historical environment records, not a tested installation recipe or assertion of current package availability. Installing them will not supply the omitted adapters or establish training-start identity. Online inference and retraining are outside this release's advertised reproduction scope.

Figures and the manuscript are included as finished artifacts. Their original build toolchain is not required for scientific replay; pixel-identical figure or PDF regeneration is not advertised.
