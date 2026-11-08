"use strict";
// RITA demo front-end. Hosted statically (e.g. the repo's GitHub Pages site); it calls the RITA
// proxy API on lme245. API_BASE is the public proxy URL (not secret). The UI language is read from
// the page's <html lang="…"> (de | en); the German nursing category taxonomy is returned as-is.
const API_BASE = "https://lme245.cs.fau.de/rita";

const LANG = (document.documentElement.lang || "de").toLowerCase().startsWith("en") ? "en" : "de";

const I18N = {
  de: {
    example: "Viele Kolleginnen und Kollegen würden wieder in die Pflege zurückkehren, wenn die " +
             "Dienstpläne verlässlicher wären und sich Familie und Schichtdienst besser vereinbaren ließen.",
    chars: n => `${n} Zeichen`,
    enterText: "Bitte einen Text eingeben.",
    tooLong: n => `Text zu lang (max. ${n} Zeichen).`,
    passageTooLong: n => `Eine Passage ist zu lang (max. ${n} Zeichen). Bitte feiner gliedern.`,
    completeChallenge: "Bitte die Bot-Prüfung abschließen.",
    classifying: "Klassifiziere …",
    classifyingN: n => `Klassifiziere ${n} Passagen … das kann einen Moment dauern.`,
    noPassages: "Keine Passagen gefunden.",
    networkError: "Netzwerkfehler. Bitte erneut versuchen.",
    errorStatus: s => `Fehler (${s}).`,
    turnstileError: code => "Bot-Prüfung konnte nicht geladen werden" + (code ? ` (Code ${code})` : "") +
             ". Bitte den Tracking-/Werbeschutz für diese Seite lockern oder einen anderen Browser versuchen.",
    turnstileHint: "Hinweis: Die Cloudflare-Bot-Prüfung erscheint nicht — meist blockiert der Tracking-Schutz " +
             "des Browsers (etwa der verbesserte Schutz vor Aktivitätenverfolgung in Firefox). Bitte ihn für diese " +
             "Seite deaktivieren (Schild-Symbol in der Adressleiste) oder einen anderen Browser nutzen.",
    resultTitle: "Ergebnis",
    notClassified: "Nicht eindeutig klassifizierbar.",
    suggested: "Vorgeschlagene Hauptkategorie",
    dimension: "Dimension",
    related: "Verwandte Kategorien",
    resultCount: n => `Ergebnis (${n} Passagen)`,
    downloadCsv: "CSV herunterladen",
    th: ["#", "Passage", "ID", "Hauptkategorie", "Dimension"],
    ambiguous: "— nicht eindeutig —",
    rowError: "Fehler",
    noteTruncated: (n, max) => `${n} weitere Passage(n) nicht verarbeitet (Limit ${max} pro Durchlauf).`,
    noteSkipped: n => `${n} Passage(n) wegen Zeit- oder Kontingentlimit übersprungen.`,
    csvHeader: ["nr", "passage", "hauptkategorie_id", "hauptkategorie", "dimension", "alternativen"],
    csvName: "mayring-klassifikation.csv",
  },
  en: {
    example: "Many colleagues would return to nursing if the shift schedules were more reliable and " +
             "family life could be better balanced with shift work.",
    chars: n => `${n} characters`,
    enterText: "Please enter some text.",
    tooLong: n => `Text too long (max. ${n} characters).`,
    passageTooLong: n => `One passage is too long (max. ${n} characters). Please split it more finely.`,
    completeChallenge: "Please complete the bot check.",
    classifying: "Classifying …",
    classifyingN: n => `Classifying ${n} passages … this may take a moment.`,
    noPassages: "No passages found.",
    networkError: "Network error. Please try again.",
    errorStatus: s => `Error (${s}).`,
    turnstileError: code => "The bot check could not be loaded" + (code ? ` (code ${code})` : "") +
             ". Please relax the tracking/ad protection for this site or try a different browser.",
    turnstileHint: "Note: the Cloudflare bot check is not showing — this is usually the browser's tracking " +
             "protection (e.g. Enhanced Tracking Protection in Firefox). Please disable it for this site " +
             "(shield icon in the address bar) or use a different browser.",
    resultTitle: "Result",
    notClassified: "Could not be classified unambiguously.",
    suggested: "Suggested main category",
    dimension: "Dimension",
    related: "Related categories",
    resultCount: n => `Result (${n} passages)`,
    downloadCsv: "Download CSV",
    th: ["#", "Passage", "ID", "Main category", "Dimension"],
    ambiguous: "— not clear —",
    rowError: "Error",
    noteTruncated: (n, max) => `${n} further passage(s) not processed (limit ${max} per run).`,
    noteSkipped: n => `${n} passage(s) skipped due to a time or quota limit.`,
    csvHeader: ["nr", "passage", "main_category_id", "main_category", "dimension", "alternatives"],
    csvName: "mayring-classification.csv",
  },
};
const L = I18N[LANG];

