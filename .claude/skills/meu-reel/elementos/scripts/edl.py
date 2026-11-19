#!/usr/bin/env python3
"""Passo 3 — monta a lista de cortes (EDL) a partir de assets/plano.json ("blocos").

Para cada bloco (gravação + palavra inicial + palavra final): encontra a fala, corta pausas >= 0,30 s
(deixa 0,08 s antes e 0,14 s depois da fala), alinha cada trecho a quadros inteiros e define o
enquadramento igual (rosto ~20,5% da altura, olhos a 28% do topo) com aproximação de 110% alternando por frase.
Precisa de transcripts/<take>.json (Whisper local) e assets/faces.json (preparar.py).
Grava assets/edl.json e assets/transcript.json (tempos do vídeo já cortado).
"""
import json, os, subprocess
import numpy as np
from plano import ROOT, caminho, carregar, palavra

WORK = caminho("source", "work")
TR = caminho("transcripts")
PRE, POST, MIN_GAP = 0.08, 0.14, 0.30
_P = json.load(open(caminho("assets", "plano.json")))
# 19/11: "nos pontos em que ela demora a falar a palavra, corte e já deixe na palavra sendo dita"
PRE, POST, MIN_GAP = _P.get("pre", PRE), _P.get("pos", POST), _P.get("pausa_min", MIN_GAP)
FACE_TARGET, EYE_TARGET = 0.175, 0.28  # rosto 17,5% (aberto) a ~19% (fechado)
FACES = json.load(open(caminho("assets", "faces.json")))
PLANO = carregar()
# 19/11 ("o enquadramento tá estranho"): rosto do MESMO tamanho em todos os cortes, como na referência (~22-23%).
# O alvo é o maior entre o pedido e o mínimo que cada gravação exige para os olhos ficarem a 28%.
if PLANO.get("rosto_fixo"):
    FACE_TARGET = max(PLANO["rosto_fixo"], max(f["fh"] * (1 - EYE_TARGET) / (1 - f["eye"]) for f in FACES.values()))


def voiced_runs(take):
    # 19/11: pausas medidas no áudio externo ANTES do tratamento (a compressão "enche" as pausas);
    # sem áudio externo, na voz da câmera já sem eco
    cands = [caminho("source", "ext", take + ".wav"), caminho("source", "voz", f"_{take}_dry.wav"), os.path.join(WORK, take + ".mov")]
    if take in PLANO.get("camera_audio", []):  # 19/11 v4: pausas medidas na MESMA voz que vai ao ar (câmera sem eco)
        cands = [caminho("source", "voz", f"_{take}_dry.wav"), caminho("source", "voz_cam", f"_{take}_dry.wav")] + cands
    src = next(c for c in cands if os.path.exists(c))
    def env(af):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-af", af, "-f", "s16le", "-"],
                             capture_output=True).stdout
        x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        hop = 160; n = len(x) // hop
        db = 20 * np.log10(np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1)) + 1e-9)
        floor, peak = np.percentile(db, 8), np.percentile(db, 95)
        return db, floor, peak, n
    db, floor, peak, n = env("highpass=f=150,lowpass=f=3800")
    # 19/11: o detector só via graves/médios e cortava o "des" de "descontos": a faixa aguda (S, X, F) também conta
    dh, fh, ph, nh = env("highpass=f=3500,lowpass=f=7800")
    n = min(n, nh)
    vl = db[:n] > floor + 0.45 * (peak - floor)          # fala (médios)
    vh = dh[:n] > fh + 0.45 * (ph - fh)                   # chiado de S/X/F (agudos)
    runs, i = [], 0
    while i < n:
        if vl[i]:
            j = i
            while j < n and vl[j]: j += 1
            a, b = i, j
            # 19/11 v4: a faixa aguda só ESTENDE o começo/fim da palavra (no máx. 0,25 s), sem tapar a pausa
            while a > 0 and vh[a - 1] and i - a < 25: a -= 1
            while b < n and vh[b] and b - j < 25: b += 1
            runs.append([a / 100, b / 100]); i = j
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < 0.12: merged[-1][1] = r[1]
        else: merged.append(r)
    return [r for r in merged if r[1] - r[0] >= 0.08]


