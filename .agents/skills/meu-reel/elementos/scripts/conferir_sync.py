#!/usr/bin/env python3
"""Confere a sincronia boca x locução: passa o som original pelo mesmo ajuste de tempo da imagem
(edl.json) e compara com a locução. Atraso perto de 0 ms = boca no tempo do som."""
import json, sys, numpy as np, soundfile as sf
from plano import caminho
EDL = json.load(open(caminho("assets", "edl.json"))); E = EDL["clips"]
vo, _ = sf.read(caminho("assets", "voice_vo_raw.wav")) if len(sys.argv) < 2 else sf.read(sys.argv[1])


def logenv(x, hop):
    n = len(x) // hop; return np.log(np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, 1)) + 1e-4)


envS = {t: logenv(sf.read(caminho("assets", f"src16_{t}.wav"))[0], 160) for t in {c["take"] for c in E}}
envV = logenv(vo, 480)
if "audio" in EDL:  # simula a voz no tempo de saída pelo mapa (não precisa renderizar)
    ev = logenv(sf.read(caminho("assets", "vo_emendada.wav"))[0], 480)
    envV = np.full(int(round(EDL["duration"] * 100)), np.log(1e-4))
    for g in EDL["audio"]:
        mp = np.array(g["mapa"]); k0 = int(round(g["out_in"] * 100))
        for k in range(k0, min(k0 + int(round(g["frames"] / 30 * 100)), len(envV))):
            j = int(np.interp(k / 100 - g["out_in"], mp[:, 0], mp[:, 1]) * 100)
            if 0 <= j < len(ev): envV[k] = ev[j]
warp = np.full(len(envV), np.nan)
for c in E:
    p = np.array(c["pecas"])
    for k in range(int(round(c["out_in"] * 100)), min(int(round(c["out_out"] * 100)), len(warp))):
        j = int((c["src_in"] + np.interp(k / 100 - c["out_in"], p[:, 0], p[:, 1])) * 100)
        if 0 <= j < len(envS[c["take"]]): warp[k] = envS[c["take"]][j]


def lagm(a, b, maxl=25):
    ok = ~np.isnan(a) & ~np.isnan(b); a, b = a.copy(), b.copy(); a[~ok] = np.nanmean(a); b[~ok] = np.nanmean(b)
    a = (a - a.mean()) / (a.std() + 1e-9); b = (b - b.mean()) / (b.std() + 1e-9)
    cs = [np.mean(a[max(0, L):len(a) + min(0, L)] * b[max(0, -L):len(b) - max(0, L)]) for L in range(-maxl, maxl + 1)]
    k = int(np.argmax(cs)); return (k - maxl) * 10, cs[k]


blocks = []
for c in E:
    if not blocks or blocks[-1][0] != c["block"]: blocks.append([c["block"], c["out_in"], c["out_out"]])
    else: blocks[-1][2] = c["out_out"]
for nm, a, b in blocks:
    L, cb = lagm(warp[int(a * 100):int(b * 100)], envV[int(a * 100):int(b * 100)])
    print(f"{nm:20s} atraso da boca {L:+5d} ms (corr {cb:.2f})")
bad = []
for a in np.arange(0, len(envV) / 100 - 2, 0.5):
    L, cb = lagm(warp[int(a * 100):int((a + 2) * 100)], envV[int(a * 100):int((a + 2) * 100)], 15)
    if cb > 0.5 and abs(L) >= 80: bad.append((round(float(a), 1), L))
print("janelas de 2 s com |atraso| >= 80 ms:", bad if bad else "nenhuma")