const $ = (id) => document.getElementById(id);
const textEl = $("text"), goEl = $("go"), goBatchEl = $("goBatch"), statusEl = $("status"),
      resultEl = $("result"), counterEl = $("counter");

let turnstileId = null, sitekey = "", maxChars = 4000, maxBatch = 20, turnstileReady = false;

window.onTurnstileReady = function () { turnstileReady = true; maybeRenderTurnstile(); };

function setStatus(msg, isErr) {
  statusEl.textContent = msg || "";
  statusEl.classList.toggle("err", !!isErr);
}
function updateCounter() { counterEl.textContent = L.chars(textEl.value.length); }

textEl.addEventListener("input", updateCounter);
$("example").addEventListener("click", () => { textEl.value = L.example; updateCounter(); textEl.focus(); });

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

function maybeRenderTurnstile() {
  if (!sitekey || !turnstileReady || turnstileId !== null || !window.turnstile) return;
  try {
    turnstileId = window.turnstile.render("#turnstile", {
      sitekey, theme: "auto",
      "error-callback": (code) => { setStatus(L.turnstileError(code), true); return true; },
    });
    setTimeout(() => {
      if (!document.querySelector("#turnstile iframe") && !token()) setStatus(L.turnstileHint, true);
    }, 7000);
  } catch (e) { /* already rendered */ }
}

function token() {
  if (sitekey && window.turnstile && turnstileId !== null) return window.turnstile.getResponse(turnstileId) || "";
  return "";
}

