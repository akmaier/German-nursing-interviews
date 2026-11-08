"use strict";
// RITA demo front-end. Hosted statically anywhere (e.g. the repo's GitHub Pages site); it calls
// the RITA proxy API on lme245. API_BASE is the public proxy URL (not secret); change it if the
// backend moves. CORS on the server must allow this page's origin (see ALLOWED_ORIGIN).
const API_BASE = "https://lme245.cs.fau.de/rita";

const $ = (id) => document.getElementById(id);
const textEl = $("text"), goEl = $("go"), goBatchEl = $("goBatch"), statusEl = $("status"),
      resultEl = $("result"), counterEl = $("counter");

const EXAMPLE =
  "Viele Kolleginnen und Kollegen würden wieder in die Pflege zurückkehren, wenn die " +
  "Dienstpläne verlässlicher wären und sich Familie und Schichtdienst besser vereinbaren ließen.";

let turnstileId = null, sitekey = "", maxChars = 4000, maxBatch = 20, turnstileReady = false;

// Cloudflare calls this when its script has finished loading (api.js?onload=onTurnstileReady).
window.onTurnstileReady = function () { turnstileReady = true; maybeRenderTurnstile(); };

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
    maxBatch = c.max_batch_passages || 20;
    const mb = $("maxBatch"); if (mb) mb.textContent = String(maxBatch);
    sitekey = c.turnstile_sitekey || "";
    maybeRenderTurnstile();
  } catch (e) { $("model").textContent = "—"; }
}

// Render exactly once, whenever BOTH the config (sitekey) and the Turnstile script are ready —
// regardless of which arrives first. Surfaces failures instead of hiding them.
function maybeRenderTurnstile() {
  if (!sitekey || !turnstileReady || turnstileId !== null || !window.turnstile) return;
  try {
    turnstileId = window.turnstile.render("#turnstile", {
      sitekey, theme: "auto",
      "error-callback": (code) => {
        setStatus("Bot-Prüfung konnte nicht geladen werden" + (code ? ` (Code ${code})` : "") +
          ". Bitte den Tracking-/Werbeschutz für diese Seite lockern oder einen anderen Browser versuchen.", true);
        return true;
      },
    });
    // If no challenge appears within a few seconds, hint the likely cause (browser tracking protection).
    setTimeout(() => {
      if (!document.querySelector("#turnstile iframe") && !token()) {
        setStatus("Hinweis: Die Cloudflare-Bot-Prüfung erscheint nicht — meist blockiert der Tracking-Schutz " +
          "des Browsers (etwa der verbesserte Schutz vor Aktivitätenverfolgung in Firefox). Bitte ihn für diese " +
          "Seite deaktivieren (Schild-Symbol in der Adressleiste) oder einen anderen Browser nutzen.", true);
      }
    }, 7000);
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

// ---- whole-interview mode: split -> batch classify -> table + CSV --------------------
function splitPassages(raw) {
  let parts = raw.split(/\n\s*\n/).map(s => s.replace(/\s+/g, " ").trim()).filter(Boolean);
  if (parts.length <= 1) parts = raw.split(/\n/).map(s => s.replace(/\s+/g, " ").trim()).filter(Boolean);
  return parts;
}

async function classifyBatch() {
  const raw = textEl.value.trim();
  if (!raw) { setStatus("Bitte einen Text eingeben.", true); return; }
  let passages = splitPassages(raw);
  if (!passages.length) { setStatus("Keine Passagen gefunden.", true); return; }
  let truncated = 0;
  if (passages.length > maxBatch) { truncated = passages.length - maxBatch; passages = passages.slice(0, maxBatch); }
  if (passages.some(p => p.length > maxChars)) {
    setStatus(`Eine Passage ist zu lang (max. ${maxChars} Zeichen). Bitte feiner gliedern.`, true); return;
  }
  const tok = token();
  if (sitekey && !tok) { setStatus("Bitte die Bot-Prüfung abschließen.", true); return; }

  goEl.disabled = true; goBatchEl.disabled = true;
  setStatus(`Klassifiziere ${passages.length} Passagen … das kann einen Moment dauern.`);
  $("batchResult").classList.add("hidden"); resultEl.classList.add("hidden");
  try {
    const r = await fetch(`${API_BASE}/api/classify_batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passages, turnstile_token: tok }),
    });
    const data = await r.json();
    if (!r.ok || data.ok === false) { setStatus(data.error || `Fehler (${r.status}).`, true); return; }
    setStatus("");
    renderBatch(data, truncated);
  } catch (e) {
    setStatus("Netzwerkfehler. Bitte erneut versuchen.", true);
  } finally {
    goEl.disabled = false; goBatchEl.disabled = false;
    if (sitekey && window.turnstile && turnstileId !== null) window.turnstile.reset(turnstileId);
  }
}

function renderBatch(data, truncated) {
  const rows = data.results || [];
  const body = rows.map((r, i) => {
    if (!r.ok) return `<tr><td>${i + 1}</td><td class="pcell">${esc(r.passage)}</td><td colspan="3" class="err">${esc(r.error || "Fehler")}</td></tr>`;
    if (r.classified === false) return `<tr><td>${i + 1}</td><td class="pcell">${esc(r.passage)}</td><td colspan="3">— nicht eindeutig —</td></tr>`;
    return `<tr><td>${i + 1}</td><td class="pcell">${esc(r.passage)}</td><td>${esc(r.id)}</td><td>${esc(r.name)}</td><td>${esc(r.dimension)}</td></tr>`;
  }).join("");
  const notes = [];
  if (truncated) notes.push(`${truncated} weitere Passage(n) nicht verarbeitet (Limit ${maxBatch} pro Durchlauf).`);
  if (data.skipped) notes.push(`${data.skipped} Passage(n) wegen Zeit- oder Kontingentlimit übersprungen.`);
  const el = $("batchResult");
  el.classList.remove("hidden");
  el.innerHTML = `
    <div class="batchhead"><h2>Ergebnis (${rows.length} Passagen)</h2>
      <button id="csv" type="button" class="secondary">CSV herunterladen</button></div>
    <div class="tablewrap"><table class="btable">
      <thead><tr><th>#</th><th>Passage</th><th>ID</th><th>Hauptkategorie</th><th>Dimension</th></tr></thead>
      <tbody>${body}</tbody></table></div>
    ${notes.length ? `<p class="note">${esc(notes.join(" "))}</p>` : ""}`;
  $("csv").addEventListener("click", () => downloadCSV(rows));
}

function csvCell(s) { s = String(s == null ? "" : s); return /[";\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; }
function downloadCSV(rows) {
  const lines = [["nr", "passage", "hauptkategorie_id", "hauptkategorie", "dimension", "alternativen"].join(";")];
  rows.forEach((r, i) => {
    const classified = r.ok && r.classified !== false;
    lines.push([i + 1, r.passage || "", classified ? (r.id || "") : "", classified ? (r.name || "") : "",
                classified ? (r.dimension || "") : "", r.alternativen || ""].map(csvCell).join(";"));
  });
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "mayring-klassifikation.csv";
  document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}

goEl.addEventListener("click", classify);
goBatchEl.addEventListener("click", classifyBatch);
updateCounter();
loadConfig();
