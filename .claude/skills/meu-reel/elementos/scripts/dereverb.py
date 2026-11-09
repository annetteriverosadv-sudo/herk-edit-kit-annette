#!/usr/bin/env python3
"""Tira o eco da sala da voz (correção 2026-11-09: "parece banheiro", "deixa como microfone perto").

1) WPE (nara_wpe): remove a reverberação tardia prevendo-a a partir do passado do sinal.
2) Supressão espectral do "rabo" de reverberação (Lebart/Habets) com T60 estimado, ganho mínimo limitado.
Uso: python3 dereverb.py entrada.wav saida.wav [t60=0.5] [forca=1.0]
Entrada mono; trabalha em 48 kHz. Rode DEPOIS de tirar zumbido/graves e ANTES do RNNoise/EQ/compressão.
"""
import sys, numpy as np, soundfile as sf
from scipy.signal import stft, istft
from nara_wpe.wpe import wpe

inp, out = sys.argv[1], sys.argv[2]
T60 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
FORCA = float(sys.argv[4]) if len(sys.argv) > 4 else 0.6  # 0.6 = aprovado no 6x1; acima disso a fala começa a deformar
x, sr = sf.read(inp, dtype="float64")
if x.ndim > 1: x = x.mean(1)
N, H = 1536, 384                                    # 32 ms / 8 ms em 48 kHz
f, t, Y = stft(x, sr, nperseg=N, noverlap=N - H)
# 1) WPE (um canal): taps 10, atraso 3 quadros (~24 ms: preserva o som direto e as primeiras reflexões curtas)
Z = wpe(Y[None, :, :].transpose(1, 0, 2), taps=10, delay=3, iterations=3, statistics_mode="full").transpose(1, 0, 2)[0]
# 2) supressão do rabo: potência da reverberação tardia = potência de ~50 ms atrás, atenuada pelo decaimento do T60
P = np.abs(Z) ** 2
Ps = P.copy()
for k in range(1, P.shape[1]):                      # suavização temporal leve
    Ps[:, k] = 0.6 * Ps[:, k - 1] + 0.4 * P[:, k]
d = max(1, int(round(0.05 * sr / H)))
decay = np.exp(-2 * (3 * np.log(10) / T60) * d * H / sr)
Lr = np.zeros_like(P); Lr[:, d:] = decay * Ps[:, :-d]
G = np.maximum(1 - FORCA * Lr / (P + 1e-12), 0.0)
G = np.maximum(G, 10 ** (-12 / 20))                 # no máximo -12 dB, para não "picotar" a fala
for k in range(1, G.shape[1]):                      # suaviza a subida/descida do ganho
    G[:, k] = 0.5 * G[:, k] + 0.5 * G[:, k - 1]
_, y = istft(Z * G, sr, nperseg=N, noverlap=N - H)
y = y[: len(x)]
y *= np.sqrt(np.mean(x ** 2) / (np.mean(y ** 2) + 1e-12))
sf.write(out, np.clip(y, -1, 1), sr, subtype="PCM_16")
print(f"ok {out} (T60 {T60}s, força {FORCA})")