def load_words(take, runs):
    words = json.load(open(os.path.join(TR, take + ".json")))["words"]
    # A word whose aligned start falls in silence is moved to the speech it belongs to:
    # a word that ends a phrase (.,?!) is pulled back to the end of the previous run,
    # any other word is pushed to the next voiced onset.
    for k, w in enumerate(words):
        inside = any(a - 0.05 <= w["start"] <= b for a, b in runs)
        if inside:
            continue
        prev = [(a, b) for a, b in runs if b <= w["start"]]
        nxt = [a for a, b in runs if a > w["start"] and a - w["start"] <= 0.7]
        est = max(0.18, 0.065 * len(w["text"].strip(".,!?")))
        if w["text"][-1:] in ".,?!" and prev and w["start"] - prev[-1][1] <= 0.6:
            lo = words[k - 1]["start"] + 0.08 if k else 0
            w["start"] = max(lo, prev[-1][1] - est)
            w["end"] = prev[-1][1]
        elif nxt:
            w["start"] = nxt[0]; w["end"] = max(w["end"], w["start"] + 0.1)
    for k in range(1, len(words)):  # keep order
        if words[k]["start"] < words[k - 1]["start"]:
            words[k]["start"] = words[k - 1]["start"] + 0.02
    return words


def crop_for(take, punch):
    f = FACES[take]
    # base zoom: face at FACE_TARGET, raised if needed so the eye line can sit at EYE_TARGET
    base = max(FACE_TARGET / f["fh"], (1 - EYE_TARGET) / (1 - f["eye"]))
    s = base * punch                               # zoom relative to the full frame
    wh = 1 / s                                     # window size as a fraction of the frame
    y0 = min(max(f["eye"] - EYE_TARGET * wh, 0), 1 - wh)
    x0 = min(max(f["cx"] - 0.5 * wh, 0), 1 - wh)
    return dict(zoom=round(s, 4), x=round(x0, 4), y=round(y0, 4), w=round(wh, 4),
                eye_out=round((f["eye"] - y0) / wh, 3), face_out=round(f["fh"] * s, 3))


takes = sorted({b["take"] for b in PLANO["blocos"]})
runs = {t: voiced_runs(t) for t in takes}
words = {t: load_words(t, runs[t]) for t in takes}
blocks = [(b["take"], palavra(words[b["take"]], b["de"]), palavra(words[b["take"]], b["ate"]), b["nome"], b.get("burn", True), b.get("plano"))
          for b in PLANO["blocos"]]
# aproximações suaves pedidas: (take, índice da palavra) -> o trecho que começa nela ganha zoom animado na composição
ZOOM = {(z["take"], palavra(words[z["take"]], z["em"])) for z in PLANO.get("aproximacoes", [])}
# planos escolhidos à mão: (take, índice da 1ª palavra do trecho) -> 1.0 (aberto) ou 1.1 (fechado)
PLANOS = {(z["take"], palavra(words[z["take"]], z["em"])): z["plano"] for z in PLANO.get("planos", [])}

