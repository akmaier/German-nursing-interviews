# German Nursing Interviews — an LLM benchmark for Mayring qualitative content analysis

Code and anonymized data for the study *"Large language models reproduce the structure of expert
qualitative content analysis in German nursing interviews"* (R. Zöllner, S. Mages, A. Maier).

It contains the benchmark **code**, the **anonymized category system and gold labels**, the **model
predictions and LLM-judge verdicts**, the **human-validation ratings**, and scripts that
**reproduce every results table from the released data** — no model access required. A **screened
subset of 307 interview passages** is included; the two highest-risk interviews are withheld in full
(see *Data & participant protection* below).

## What the benchmark measures
Two tasks against one expert's Mayring coding (8 dimensions, 27 main categories, 113 subcategories)
of German nursing interviews on nurse retention, return to practice and recruitment:
- **Task A — deductive.** Assign each of 685 passages to one of 27 main categories (closed set).
  13 open-weight models × 5 random seeds, temperature 0.7.
- **Task B — inductive.** Four models generate their own fine-category labels without the codebook;
  an LLM-as-a-judge rates each generated label against the expert label as *same / related /
  different*; two human experts and a second judge calibrate the judge.

## Repository layout
```
data/        codebook.json (27 categories + definitions), category_system/ (full hierarchy)
             passages/  307 screened passages, shuffled R#### ids (interviews 16 & 19 withheld)
results/     taskA/   13 models × 5 seeds predictions (category codes only, no passage text)
             taskB/   4 models × 5 seeds judge verdicts (+ generated labels for released passages)
             judge/   judge verdicts + verification key (verdict-only, no label text)
             human_ratings/  anonymized rater1/rater2 (+ opus/fable) rating CSVs
             leaderboard_taskA.csv, RESULTS_taskA.md, RESULTS_taskB.md
code/        reproduce_taskA.py, reproduce_taskB.py, reproduce_human_validation.py, client.py
             inference/   reference runners used to generate the data (need model access)
config/      llm_api.example.toml   (OpenAI-compatible endpoint template)
docs/        local_serving.md       (serve open weights via vLLM/SGLang or NVIDIA NIM)
DATA_STATEMENT.md  DATA_DICTIONARY.md  CITATION.cff  LICENSE (code)  LICENSE-DATA
```

## Reproduce the results — no model access needed
The reproduction scripts use only the Python 3.11+ standard library:
```bash
python code/reproduce_taskA.py             # Table 2: 13-model leaderboard
python code/reproduce_taskB.py             # Table 3: semantic-match rates + judge reliability
python code/reproduce_human_validation.py  # Table 4: human/judge agreement + K3 acceptance
```
They recompute the paper's numbers directly from the stored predictions and verdicts.

## Re-run inference (optional; needs model access)
The evaluated models are open-weight. Serve them yourself with **vLLM** or **SGLang**, or via
**NVIDIA NIM**, then copy `config/llm_api.example.toml` to `config/llm_api.toml` and point it at
your OpenAI-compatible endpoint (see `docs/local_serving.md`). The runners in `code/inference/`
re-run Task A/B.

> **Note.** Re-running inference requires the full original interview passages, which are **not
> released** (only the screened 307-passage subset is). The reported metrics reproduce from the
> stored predictions via the `reproduce_*.py` scripts above — no passage text or model access needed.

## Data & participant protection
A **screened subset of 307 passages** is released (`data/passages/`), in randomized order under
shuffled ids, after expert screening and the removal — in full — of the two interviews rated highest
re-identification risk. Recordings, transcripts, full interview documents, the other 15 interviews,
and the withheld interviews' passage text are **not** released. Derived artifacts (category system,
gold labels, model predictions, judge/human verdicts) cover all 685 benchmark passages but contain
**no passage text**. Interviews and raters appear only as pseudonyms. See **`DATA_STATEMENT.md`**
for the full screening rationale, residual-risk disclosure, ethics and consent.

## Licensing & citation
Code: see `LICENSE`. Data: **CC BY 4.0** (`LICENSE-DATA`). Please cite the paper — see `CITATION.cff`.
