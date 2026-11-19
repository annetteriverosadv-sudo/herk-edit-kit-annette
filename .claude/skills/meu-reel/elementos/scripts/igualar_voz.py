#!/usr/bin/env python3
"""Iguala o som de todas as gravações (19/11: "deixe todos os sons parecidos e igualados, a diferença é muito grande").
1) Som da câmera (sem agudos acima de ~6 kHz): brilho recriado de leve (aexciter) antes do casamento.
2) Timbre: espectro médio da fala de cada gravação levado a UM alvo comum (média de todas), FIR suavizado em
   1/3 de oitava, limitado a ±8 dB; acima de 8 kHz todas são cortadas igual (onde a câmera não tem som).
3) Volume: a fala de todas no mesmo nível (loudness integrado), pausas no mesmo nível (expansor igual).
Lê source/voz/<take>.wav (cópia em source/voz_antes_igualar/) e grava por cima. Rode depois do tratar_voz.py."""
import json, os, shutil, subprocess, numpy as np, soundfile as sf
from scipy.signal import welch, firwin2, fftconvolve
from plano import caminho, carregar
SR = 48000; P = carregar()
CAM = P.get("camera_audio", [])
takes = sorted(f[:-4] for f in os.listdir(caminho("source", "voz")) if f.endswith(".wav") and not f.startswith("_"))
bk = caminho("source", "voz_antes_igualar"); os.makedirs(bk, exist_ok=True)
for t in takes:
    if not os.path.exists(os.path.join(bk, t + ".wav")):
        shutil.copy(caminho("source", "voz", t + ".wav"), os.path.join(bk, t + ".wav"))
def ff(i, o, af):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", i, "-af", af, "-ac", "1", "-ar", str(SR), "-c:a", "pcm_f32le", o], check=True)
def ltas(x):
    h = SR // 100; n = len(x) // h
    db = 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-9)
    v = db > np.percentile(db, 55)
    seg = np.concatenate([x[i * h:(i + 1) * h] for i in np.where(v)[0]])
    f, Pw = welch(seg, SR, nperseg=4096); return f, 10 * np.log10(Pw + 1e-20)
tmp = {}
for t in takes:
    src = os.path.join(bk, t + ".wav"); o = f"/tmp/ig1_{t}.wav"
    if t in CAM:   # recria um pouco de brilho (harmônicos acima de 3,5 kHz) no som abafado da câmera
        ff(src, o, "aexciter=amount=2.5:drive=7:blend=0:freq=3500:ceil=9999,highpass=f=80")
    else:
        ff(src, o, "highpass=f=80")
    tmp[t] = sf.read(o)[0]
specs = {t: ltas(tmp[t]) for t in takes}
f = specs[takes[0]][0]
norm = lambda d: d - d[(f > 300) & (f < 1000)].mean()
alvo = np.mean([norm(specs[t][1]) for t in takes if t not in CAM], axis=0)   # alvo: timbre médio dos externos...
alvo = np.where(f > 6000, alvo - np.clip((f - 6000) / 2000 * 4, 0, 6), alvo)   # ...com o excesso de agudo amaciado
smooth = lambda d: np.array([d[(f >= fc / 1.12) & (f <= fc * 1.12)].mean() if fc > 40 else 0 for fc in f])
os.makedirs(caminho("assets"), exist_ok=True); rel = {}
for t in takes:
    d = smooth(alvo - norm(specs[t][1]))
    d = np.clip(d, -8, 8); d[f < 80] = 0; d[f > 8000] = d[np.argmin(abs(f - 8000))]
    taps = firwin2(4095, f / (SR / 2), 10 ** (d / 20))
    y = fftconvolve(tmp[t], taps, mode="same")
    sf.write(f"/tmp/ig2_{t}.wav", y, SR, subtype="FLOAT")
    rel[t] = [round(float(np.interp(h, f, d)), 1) for h in (150, 500, 2000, 4000, 7000)]
# volume igual (fala) + pausas iguais + corte comum acima de 8,5 kHz
for t in takes:
    ff(f"/tmp/ig2_{t}.wav", caminho("source", "voz", t + ".wav"),
       "lowpass=f=8500:poles=2,loudnorm=I=-19:TP=-3:LRA=7:linear=true,"
       "agate=threshold=0.02:ratio=2:range=0.15:attack=4:release=180:knee=4,loudnorm=I=-19:TP=-3:LRA=7:linear=true")
    print(t, "EQ (dB) em 150/500/2k/4k/7k:", rel[t])
