# Serving the models for an open, reproducible run

The reproduction scripts (`code/reproduce_*.py`) need **no** model access — they recompute the
tables from the stored predictions and verdicts. You only need a served model to **re-run
inference** (an optional extension; see the caveat in `DATA_STATEMENT.md`).

All evaluated models are open-weight and available from public sources (e.g. Hugging Face). You can
serve any of them behind an **OpenAI-compatible** `/v1/chat/completions` endpoint and point the
client at it.

## Option A — vLLM (OpenAI-compatible server)
```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
    --model <org/model-id> --port 8000
# endpoint: http://localhost:8000/v1
```

## Option B — SGLang
```bash
pip install "sglang[all]"
python -m sglang.launch_server --model-path <org/model-id> --port 8000
# endpoint: http://localhost:8000/v1
```

## Option C — NVIDIA NIM
Run the model's NIM container (or use a hosted NIM endpoint); it exposes an OpenAI-compatible API.
Use its base URL and API key below.

## Point the client at your endpoint
```bash
cp config/llm_api.example.toml config/llm_api.toml
# edit config/llm_api.toml:
#   base_url    = "http://localhost:8000/v1"   (or your NIM endpoint)
#   api_key     = "none"                        (or your endpoint key)
#   model       = "<org/model-id>"
#   judge_model = "<org/judge-model-id>"
```
`config/llm_api.toml` is gitignored and must never be committed. The client sends the key only in
the request header. See `code/inference/` for the Task A/B runners.
