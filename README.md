# German Nursing Interviews — an LLM benchmark for Mayring qualitative content analysis

> ## 🔬 Live demonstrator → **https://akmaier.github.io/German-nursing-interviews/**
> Paste German nursing-interview text and get its Mayring main category (one of 27),
> powered by NVIDIA Nemotron. Built on the released category system — no interview data involved.

Code and anonymized data for the study *"An open workflow for Mayring qualitative content analysis
of nursing interviews with large language models and artificial intelligence agents"* (R. Zöllner, S. Mages, A. Maier).

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

## Build your own Mayring category system (fork + agentic pipeline)

This repo is not only a benchmark — it is a **reusable template** for building and validating a
Mayring category system for **your own** interview corpus, with large language models doing the
drafting and coding and an agent orchestrating the steps. The method follows Mayring's qualitative
content analysis: **inductive** category formation (let the data suggest the categories) followed
by **deductive** application (apply the resulting codebook), calibrated against human raters.

Fork two repositories and let an agent drive them:
- **`akmaier/german-nursing-interviews` (this repo)** — the pipeline scripts, the category-system
  schema (`data/codebook.json`), the calibration/reproduction code, and a complete worked example to imitate.
- **[`akmaier/agent-m`](https://github.com/akmaier/agent-m)** — the agentic orchestrator (companion to the
  *Vibe Coding* textbook) that carries the project from your raw interviews (the requirement source) to a
  released category system + demonstrator, committing each artifact to your fork.

> **Human oversight is required.** The models produce a strong first-pass category system and scale the
> coding; a domain expert must validate the categories and judge the acceptability of disagreements.
> Treat the models as first-pass coders, not autonomous analysts.

### Preliminaries — from interviews to text (transcription)
Before step 0 you need your interviews as **text**. Two routes, from quickest to highest quality:

- **Voice typing on a phone** (fastest — good for notes or short interviews).
  - *iPhone:* tap the microphone on the keyboard in Notes (or any text field) and speak; or record in
    **Voice Memos** and use its built-in transcript (iOS 18+).
  - *Android:* use **Gboard** voice typing (the mic key), or the **Recorder** app (Pixel) / **Live
    Transcribe**, which transcribe live as you speak.
  - Speak clearly; afterwards split the text into coding units (one statement/idea per line).

- **Whisper ASR** (recommended for recorded interviews — runs **locally**, so recordings never leave your machine).
  ```bash
  pip install -U openai-whisper          # also needs ffmpeg:  brew install ffmpeg  /  apt install ffmpeg
  whisper interview01.m4a --model large-v3 --language de --output_format txt
  ```
  Use `--model large-v3` for German quality and `--output_format srt` if you want timestamps. For speed use
  **faster-whisper** or **whisper.cpp**; for speaker turns ("who said what") add diarization via **WhisperX**
  or **pyannote.audio**. Keeping Whisper local means raw audio and transcripts stay on your own hardware —
  important for participant data protection; only de-identified, segmented passages later reach the (internal)
  LLM endpoint.

Then clean and segment each transcript into passages (one coding unit per `passage_id`) and continue below.

### 0. Setup
1. Fork and clone both repos.
2. Transcribe your interviews and segment each into **coding units** (passages) — typically one
   statement/idea per unit — with a stable `passage_id`. Keep them under `data/source/<your_corpus>/`.
3. Point the pipeline at an LLM endpoint: copy `config/llm_api.example.toml` → `config/llm_api.toml`
   and set your gateway / NVIDIA NIM / self-hosted vLLM endpoint (see `docs/local_serving.md`). For
   sensitive data, use an **institution-internal** endpoint — this is the single place to change it.
4. Pick models and seeds: 2–4 models for inductive generation, one strong "coder" model for deductive
   assignment, and one strong **judge** model (e.g. Claude Opus). Use **5 random seeds, temperature 0.7**.

### 1. Inductive category formation — build the codebook (Mayring, phase 1)
1. **Generate fine-category labels without a codebook.** For every passage, each model coins a short
   German (or other-language) fine-category label. Template: `code/inference/run_all_taskB.py`
   → `results/taskB_<model>_seed<k>.csv` (`passage_id; …; model_label`).
