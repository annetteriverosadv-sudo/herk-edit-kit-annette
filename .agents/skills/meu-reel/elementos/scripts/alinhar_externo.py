#!/usr/bin/env python3
"""Áudio externo gravado AO MESMO TEMPO que o vídeo (outro celular): acha o deslocamento exato
(GCC-PHAT, precisão de amostra) entre o som da câmera e o áudio externo, mede se escorrega ao longo
da gravação (janelas de 3 s) e grava source/ext/<take>.wav: o áudio externo já no tempo do vídeo
(48 kHz mono, mesmo comprimento do vídeo). Config: assets/externo.json {take: arquivo_do_audio}."""
import json, os, subprocess, sys, numpy as np, soundfile as sf
from scipy.signal import resample_poly
from plano import caminho
CFG = json.load(open(caminho("assets", "externo.json")))
SR = 48000
def ld(p, sr=SR, cam=False):
    tmp = f"/tmp/al_{os.path.basename(p)}_{sr}.wav"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", p, "-vn", "-ac", "1", "-ar", str(sr), tmp], check=True)
    return sf.read(tmp, dtype="float64")[0]
def gcc(a, b, maxlag):
    """atraso de b em relação a a (s, positivo = b atrasado), restrito a ±maxlag amostras."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    A, B = np.fft.rfft(a, n), np.fft.rfft(b, n)
    R = A * np.conj(B); R /= np.abs(R) + 1e-12
    f = np.fft.rfftfreq(n, 1 / SR); R[(f < 300) | (f > 3500)] = 0   # só a faixa da voz
    r = np.fft.irfft(R, n); r = np.concatenate([r[-maxlag:], r[:maxlag + 1]])
    k = int(np.argmax(r)); return (k - maxlag), r[k] / (np.mean(np.abs(r)) + 1e-12)
os.makedirs(caminho("source", "ext"), exist_ok=True)
res = {}
for take, cfg in CFG.items():
    cam = ld(caminho("source", "work", take + ".mov"))
    ext_full = ld(caminho(cfg["arquivo"]))
    bp = lambda x: x - np.convolve(x, np.ones(48) / 48, mode="same")  # tira graves (motor)
    c, e = bp(cam), bp(ext_full)
    off0 = cfg["off"]  # estimativa grosseira (s): tempo do áudio externo onde o vídeo começa
    # 1) deslocamento global com toda a gravação
    i0 = int(off0 * SR)
    seg = e[max(0, i0 - SR): i0 + len(c) + SR]
    lag, q = gcc(seg, c, SR)
    off = (max(0, i0 - SR) + lag) / SR
    if "fixo" in cfg: off = cfg["fixo"]  # mediana das janelas, quando o áudio externo tem eco e o pico varia
    # 2) janelas de 3 s para ver se escorrega
    pts = []
    for t in np.arange(0.5, len(c) / SR - 3, 1.5):
        a = c[int(t * SR):int((t + 3) * SR)]
        if np.sqrt(np.mean(a ** 2)) < 1e-3: continue
        j = int((t + off) * SR)
        b = e[j - 2400:j + int(3 * SR) + 2400]
        lg, qq = gcc(b, a, 4800)
        o = (j - 2400 + lg) / SR - t
        if qq > 8 and abs(o - off) < 0.04: pts.append((t, o))
    pts = np.array(pts)
    if len(pts) >= 3 and np.ptp(pts[:, 0]) > 6:
        k, b0 = np.polyfit(pts[:, 0], pts[:, 1], 1)
    else:
        k, b0 = 0.0, off
    print(f"{take}: deslocamento {off:.4f}s (qualidade {q:.0f}); janelas: " +
          " ".join(f"{t:.1f}s→{o*1000-off*1000:+.1f}ms" for t, o in pts) + f" | deriva {k*1e6:+.0f} ppm")
    # 3) áudio externo no tempo do vídeo (com correção de deriva, se houver)
    tv = np.arange(len(cam)) / SR
    src_t = b0 + tv * (1 + k) if abs(k) > 2e-5 else off + tv
    ext_al = np.interp(src_t * SR, np.arange(len(ext_full)), ext_full, left=0, right=0)
    sf.write(caminho("source", "ext", take + ".wav"), ext_al, SR, subtype="PCM_24")
    res[take] = dict(off=round(off, 5), deriva_ppm=round(k * 1e6, 1), janelas=[(round(t, 2), round(o, 5)) for t, o in pts])
json.dump(res, open(caminho("assets", "externo_sync.json"), "w"), indent=1)
