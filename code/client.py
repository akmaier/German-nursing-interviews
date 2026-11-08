#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal OpenAI-compatible client for any OpenAI-compatible endpoint (open weights served via vLLM/SGLang, or NVIDIA NIM).
Reads config/llm_api.toml at RUNTIME (never printed/committed). The API key lives only in the
request header; error messages carry status + response body, never the key.
"""
import os, json, tomllib, urllib.request, urllib.error

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH=os.path.join(ROOT,"config","llm_api.toml")

def _clean(v):
    if not v: return None
    s=str(v)
    return None if (s.startswith("replace-") or s=="your-key-here") else s

def _load():
    with open(CFG_PATH,"rb") as f: d=tomllib.load(f)
    llm=d.get("llm",{})
    return {
        "base_url": (llm.get("base_url") or "http://localhost:8000/v1").rstrip("/"),
        "api_key": _clean(llm.get("api_key")),
        "model": llm.get("model") or "gpt-oss-120b",
        "judge_model": llm.get("judge_model"),
        "timeout": int(llm.get("timeout_seconds") or 60),
    }
CFG=_load()

def _req(path, method="GET", payload=None, timeout=None):
    if not CFG["api_key"]:
        raise RuntimeError("Kein API-Key in config/llm_api.toml (oder noch Platzhalter).")
    url=CFG["base_url"]+path
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {CFG['api_key']}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout or CFG["timeout"]) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body=e.read().decode(errors="replace")[:800]
        raise RuntimeError(f"HTTP {e.code} {path}: {body}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error {path}: {e.reason}") from None

def list_models():
    return _req("/models")

def chat(messages, model=None, temperature=0, max_tokens=600, timeout=None, **kw):
    p={"model": model or CFG["model"], "messages": messages,
       "temperature": temperature, "max_tokens": max_tokens}
    p.update(kw)
    return _req("/chat/completions","POST",p,timeout=timeout)

if __name__=="__main__":
    # safe self-test: prints base_url + whether a key is present, never the key itself
    print("base_url:", CFG["base_url"])
    print("default model:", CFG["model"], "| judge:", CFG["judge_model"])
    print("api_key present:", bool(CFG["api_key"]))