2. **Reduce** (Mayring Z3/Z4): merge semantically equivalent fine labels into a consolidated set of
   **fine categories**. The agent proposes merges; the expert confirms. Keep a `Reduction-Mapping.csv`
   (raw fine → merged fine) for full traceability.
3. **Abstract** the fine categories into **main categories**, then main categories into **dimensions**.
   Emit `data/codebook.json` — per main category `{id, name, dimension, definition, anchors:[fine titles]}`
   (use this repo's `data/codebook.json` as the schema). `code/inference/build_eval_set.py` is the
   template that turns a hand-coded ground truth into `eval_set.csv` + `codebook.json`.
4. **Expert review (human-in-the-loop):** a domain expert edits names/definitions, re-hangs
   mis-sorted fine categories and signs off. This step is irreplaceable.

### 2. Deductive application — apply the codebook (Mayring, phase 2)
1. **Closed-set assignment.** Each model assigns every passage to exactly one main category from your
   codebook. Template: `code/inference/run_all_taskA.py`, 5 seeds × temperature 0.7
   → `results/taskA_<model>_seed<k>.csv` + `leaderboard_taskA.csv`.
2. Reuse the fixed, constrained-JSON classification prompt in `demo/server/app.py`
   (`build_system_prompt`) for both batch assignment and the demonstrator — the model only ever sees
   the text and the fixed category list, never free-form instructions.

### 3. Calibration — make the numbers trustworthy
Automatic agreement overstates quality; calibrate it against humans.
1. **LLM-as-judge (inductive).** Build deduplicated label pairs with
   `code/inference/build_judge_pairs.py` (labels only — no passage text leaves this step), then have the
   judge rate each generated label vs the expert label as *same / related / different*. Report **strict**
   (% *same*) and **thematic** (% *same*+*related*) agreement, mean ± sample SD over seeds
   (`code/reproduce_taskB.py`).
2. **Human validation (two blinded raters).** Sample ~60 deductive assignments + ~100 inductive label
   pairs; two experts rate them blind. Compute inter-human Cohen's/Fleiss κ and the **human-acceptance
   rate** (share of model codings a human accepts as fitting or defensible) after population reweighting
   (`code/reproduce_human_validation.py`). Expect exact matching to badly **understate** acceptability.
3. **Judge reliability.** Run the judge 4× on a 300-pair subset (intra-rater Fleiss κ), add a second LLM
   judge (inter-judge κ) and compare judge-vs-human κ — the judge should sit **near** inter-human
   agreement, not above it. If it looks much better than humans, it is over-confident.
4. **Seed stability + significance.** Report per-seed SD and compare models with a **passage-clustered
   paired bootstrap** (passages as clusters, the 5 seeds as repeated measures) — see `code/reproduce_taskA.py`.
5. **Select the coder.** Carry forward the model with the best *human-accepted* agreement (not the best
   exact match), preferring a self-hostable one where data protection matters.

### 4. Reproduce & report, then deploy
- `code/reproduce_taskA.py`, `reproduce_taskB.py`, `reproduce_human_validation.py` regenerate every
  table from the stored predictions/verdicts — adapt the file globs to your corpus. Keep
  `results/RESULTS_taskA.md` / `RESULTS_taskB.md` as your report.
- **Demonstrator (optional):** swap `demo/server/categories.json` for your main-category definitions,
  point the server `.env` + `demo/web/app.js` `API_BASE` at your endpoint, and deploy (`demo/README.md`).
  It supports single-passage and whole-interview → CSV. For real/PII interviews, run it against an
  **institution-internal** endpoint, not the public NVIDIA one.

### Letting Agent-M run the whole cycle
Point your agent at **agent-m** with this repo as the worked example and your interviews as the
requirement source. Agent-M sequences the full pipeline — segmentation → inductive drafting →
reduction → expert review → deductive assignment → calibration → a released category system and
demonstrator — committing each artifact to your fork. See the *Vibe Coding* textbook for the
underlying agentic-engineering method. The only human-mandatory gates are the expert category review
(step 1.4) and the two-rater human validation (step 3.2).

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
