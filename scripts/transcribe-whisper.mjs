#!/usr/bin/env node
// Transcribe a video/audio file LOCALLY with whisper.cpp -> word-level JSON.
// Nothing is uploaded: audio is extracted with ffmpeg and transcribed on this machine.
// Output matches the kit's common transcript format (same shape the ElevenLabs
// helper produced): { language_code, audio_duration_secs, text, words: [{ text, start, end, type }] }
//
// Usage:
//   node scripts/transcribe-whisper.mjs <input> [options]
//
// Options:
//   --output, -o <path>   default: <input-without-ext>.json next to the source
//   --model <path>        ggml model file (default: WHISPER_MODEL from env/.env)
//   --bin <path>          whisper-cli binary (default: WHISPER_CPP_BIN from env/.env)
//   --language, -l <code> default: WHISPER_LANGUAGE from env/.env, else "pt"
//   --start <secs>        transcribe from this point of the source (test clips)
//   --duration <secs>     transcribe only this many seconds (test clips)
//   --threads <n>         CPU threads (default: all cores)
//   --prompt <text>       optional context/vocabulary hint for Whisper
//   --dtw <preset|off>    token-level timing (default: auto from model name, e.g. small)
//   --keep-audio          keep the extracted 16 kHz WAV next to the output
//
// Times are always written on the SOURCE timeline: when --start is used, the
// offset is added back so word times match the original recording.

import { readFileSync, writeFileSync, existsSync, unlinkSync, mkdtempSync, rmSync } from "node:fs";
import { dirname, join, resolve, basename, extname } from "node:path";
import { spawnSync } from "node:child_process";
import { argv, exit, env } from "node:process";
import { fileURLToPath } from "node:url";
import { tmpdir, availableParallelism } from "node:os";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const WORKSPACE_ROOT = resolve(SCRIPT_DIR, "..");

function die(msg, code = 1) {
  console.error(msg);
  exit(code);
}

