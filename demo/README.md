# RITA — Mayring category classifier (public demo)

A small public web demo that classifies a German nursing-interview snippet into one of the
**27 Mayring main categories** from the RITA study, using a hosted LLM (default: NVIDIA
Nemotron-3-Ultra-550B via NIM). Companion to the paper *Zöllner, Mages & Maier*.

It is deliberately **not** a general chat endpoint: the browser only ever sends the text to
classify, the server owns the entire prompt and forces a constrained, validated answer.

```
 Browser (static page)
   │  POST ./api/classify  { text, turnstile_token }
   ▼
 Apache 2.4 on lme245.cs.fau.de  (443, existing TLS vhost)
   │  ProxyPass /rita/ → http://127.0.0.1:8090/
   ▼
 FastAPI proxy (uvicorn, systemd; API key in env only)
   • builds the fixed 27-category German prompt from categories.json
   • caps input & output, validates the returned id ∈ 27
   • per-IP rate limit · global daily budget breaker · kill switch · Turnstile
   ▼
 NVIDIA NIM  (Nemotron)         ← ~77 ms from lme245
```

## Why it can't be abused as an open endpoint
- **Not a relay.** The client sends only `{text}`. The server fixes the model, parameters and
  system prompt, caps `max_tokens`, and returns **only a category id validated against the 27**
  (plus a short rationale). It cannot be coaxed into generating arbitrary content.
- **Body-size cap.** Oversized requests are rejected *before* parsing (app middleware
  `MAX_BODY_BYTES` + Apache `LimitRequestBody`), so a giant body can't exhaust memory ahead of
  the other checks.
- **Bounded cost.** Per-IP rate limit (`RATE_PER_MIN`, `RATE_PER_DAY`) is enforced **before** a
  global `DAILY_CALL_CAP` breaker (reserve-then-release, so transport failures don't burn budget;
  one IP can't drain the shared cap). Spend is bounded and known. A `KILL_FILE` disables it instantly.
- **Bot challenge, fail-closed.** Cloudflare **Turnstile** is verified server-side. If the secret
  is missing the endpoint refuses (503) rather than opening up — override only with
  `ALLOW_INSECURE_NO_TURNSTILE=1` for local dev.
- **Shared-host trust boundary.** The box runs other apps, so localhost-bind isn't enough: Apache
  injects a secret `X-Rita-Proxy` nonce and the app rejects `/api/classify` without it, so a
  co-tenant or an SSRF can't hit `127.0.0.1:8090` directly with a forged client IP.
- **Key hygiene.** The NIM key lives only in an `EnvironmentFile` outside the repo; it is never
  in the source or the client. Put a spending cap on the NVIDIA key as a backstop.
- **Privacy.** Raw input is never logged (only an HMAC-hashed IP + length + result). Users are
  told the text goes to NVIDIA and is not stored.

> Run with **one worker** (`--workers 1`, as the unit does): the rate-limiter and budget counter
> are in-process. To scale out, move them to shared storage (e.g. Redis) first.

## Files
```
server/app.py            FastAPI proxy (all logic + abuse controls)
server/categories.json   27 main categories: id, name, dimension, definition (NO interview text)
server/requirements.txt  fastapi, uvicorn, httpx
server/.env.example      environment template (copy & fill OUTSIDE the repo)
web/                     static front-end (index.html, app.js, style.css)
deploy/rita-demo.service systemd unit
deploy/apache-rita.conf  Apache snippet (add inside the existing *:443 vhost)
```

## Deploy on lme245 (collaborative — some steps need you)
1. **Cloudflare Turnstile:** create a widget for `lme245.cs.fau.de` → note the **site key** (public)
   and **secret key**.
2. **Copy the code:** `rsync` `server/` and `web/` to `/home/akmaier/rita-demo/` (keep the
   `server/`, `web/` layout; the venv goes in `/home/akmaier/rita-demo/.venv`).
3. **venv:** `python3 -m venv /home/akmaier/rita-demo/.venv && \
   /home/akmaier/rita-demo/.venv/bin/pip install -r /home/akmaier/rita-demo/server/requirements.txt`
4. **Secrets:** copy `server/.env.example` → `/home/akmaier/rita-demo.env`, fill in
   `NIM_API_KEY`, `TURNSTILE_SITEKEY`, `TURNSTILE_SECRET`, a long random `PROXY_SHARED_SECRET`
   and a random `LOG_SALT`; `chmod 600` it. (Generate nonces with `openssl rand -hex 32`.)
5. **Service:** install `deploy/rita-demo.service` → `/etc/systemd/system/`, then
   `sudo systemctl daemon-reload && sudo systemctl enable --now rita-demo`.
   Check: `curl -s localhost:8090/api/health` (should show `proxy_guard:true`, `turnstile:true`).
6. **Apache:** paste `deploy/apache-rita.conf` inside the existing `<VirtualHost *:443>` for
   `lme245.cs.fau.de`, **replacing `REPLACE_WITH_A_LONG_RANDOM_NONCE` with the same value you
   put in `PROXY_SHARED_SECRET`**, then `sudo apachectl configtest && sudo systemctl reload apache2`.
7. **Verify:** open `https://lme245.cs.fau.de/rita/`, classify the example.

**Kill switch:** `touch /home/akmaier/rita-demo/DISABLED` (→ 503), `rm` it to re-enable.

## Notes
- Confirm the exact NIM catalog id for Nemotron before go-live (the hosted catalog drifts); the
  model endpoint is a single env var, so swapping models (or to a local vLLM) is a one-line change.
- A live single-shot at low temperature can differ from the paper's 5-seed majority (temp 0.7);
  the UI says so.
- No interview passages are used or shipped — only the 27 category definitions.
- **Hosting the page on GitHub Pages.** The front-end (`web/`) is static and runs from the repo's
  GitHub Pages site; it calls the API on `lme245.cs.fau.de` **cross-origin**. Point `API_BASE` in
  `web/app.js` at `https://lme245.cs.fau.de/rita` and set the server's `ALLOWED_ORIGIN` to the Pages
  origin (e.g. `https://akmaier.github.io`). lme245 must present a valid public-CA TLS cert (it does —
  same 443 vhost as the other services) so the browser allows the cross-origin fetch. Enable Pages to
  serve `web/` (e.g. copy it to `/docs` or set Pages source to the `web/` path).