clips, out_words, t_out, punch = [], [], 0.0, 1.0
for bi, (take, a, b, label, flash, fixo) in enumerate(blocks):
    ws = words[take][a:b + 1]
    allw = words[take]
    s0, s1 = ws[0]["start"], ws[-1]["end"]
    prev_end = allw[a - 1]["end"] if a > 0 else 0.0
    next_start = allw[b + 1]["start"] if b + 1 < len(allw) else 1e9
    s1 = min(s1, next_start - 0.05)
    lo, hi = max(s0 - 0.05, prev_end), min(s1 + 0.25, next_start - PRE - POST)
    rr = [[max(r[0], lo), min(r[1], hi)] for r in runs[take] if r[1] > lo and r[0] < s1]
    rr = [r for r in rr if r[1] - r[0] > 0.04]
    # split into sub-clips at long pauses
    subs = [[rr[0][0] - PRE, rr[0][1] + POST]]
    for (pa, pb), (na, nb) in zip(rr, rr[1:]):
        if na - pb >= max(MIN_GAP, PRE + POST + 0.10):  # 19/11 v4: só corta se sobrar >= 0,1 s de silêncio para tirar
            subs.append([na - PRE, nb + POST])
        else:
            subs[-1][1] = nb + POST
    # 19/11 v4: trecho com menos de 0,5 s não vira corte próprio (dá pulo estranho): junta com o anterior
    k = 1
    while k < len(subs):
        if subs[k][1] - subs[k][0] < 0.5 or subs[k - 1][1] - subs[k - 1][0] < 0.5:
            subs[k - 1][1] = subs[k][1]; del subs[k]
        else:
            k += 1
    # snap every clip to a whole number of frames so video and audio lengths match exactly
    subs = [[round(ia * 30) / 30, round(ia * 30) / 30 + max(1, round((ib - ia) * 30)) / 30] for ia, ib in subs]
    for si, (ia, ib) in enumerate(subs):
        seg_words = [w for w in ws if ia - 0.02 <= w["start"] < ib]
        # punch-in toggles when a new sentence starts (block start or after . ? !)
        zoom = any((take, words[take].index(w)) in ZOOM for w in seg_words[:1])
        if si == 0 or PLANO.get("rosto_fixo"):  # rosto fixo: sem alternar aberto/fechado
            punch = 1.0                      # cada bloco novo volta ao plano aberto
        elif clips and clips[-1]["last_text"][-1:] in ".?!:" and not PLANO.get("rosto_fixo"):
            punch = 1.0 if punch != 1.0 else 1.10
        first = (take, words[take].index(seg_words[0])) if seg_words else None
        if first in PLANOS:
            punch = PLANOS[first]
        if zoom:
            punch = 1.10                     # conta como fechado para a alternância
        if fixo:                             # bloco com plano fixo (ex.: encerramento em plano fechado)
            punch, zoom = fixo, False
        clip = dict(take=take, src_in=round(ia, 3), src_out=round(ib, 3), out_in=round(t_out, 3),
                    block=label, punch=punch, burn=bool(flash and si == 0 and bi > 0), zoom=zoom,
                    crop=crop_for(take, 1.0 if zoom else punch),
                    last_text=seg_words[-1]["text"] if seg_words else "")
        for w in seg_words:
            st = t_out + max(0.0, w["start"] - ia)
            en = t_out + min(ib - ia, max(w["end"], w["start"] + 0.08) - ia)
            out_words.append(dict(text=w["text"], start=round(st, 3), end=round(en, 3), type="word",
                                  take=take, src_start=w["start"]))
        t_out += ib - ia
        clip["out_out"] = round(t_out, 3)
        clips.append(clip)

# monotonic word ends
for k in range(len(out_words) - 1):
    out_words[k]["end"] = min(out_words[k]["end"], out_words[k + 1]["start"])

json.dump(dict(fps=30, width=1080, height=1920, duration=round(t_out, 3), clips=clips),
          open(os.path.join(ROOT, "assets", "edl.json"), "w"), indent=1, ensure_ascii=False)
json.dump(dict(language_code="pt", audio_duration_secs=round(t_out, 3),
               text=" ".join(w["text"] for w in out_words), words=out_words),
          open(os.path.join(ROOT, "assets", "transcript.json"), "w"), indent=1, ensure_ascii=False)
print(f"{len(clips)} clips, {t_out:.2f}s")
for c in clips:
    print(f"{c['out_in']:6.2f}-{c['out_out']:6.2f}  {c['take']} {c['src_in']:6.2f}-{c['src_out']:6.2f} "
          f"punch={c['punch']} zoom={c['zoom']} burn={c['burn']} eye={c['crop']['eye_out']} face={c['crop']['face_out']} "
          f"[{c['block']}] ...{c['last_text']}")
