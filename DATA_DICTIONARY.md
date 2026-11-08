# Data dictionary

All CSVs are UTF-8, `;`-delimited. Category ids use the `RQ1-Mxx` scheme (27 main categories).

## Passage identifiers
Every passage carries a shuffled identifier `R####` (R0001…R0685). The order is randomized and the
mapping to the original interviews, the original passage order, and the original ids is **not
published**, so neither interview membership nor sequence can be reconstructed from the release.
The same `R####` id joins the passages file to all prediction, label, judge and human files.

## data/
**passages/passages_shuffled.csv** — the released passage subset: `passage_id ; n_words ; text`.
It contains **307** screened, expert-approved passages in shuffled order. Passages from the two
highest re-identification-risk interviews are **not included** (see DATA_STATEMENT.md), and 34
duplicate/withdrawn passages were removed during screening. The expert gold labels for **all** 685
benchmark passages remain available in the results files (keyed by `passage_id`); text ships only
for these 307.

**codebook.json** — the 27 main categories with definitions and anchor examples (judge/prompt material).
**category_system/** — `Codebook.csv`, `Reduction-Mapping.csv`, `Summary-Codebook.csv` (the category hierarchy).

## results/taskA/  (deductive predictions, labels only — no passage text)
`taskA_<model>_seed<k>.csv`, 13 models × 5 seeds, 685 passages each:
| column | meaning |
|---|---|
| passage_id | passage (`R####`) |
| gold_main / pred_main | expert vs. model main category |
| gold_dim / pred_dim | expert vs. model dimension |
| main_ok / dim_ok | 1 if the model matched exactly |

## results/taskB/  (inductive — JUDGE VERDICTS, not label text)
Task B labels are model/expert **free text** that paraphrase the passage, so the generated and
expert label text is **not** shipped for withheld passages. Instead each occurrence ships its judge
verdict, which is all the reported rates need.
`taskB_<model>_seed<k>.csv`, **4 models** × 5 seeds, 685 passages each:
`passage_id ; gold_fine_id ; gold_main ; verdict` with `verdict ∈ {same, related, different}`
(the Opus judge's rating of that model's generated label vs the expert label). The four models are
RedHatAI/gemma-4-31B-it-FP8-block, deepseek-ai/DeepSeek-V4-Flash,
nvidia/nemotron-3-ultra-550b-a55b and Mistral-Large-4.0.
**generated_labels_released.csv** — `passage_id ; model ; seed ; gold_fine_title ; model_label` for
the **307 released passages only** (their text is public), so the inductive labels can be inspected
without exposing any withheld passage.

## results/judge/  (verdict-only; no label text)
- **taskB_judge_verdicts.json** — `{result:{main_verdicts:[{id, verdict}], rel_passes:[[{id, verdict}]×4]}}`; the four judge passes on the 300-pair subset drive the intra-rater reliability.
- **fable_humanpairs_verdicts.json** — the second judge's verdicts on the 100 human-anchored pairs.
- **verification_key.csv** — `sheet ; nr ; passage_id_or_pairid ; judge_verdict` (free-text label columns removed).

`code/reproduce_taskB.py` computes the full 4-model table, the gemma-vs-DeepSeek significance test
and the judge reliability directly from the verdict files above — no label text required.

## results/human_ratings/  (anonymized; verdicts only)
- **sheetA_k3_validation.csv** — `nr ; passage_id ; gold_main ; k3_main ; rater1_verdict ; rater2_verdict` (verdict ∈ {ja, vertretbar, nein}).
- **sheetB_judge_pairs.csv** — `nr ; pair_id ; rater1_verdict ; rater2_verdict ; opus_verdict ; fable_verdict` (verdict ∈ {same, related, different}; the `model_label`/`rita_label` free-text columns are removed).

## results/ summaries
`leaderboard_taskA.csv`, `RESULTS_taskA.md`, `RESULTS_taskB.md` — the computed tables;
`reproduced_RESULTS_taskB.md` is written by `code/reproduce_taskB.py`.