async function classify() {
  const text = textEl.value.trim();
  if (!text) { setStatus(L.enterText, true); return; }
  if (text.length > maxChars) { setStatus(L.tooLong(maxChars), true); return; }
  const tok = token();
  if (sitekey && !tok) { setStatus(L.completeChallenge, true); return; }

  goEl.disabled = true; setStatus(L.classifying); resultEl.classList.add("hidden");
  try {
    const r = await fetch(`${API_BASE}/api/classify`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, turnstile_token: tok }),
    });
    const data = await r.json();
    if (!r.ok || data.ok === false) setStatus(data.error || L.errorStatus(r.status), true);
    else if (data.classified === false) { setStatus(""); renderResult(null, data); }
    else { setStatus(""); renderResult(data.result, data); }
  } catch (e) { setStatus(L.networkError, true); }
  finally {
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
    resultEl.innerHTML = `<h2>${esc(L.resultTitle)}</h2><p>${esc(data.message || L.notClassified)}</p>`;
    return;
  }
  const alts = (res.alternativen || []).map(a =>
    `<li><span class="aid">${esc(a.id)}</span>${esc(a.name)}</li>`).join("");
  resultEl.innerHTML = `
    <h2>${esc(L.suggested)}</h2>
    <div class="cat-id">${esc(res.id)}</div>
    <div class="cat-name">${esc(res.name)}</div>
    <span class="chip">${esc(L.dimension)}: ${esc(res.dimension)}</span>
    <p class="def">${esc(res.definition)}</p>
    ${res.begruendung ? `<p class="begr">${esc(res.begruendung)}</p>` : ""}
    ${alts ? `<p class="chip">${esc(L.related)}</p><ul class="alts">${alts}</ul>` : ""}
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
  if (!raw) { setStatus(L.enterText, true); return; }
  let passages = splitPassages(raw);
  if (!passages.length) { setStatus(L.noPassages, true); return; }
  let truncated = 0;
  if (passages.length > maxBatch) { truncated = passages.length - maxBatch; passages = passages.slice(0, maxBatch); }
  if (passages.some(p => p.length > maxChars)) { setStatus(L.passageTooLong(maxChars), true); return; }
  const tok = token();
  if (sitekey && !tok) { setStatus(L.completeChallenge, true); return; }

  goEl.disabled = true; goBatchEl.disabled = true;
  setStatus(L.classifyingN(passages.length));
  $("batchResult").classList.add("hidden"); resultEl.classList.add("hidden");
  try {
    const r = await fetch(`${API_BASE}/api/classify_batch`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passages, turnstile_token: tok }),
    });
    const data = await r.json();
    if (!r.ok || data.ok === false) { setStatus(data.error || L.errorStatus(r.status), true); return; }
    setStatus(""); renderBatch(data, truncated);
  } catch (e) { setStatus(L.networkError, true); }
  finally {
    goEl.disabled = false; goBatchEl.disabled = false;
    if (sitekey && window.turnstile && turnstileId !== null) window.turnstile.reset(turnstileId);
  }
}

function renderBatch(data, truncated) {
  const rows = data.results || [];
  const body = rows.map((r, i) => {
    if (!r.ok) return `<tr><td>${i + 1}</td><td class="pcell">${esc(r.passage)}</td><td colspan="3" class="err">${esc(r.error || L.rowError)}</td></tr>`;
    if (r.classified === false) return `<tr><td>${i + 1}</td><td class="pcell">${esc(r.passage)}</td><td colspan="3">${esc(L.ambiguous)}</td></tr>`;
    return `<tr><td>${i + 1}</td><td class="pcell">${esc(r.passage)}</td><td>${esc(r.id)}</td><td>${esc(r.name)}</td><td>${esc(r.dimension)}</td></tr>`;
  }).join("");
  const notes = [];
  if (truncated) notes.push(L.noteTruncated(truncated, maxBatch));
  if (data.skipped) notes.push(L.noteSkipped(data.skipped));
  const el = $("batchResult");
  el.classList.remove("hidden");
  el.innerHTML = `
    <div class="batchhead"><h2>${esc(L.resultCount(rows.length))}</h2>
      <button id="csv" type="button" class="secondary">${esc(L.downloadCsv)}</button></div>
    <div class="tablewrap"><table class="btable">
      <thead><tr>${L.th.map(h => `<th>${esc(h)}</th>`).join("")}</tr></thead>
      <tbody>${body}</tbody></table></div>
    ${notes.length ? `<p class="note">${esc(notes.join(" "))}</p>` : ""}`;
  $("csv").addEventListener("click", () => downloadCSV(rows));
}

function csvCell(s) { s = String(s == null ? "" : s); return /[";\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; }
function downloadCSV(rows) {
  const lines = [L.csvHeader.join(";")];
  rows.forEach((r, i) => {
    const classified = r.ok && r.classified !== false;
    lines.push([i + 1, r.passage || "", classified ? (r.id || "") : "", classified ? (r.name || "") : "",
                classified ? (r.dimension || "") : "", r.alternativen || ""].map(csvCell).join(";"));
  });
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = L.csvName;
  document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}

goEl.addEventListener("click", classify);
goBatchEl.addEventListener("click", classifyBatch);
updateCounter();
loadConfig();
