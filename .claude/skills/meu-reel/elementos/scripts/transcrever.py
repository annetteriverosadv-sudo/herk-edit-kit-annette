#!/usr/bin/env python3
"""Transcrição local por trechos (quando o Whisper "pula" fala: áudio baixo, zumbido, "vai!" no começo).

1. Roda o Whisper com VAD (Silero) só para achar os trechos de fala, no tempo real da gravação.
2. Junta trechos próximos e transcreve cada um separado (npm run transcribe -- --start/--duration),
   com tempos palavra por palavra (DTW), já no tempo da gravação original.
3. Grava transcripts/<take>.json no formato do kit.
Uso: python3 scripts/transcrever.py <take> [<take> ...]   (take = nome em source/work, sem .mov)
"""
import json, os, subprocess, sys, tempfile
from plano import caminho

KIT = os.path.abspath(caminho("..", ".."))
PROMPT = os.environ.get("PROMPT_TEMA", "")


def run_tr(src, out, extra):
    cmd = ["npm", "run", "-s", "transcribe", "--", src, "-o", out] + extra
    if PROMPT:
        cmd += ["--prompt", PROMPT]
    r = subprocess.run(cmd, cwd=KIT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout + r.stderr)
    return json.load(open(out))


def trechos_de_fala(src):
    """Trechos de fala pelo volume (sem o Whisper): corta nas pausas >= 0,35 s; trechos de 0,3 a 8 s."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000",
                          "-af", "highpass=f=150,lowpass=f=3800", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = len(x) // 160
    db = 20 * np.log10(np.sqrt(np.mean(x[:n * 160].reshape(n, 160) ** 2, axis=1)) + 1e-9)
    db = np.convolve(db, np.ones(3) / 3, "same")
    floor, peak = np.percentile(db, 8), np.percentile(db, 95)
    v = db > floor + 0.35 * (peak - floor)
    runs, i = [], 0
    while i < n:
        if v[i]:
            j = i
            while j < n and v[j]: j += 1
            runs.append([i / 100, j / 100]); i = j
        else:
            i += 1
    runs = [r for r in runs if r[1] - r[0] >= 0.06]
    ch = []
    for r in runs:
        if ch and r[0] - ch[-1][1] < 0.35 and r[1] - ch[-1][0] <= 8:
            ch[-1][1] = r[1]
        else:
            ch.append(list(r))
    return [c for c in ch if c[1] - c[0] >= 0.25]


for take in sys.argv[1:]:
    src = caminho("source", "work", take + ".mov")
    tmp = tempfile.mkdtemp()
    chunks = trechos_de_fala(src)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                               capture_output=True, text=True).stdout)
    words = []
    for k, (a, b) in enumerate(chunks):
        st = max(0.0, a - 0.30, chunks[k - 1][1] if k else 0.0)
        en = min(dur, b + 0.40, chunks[k + 1][0] if k + 1 < len(chunks) else dur)
        part = run_tr(src, os.path.join(tmp, f"c{k}.json"), ["--start", f"{st:.3f}", "--duration", f"{en - st:.3f}"])
        pw = [w for w in part["words"] if w["type"] == "word"]
        print(f"  {take} trecho {k}: {st:6.2f}-{en:6.2f}  {' '.join(w['text'] for w in pw)}")
        words += pw
    for i in range(1, len(words)):
        if words[i]["start"] < words[i - 1]["start"]:
            words[i]["start"] = words[i - 1]["start"] + 0.01
    json.dump(dict(language_code="pt", audio_duration_secs=dur, provider="whisper.cpp (local, por trechos VAD)",
                   text=" ".join(w["text"] for w in words), words=words),
              open(caminho("transcripts", take + ".json"), "w"), indent=1, ensure_ascii=False)
    print(take, "ok:", len(words), "palavras")