// --- read .env (without overriding real environment variables) ---
const dotenvValues = {};
const dotenvPath = join(WORKSPACE_ROOT, ".env");
if (existsSync(dotenvPath)) {
  for (const line of readFileSync(dotenvPath, "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) dotenvValues[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
}
const cfg = (name) => env[name] || dotenvValues[name] || "";

// --- parse args ---
const args = argv.slice(2);
if (args.length === 0 || args.includes("--help") || args.includes("-h")) {
  console.log(
    "Usage: node scripts/transcribe-whisper.mjs <input> [--output path] [--model path] " +
      "[--bin path] [--language pt] [--start secs] [--duration secs] [--threads n] " +
      "[--prompt text] [--dtw preset|off] [--keep-audio]",
  );
  exit(args.length === 0 ? 1 : 0);
}

const opts = {
  input: null,
  output: null,
  model: cfg("WHISPER_MODEL"),
  bin: cfg("WHISPER_CPP_BIN"),
  language: cfg("WHISPER_LANGUAGE") || "pt",
  start: 0,
  duration: null,
  threads: Math.max(1, availableParallelism()),
  prompt: "",
  dtw: cfg("WHISPER_DTW") || "auto",
  keepAudio: false,
};
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--output" || a === "-o") opts.output = args[++i];
  else if (a === "--model") opts.model = args[++i];
  else if (a === "--bin") opts.bin = args[++i];
  else if (a === "--language" || a === "-l" || a === "--lang") opts.language = args[++i];
  else if (a === "--start") opts.start = Number(args[++i]);
  else if (a === "--duration") opts.duration = Number(args[++i]);
  else if (a === "--threads") opts.threads = Number(args[++i]);
  else if (a === "--prompt") opts.prompt = args[++i];
  else if (a === "--dtw") opts.dtw = args[++i];
  else if (a === "--keep-audio") opts.keepAudio = true;
  else if (a.startsWith("--")) die(`unknown option: ${a}`);
  else if (!opts.input) opts.input = a;
  else die(`unexpected argument: ${a}`);
}
if (!opts.input) die("no input file given");
if (!Number.isFinite(opts.start) || opts.start < 0) die("--start must be a number >= 0");
if (opts.duration !== null && (!Number.isFinite(opts.duration) || opts.duration <= 0))
  die("--duration must be a number > 0");

const resolveFromRoot = (p) => (p ? resolve(WORKSPACE_ROOT, p) : "");
opts.bin = resolveFromRoot(opts.bin);
opts.model = resolveFromRoot(opts.model);
if (!opts.bin || !existsSync(opts.bin))
  die(`whisper-cli not found. Set WHISPER_CPP_BIN in .env or pass --bin. (got: ${opts.bin || "empty"})`);
if (!opts.model || !existsSync(opts.model))
  die(`Whisper model not found. Set WHISPER_MODEL in .env or pass --model. (got: ${opts.model || "empty"})`);

const inputPath = resolve(opts.input);
if (!existsSync(inputPath)) die(`input not found: ${inputPath}`);
const inputStem = basename(inputPath, extname(inputPath));
const outputPath = resolve(opts.output ?? join(dirname(inputPath), `${inputStem}.json`));

// --- source duration (ffprobe) ---
const probe = spawnSync(
  "ffprobe",
  ["-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", inputPath],
  { encoding: "utf8" },
);
if (probe.status !== 0) die(`ffprobe failed: ${probe.stderr}`);
const sourceDuration = Number(probe.stdout.trim());
if (!Number.isFinite(sourceDuration)) die("could not read source duration with ffprobe");
if (opts.start >= sourceDuration) die(`--start ${opts.start}s is past the end (${sourceDuration.toFixed(2)}s)`);
const clipEnd = opts.duration === null ? sourceDuration : Math.min(sourceDuration, opts.start + opts.duration);

// --- extract 16 kHz mono WAV (whisper.cpp input format) ---
const workDir = mkdtempSync(join(tmpdir(), "whisper-"));
const wavPath = join(workDir, `${inputStem}.wav`);
const ffArgs = ["-v", "error", "-y"];
if (opts.start > 0) ffArgs.push("-ss", String(opts.start));
ffArgs.push("-i", inputPath);
if (opts.duration !== null) ffArgs.push("-t", String(clipEnd - opts.start));
ffArgs.push("-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wavPath);
const ff = spawnSync("ffmpeg", ffArgs, { encoding: "utf8" });
if (ff.status !== 0) die(`ffmpeg audio extraction failed: ${ff.stderr}`);

// --- DTW preset from the model file name (ggml-small.bin -> small) ---
if (opts.dtw === "auto") {
  const m = basename(opts.model).match(/^ggml-(tiny|base|small|medium|large-v[123](?:-turbo)?|large)(\.en)?\.bin$/);
  opts.dtw = m ? m[1].replace(/-/g, ".") + (m[2] ?? "") : "off";
}
const useDtw = opts.dtw !== "off";

// --- run whisper.cpp ---
// DTW mode: natural segments, token-level aligned times (needs flash attention off).
// Fallback: one segment per word (-ml 1 -sow), coarser timing.
const outPrefix = join(workDir, "out");
const wArgs = ["-m", opts.model, "-f", wavPath, "-l", opts.language, "-t", String(opts.threads)];
if (useDtw) wArgs.push("-dtw", opts.dtw, "-nfa");
else wArgs.push("-ml", "1", "-sow");
wArgs.push("-ojf", "-of", outPrefix, "-np");
if (opts.prompt) wArgs.push("--prompt", opts.prompt);
console.log(
  `transcribing locally with ${basename(opts.model)} (${opts.language}, ` +
    `${useDtw ? `dtw ${opts.dtw}` : "segment timing"}), ${(clipEnd - opts.start).toFixed(1)}s of audio ...`,
);
const t0 = Date.now();
const w = spawnSync(opts.bin, wArgs, { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
if (w.status !== 0) die(`whisper-cli failed (exit ${w.status}):\n${w.stderr}`);
const raw = JSON.parse(readFileSync(`${outPrefix}.json`, "utf8"));

// --- normalize to the kit's word format ---
const round = (n) => Math.round(n * 1000) / 1000;
const words = [];
const isEventText = (t) => /^[\[(].*[\])]$/.test(t); // e.g. [Música], (risos)

if (useDtw) {
  // Build words from tokens: a token starting with a space opens a new word;
  // sub-word pieces and punctuation join the current word.
  const groups = [];
  for (const seg of raw.transcription ?? []) {
    const segEnd = (seg.offsets?.to ?? 0) / 1000;
    for (const tok of seg.tokens ?? []) {
      const t = tok.text ?? "";
      if (!t || /^\[_/.test(t)) continue; // special tokens
      const at = tok.t_dtw >= 0 ? tok.t_dtw / 100 : (tok.offsets?.from ?? 0) / 1000;
      const cur = groups[groups.length - 1];
      if (!cur || /^\s/.test(t) || cur.segEnd !== segEnd) {
        groups.push({ text: t.trim(), start: at, last: at, lastLen: t.trim().length, segEnd });
      } else {
        cur.text += t;
        cur.last = at;
        cur.lastLen = t.length;
      }
    }
  }
  const real = groups.filter((g) => g.text && !/^[.,!?;:…]+$/.test(g.text));
  for (let i = 0; i < groups.length; i++) {
    const g = groups[i];
    if (!g.text) continue;
    if (/^[.,!?;:…]+$/.test(g.text) && words.length) {
      words[words.length - 1].text += g.text; // stray punctuation token
      continue;
    }
    const next = real[real.indexOf(g) + 1];
    // A word ends when the next one starts, unless there is a pause: then it
    // ends shortly after its last aligned token (and never past its segment).
    const natural = g.last + Math.max(0.12, 0.06 * g.lastLen) + 0.1;
    let end = Math.min(next ? next.start : g.segEnd, natural, g.segEnd);
    if (end < g.start) end = g.start;
    words.push({
      text: g.text,
      start: round(opts.start + g.start),
      end: round(opts.start + end),
      type: isEventText(g.text) ? "audio_event" : "word",
    });
  }
}

for (const seg of useDtw ? [] : raw.transcription ?? []) {
  const rawText = seg.text ?? "";
  const text = rawText.trim();
  if (!text) continue;
  let start = opts.start + (seg.offsets?.from ?? 0) / 1000;
  let end = opts.start + (seg.offsets?.to ?? 0) / 1000;
  if (end < start) end = start;
  const isEvent = /^[\[(].*[\])]$/.test(text); // e.g. [Música], (risos)
  const prev = words[words.length - 1];
  // Punctuation or a word piece that whisper split without a leading space joins the previous word.
  if (prev && prev.type === "word" && !isEvent && !/^\s/.test(rawText)) {
    prev.text += text;
    prev.end = round(Math.max(prev.end, end));
    continue;
  }
  words.push({ text, start: round(start), end: round(end), type: isEvent ? "audio_event" : "word" });
}
// keep times monotonic
for (let i = 1; i < words.length; i++) {
  if (words[i].start < words[i - 1].start) words[i].start = words[i - 1].start;
  if (words[i].end < words[i].start) words[i].end = words[i].start;
}

const result = {
  language_code: opts.language,
  audio_duration_secs: round(clipEnd),
  source_duration_secs: round(sourceDuration),
  ...(opts.start > 0 || opts.duration !== null
    ? { clip: { start: round(opts.start), end: round(clipEnd) } }
    : {}),
  provider: "whisper.cpp (local)",
  model: basename(opts.model),
  text: words.filter((x) => x.type === "word").map((x) => x.text).join(" "),
  words,
};
writeFileSync(outputPath, JSON.stringify(result, null, 2));

if (opts.keepAudio) {
  const keep = outputPath.replace(/\.json$/i, "") + ".16k.wav";
  writeFileSync(keep, readFileSync(wavPath));
}
rmSync(workDir, { recursive: true, force: true });

const secs = ((Date.now() - t0) / 1000).toFixed(1);
const wordCount = words.filter((x) => x.type === "word").length;
console.log(`ok ${secs}s | ${wordCount} words | ${(clipEnd - opts.start).toFixed(1)}s audio | ${outputPath}`);
