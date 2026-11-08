"use strict";
// RITA demo front-end. Hosted statically anywhere (e.g. the repo's GitHub Pages site); it calls
// the RITA proxy API on lme245. API_BASE is the public proxy URL (not secret); change it if the
// backend moves. CORS on the server must allow this page's origin (see ALLOWED_ORIGIN).
const API_BASE = "https://lme245.cs.fau.de/rita";

const $ = (id) => document.getElementById(id);
const textEl = $("text"), goEl = $("go"), statusEl = $("status"),
      resultEl = $("result"), counterEl = $("counter");

const EXAMPLE =
  "Viele Kolleginnen und Kollegen würden wieder in die Pflege zurückkehren, wenn die " +
  "Dienstpläne verlässlicher wären und sich Familie und Schichtdienst besser vereinbaren ließen.";

let turnstileId = null, sitekey = "", maxChars = 4000;

function setStatus(msg, isErr) {
  statusEl.textContent = msg || "";
  statusEl.classList.toggle("err", !!isErr);
}
function updateCounter() { counterEl.textContent = `${textEl.value.length} Zeichen`; }

textEl.addEventListener("input", updateCounter);
$("example").addEventListener("click", () => {
  textEl.value = EXAMPLE; updateCounter(); textEl.focus();
});

async function loadConfig() {
  try {
    const r = await fetch(`${API_BASE}/api/config`);
    const c = await r.json();
    $("model").textContent = c.model_display || "—";
    maxChars = c.max_input_chars || 4000;
    textEl.setAttribute("maxlength", String(maxChars));
    sitekey = c.turnstile_sitekey || "";
    if (sitekey && window.turnstile) renderTurnstile();
    else if (sitekey) {
      // api.js may still be loading; retry shortly
      const t = setInterval(() => {
        if (window.turnstile) { clearInterval(t); renderTurnstile(); }
      }, 300);
      setTimeout(() => clearInterval(t), 6000);
    }
  } catch (e) { $("model").textContent = "—"; }
}

function renderTurnstile() {
  try {
    turnstileId = window.turnstile.render("#turnstile", { sitekey, theme: "auto" });
  } catch (e) { /* already rendered */ }
}

function token() {
  if (sitekey && window.turnstile && turnstileId !== null) {
    return window.turnstile.getResponse(turnstileId) || "";
  }
  return "";
}

async function classify() {
  const text = textEl.value.trim();
  if (!text) { setStatus("Bitte einen Text eingeben.", true); return; }
  if (text.length > maxChars) { setStatus(`Text zu lang (max. ${maxChars} Zeichen).`, true); return; }
  const tok = token();
  if (sitekey && !tok) { setStatus("Bitte die Bot-Prüfung abschließen.", true); return; }

  goEl.disabled = true; setStatus("Klassifiziere …"); resultEl.classList.add("hidden");
  try {
    const r = await fetch(`${API_BASE}/api/classify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, turnstile_token: tok }),
    });
    const data = await r.json();
    if (!r.ok || data.ok === false) {
      setStatus(data.error || `Fehler (${r.status}).`, true);
    } else if (data.classified === false) {
      setStatus("");
      renderResult(null, data);
    } else {
      setStatus("");
      renderResult(data.result, data);
    }
  } catch (e) {
    setStatus("Netzwerkfehler. Bitte erneut versuchen.", true);
  } finally {
    goEl.disabled = false;
    if (sitekey && window.turnstile && turnstileId !== null) window.turnstile.reset(turnstileId);
  }
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderResult(res, data) {
  resultEl.classList.remove("hidden");
  if (!res) {
    resultEl.innerHTML = `<h2>Ergebnis</h2><p>${esc(data.message || "Nicht eindeutig klassifizierbar.")}</p>`;
    return;
  }
  const alts = (res.alternativen || []).map(a =>
    `<li><span class="aid">${esc(a.id)}</span>${esc(a.name)}</li>`).join("");
  resultEl.innerHTML = `
    <h2>Vorgeschlagene Hauptkategorie</h2>
    <div class="cat-id">${esc(res.id)}</div>
    <div class="cat-name">${esc(res.name)}</div>
    <span class="chip">Dimension: ${esc(res.dimension)}</span>
    <p class="def">${esc(res.definition)}</p>
    ${res.begruendung ? `<p class="begr">${esc(res.begruendung)}</p>` : ""}
    ${alts ? `<p class="chip">Verwandte Kategorien</p><ul class="alts">${alts}</ul>` : ""}
    ${data.note ? `<p class="note">${esc(data.note)}</p>` : ""}`;
}

goEl.addEventListener("click", classify);
updateCounter();
loadConfig();
