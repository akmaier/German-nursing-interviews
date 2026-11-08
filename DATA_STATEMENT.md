# Data statement, anonymization and residual-risk disclosure

This release includes a screened subset of interview passages, following expert review by
R. Zöllner and the removal of the two highest re-identification-risk interviews. It reflects a
deliberate reversal of the earlier "no passages in any form" posture, approved by the authors.

## What is and is not released
- **Released:** the category system (codebook / mappings); the expert gold labels; all Task A model
  predictions (13 models, fixed category codes); the Task B **judge verdicts** per occurrence
  (4 models); the LLM-judge and human-validation ratings; and a **screened subset of 307 interview
  passages** (`data/passages/passages_shuffled.csv`).
- **Task B is inductive**, so the model-generated and expert fine-category labels are *free text that
  paraphrases the passage*. To avoid leaking withheld-passage content, Task B ships the judge's
  *same/related/different* verdict per occurrence (which is all the reported rates need), **not** the
  label text. The generated labels are shipped only for the 307 released passages
  (`results/taskB/generated_labels_released.csv`), whose text is public anyway. No prediction, label,
  judge or human file carries text from a withheld passage.
- **Not released:** the interview recordings, transcripts and full interview documents; the other 15
  interviews; any direct personal data; and the passage text of the **two highest re-identification-risk
  interviews** (removed in full — see below). Interviews and human raters appear only as pseudonyms;
  the mapping from the shuffled `R####` ids to the original interviews and order is not published.

## How the released passages were screened
1. **Expert screening (R. Zöllner).** The expert coder reviewed the passages and approved a subset for
   release, removing duplicates/withdrawn items and rewording several passages to strip residual
   person-, place- and date-level references. This yielded 651 screened passages.
2. **High-risk interviews removed.** An independent adversarial anonymization review
   (internal, two-model, conservative/adversarial read) rated two interviews **HIGH** re-identification risk,
   because the speaker's institutional role is resolvable by web search even after paraphrase. The
   passage text of both interviews is **removed in full** (344 passages), leaving **307** released
   passages. Their text-stripped predictions and labels are retained so the benchmark remains
   reproducible.
3. **Shuffling.** The released passages are published in randomized order under shuffled `R####` ids;
   the original order and interview membership are not recoverable.

## Residual risk (disclosed)
The released passages are near-verbatim paraphrases, so idiolect may be recognizable to colleagues.
Two retained interviews were rated MEDIUM risk (a rare-biography profile; a profile with a named
vendor link and a regional event); the authors judged these acceptable for release after screening.
A small number of `gold_fine_title` labels may encode topic-specific detail; these ship because they
are required for the Task B scoring and cannot be altered without changing the reported metrics.

## What this enables
All reported **metrics reproduce from the released predictions and verdicts** via `code/reproduce_*.py`
— no passage text and no model access are required. Re-running inference is an optional extension and
requires the original (unreleased) interview text.

## Ethics and consent
The interviews were conducted as part of doctoral research at the Alexandre Lamfalussy Faculty of
Economics, István Széchenyi Economics and Management Doctoral School, University of Sopron, Hungary.
All participants received written study information and gave written informed consent before
participation, including separate consent for audio recording. Participation was voluntary, with the
right to withdraw at any time without reason or disadvantage. The study was conducted in accordance
with the Declaration of Helsinki. Under the regulations of the István Széchenyi Economics and
Management Doctoral School, formal ethics-committee approval was not required for this interview
study. Personal data were stored separately from the analysed data and kept inaccessible to third
parties; contact details were deleted after the study, and only non-identifiable data are retained.

## License
The released data — the category system, the screened passage subset, and all contents of `results/`
(predictions, judge verdicts, human ratings, summaries) — is released under **CC BY 4.0** (see
`LICENSE-DATA`). Interview recordings, transcripts and full interview documents are not included.
