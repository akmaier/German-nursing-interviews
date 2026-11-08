# Task A — deductive category assignment

Each model assigned every one of 685 passages to one of 27 main categories (closed set), over
5 random seeds at temperature 0.7. Scored by exact match of the assigned main category (and
dimension) against the expert coding. Majority-class baseline main-category accuracy ≈ 0.127.

Reproduce with `python code/reproduce_taskA.py` (writes `leaderboard_taskA.csv`).

## Leaderboard (13 models, mean ± SD over 5 seeds)

| # | Model | main acc | dim acc | macro-F1 | Cohen's κ |
|---|---|---|---|---|---|
| 1 | Mistral-Large-4.0 | 0.720 ± 0.018 | 0.832 | 0.679 | 0.704 |
| 2 | Kimi-K3 | 0.629 ± 0.008 | 0.752 | 0.606 | 0.610 |
| 3 | nvidia/nemotron-3-ultra-550b-a55b | 0.595 ± 0.008 | 0.720 | 0.563 | 0.574 |
| 4 | deepseek-ai/DeepSeek-V4-Flash | 0.591 ± 0.006 | 0.723 | 0.557 | 0.570 |
| 5 | GLM-5.2-W4A16 | 0.587 ± 0.003 | 0.716 | 0.565 | 0.567 |
| 6 | GLM-5.2-FP8 | 0.586 ± 0.005 | 0.719 | 0.567 | 0.566 |
| 7 | RedHatAI/gemma-4-31B-it-FP8-block | 0.573 ± 0.002 | 0.698 | 0.552 | 0.553 |
| 8 | Qwen3.6-35B-A3B-FP8 | 0.564 ± 0.010 | 0.688 | 0.547 | 0.543 |
| 9 | RedHatAI/Mistral-Small-3.2-24B-Instruct-2506-FP8 | 0.546 ± 0.015 | 0.686 | 0.540 | 0.525 |
| 10 | GaleneAI/Magistral-Small-2509-FP8-Dynamic | 0.540 ± 0.015 | 0.669 | 0.535 | 0.519 |
| 11 | gpt-oss-120b | 0.514 ± 0.009 | 0.655 | 0.492 | 0.491 |
| 12 | google/gemma-4-E4B-it | 0.512 ± 0.007 | 0.645 | 0.499 | 0.490 |
| 13 | Microsoft/Phi-4-mini-instruct | 0.347 ± 0.013 | 0.528 | 0.349 | 0.317 |

`FP8` = 8-bit floating-point quantization; `W4A16` = 4-bit weights, 16-bit activations.

## Significance (passage-clustered paired bootstrap, 3000×)
- Kimi-K3 − DeepSeek-V4-Flash: +3.8 pp main-category accuracy, 95% CI [+1.7, +5.9], p < 0.001.
- GLM-5.2-FP8 − GLM-5.2-W4A16: −0.1 pp, 95% CI [−1.1, +1.0], p ≈ 0.9 (quantization effect not significant).

## Human validation
Kimi-K3 (the strongest self-hosted model) was carried to blinded human validation: two experts
accepted 91.3% and 99.1% of its main-category assignments after population reweighting, versus
62.9% exact agreement — i.e. most exact "errors" were defensible alternative codings.
See `reproduce_human_validation.py`.
