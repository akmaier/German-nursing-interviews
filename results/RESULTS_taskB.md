# Task B — inductive category formation

Four models generated their own fine-category label for each of 685 passages **without** the
codebook, over 5 random seeds. A Claude-Opus LLM-as-a-judge rated each generated label against the
expert's fine-category label as *same*, *related* or *different* (labels only, no passage text).
Because the generated and expert labels are passage-derived free text, the release ships the judge
**verdict per occurrence** (`results/taskB/`), not the label text; the generated labels are provided
only for the released passages (`results/taskB/generated_labels_released.csv`).

Reproduce with `python code/reproduce_taskB.py` (writes `results/reproduced/RESULTS_taskB.md`).
4 models × 5 seeds × 685 passages = 13,700 label-pair occurrences.

## Semantic agreement (mean ± SD over 5 seeds)
Strict = share rated *same*; thematic = *same* or *related*.

| Model | strict %same | thematic %same+related |
|---|---|---|
| RedHatAI/gemma-4-31B-it-FP8-block | 37.3 ± 1.5 | 90.5 ± 0.8 |
| deepseek-ai/DeepSeek-V4-Flash | 35.9 ± 6.3 | 90.4 ± 0.8 |
| nvidia/nemotron-3-ultra-550b-a55b | 35.6 ± 1.4 | 90.9 ± 1.2 |
| Mistral-Large-4.0 | 34.1 ± 4.5 | 89.1 ± 0.7 |

(SD is the sample standard deviation over the 5 seeds, as emitted by `reproduce_taskB.py`.)

All four models rarely match the expert's fine category verbatim (strict ≈ 34–37%) but land in the
right thematic field ≈ 89–91% of the time.

## Significance (passage-clustered paired bootstrap, 3000×)
- strict: gemma − DeepSeek = +1.4 pp (not significant).
- thematic: +0.1 pp (not significant).

## Judge intra-rater reliability (4 passes on a 300-pair subset)
- unanimous (3-way): 84.0%  ·  Fleiss' κ = 0.850
- unanimous (binary *same+related* vs *different*): 94.7%

## Human calibration of the judge
On 100 human-anchored label pairs, inter-human agreement on fine semantic equivalence was weak
(three-way κ = 0.18, binary κ = 0.33); the LLM judge agreed with humans at a comparable level, and
the two LLM judges agreed with each other at κ = 0.73. See `reproduce_human_validation.py`.
