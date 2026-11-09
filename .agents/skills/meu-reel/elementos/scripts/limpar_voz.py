#!/usr/bin/env python3
"""Limpeza de voz reforçada (correção de 09/11/2026: voz baixa e com eco, "parecia dentro de um banheiro").

Entrada: assets/cut_raw.mov (áudio do corte, gerado pelo render_cut.py). Saída: assets/voice.wav (48 kHz, mono).
Ordem: zumbido -> eco da sala (WPE) -> ruído (RNNoise + redução espectral) -> fecha caudas de eco entre palavras
-> equalização (tira o "abafado" de sala, dá presença) -> compressão -> volume.
Precisa: pip install nara_wpe noisereduce; modelo RNNoise em ~/tools/models/sh.rnnn (ou $RNNOISE_MODEL).
"""
import os, subprocess, sys
import numpy as np
from plano import caminho, carregar

SR = 48000
RNN = os.environ.get("RNNOISE_MODEL") or os.path.expanduser("~/tools/models/sh.rnnn")
A = caminho("assets")
tmp = lambda n: os.path.join(A, n)


def ff(args):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y"] + args, capture_output=True, text=True)
    if r.returncode: sys.exit(r.stderr[-1500:])


def ler(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def gravar(path, x):
    p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-c:a", "pcm_f32le", path], input=x.astype(np.float32).tobytes(), capture_output=True)
    if p.returncode: sys.exit(p.stderr.decode()[-800:])


def lufs(path):
    import re
    o = subprocess.run(["ffmpeg", "-nostdin", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[0-9.]+) LUFS", o)[-1])


# 1) zumbido (~57/113/170 Hz) e apito (~3,87 kHz) desta gravação
ff(["-i", tmp("cut_raw.mov"), "-vn", "-ac", "1", "-ar", str(SR), "-af",
    "highpass=f=120:poles=2,highpass=f=120:poles=2,bandreject=f=57:width_type=h:w=8,bandreject=f=113:width_type=h:w=8,"
    "bandreject=f=170:width_type=h:w=10,bandreject=f=3870:width_type=h:w=60", "-c:a", "pcm_f32le", tmp("v0_hum.wav")])
# a gravação vem muito baixa (~-36 LUFS): sobe para ~-20 antes de limpar, senão o RNNoise apaga a voz fraca
g0 = -20.0 - lufs(tmp("v0_hum.wav"))
ff(["-i", tmp("v0_hum.wav"), "-af", f"volume={g0:.2f}dB", "-c:a", "pcm_f32le", tmp("v1_hum.wav")])

# 2) eco da sala: WPE (dereverberação por predição linear), 1 canal
from nara_wpe.wpe import wpe
from nara_wpe.utils import stft, istft
x = ler(tmp("v1_hum.wav"))
size, shift = 2048, 512
Y = stft(x[None, :], size=size, shift=shift).transpose(2, 0, 1)     # (F, D, T)
Z = wpe(Y, taps=20, delay=2, iterations=3, statistics_mode="full").transpose(1, 2, 0)
y = istft(Z, size=size, shift=shift)[0][:len(x)]
y = np.pad(y, (0, len(x) - len(y)))
gravar(tmp("v2_wpe.wav"), y)

# 3) ruído: redução espectral ensinada com amostras REAIS do ruído (pausas das gravações, "amostras_ruido" no plano),
#    com o mesmo filtro de zumbido e o mesmo ganho. Sem amostra, o filtro confunde a voz baixa com ruído.
import noisereduce as nr
HUM = ("highpass=f=120:poles=2,highpass=f=120:poles=2,bandreject=f=57:width_type=h:w=8,bandreject=f=113:width_type=h:w=8,"
       "bandreject=f=170:width_type=h:w=10,bandreject=f=3870:width_type=h:w=60")
ruido = []
for take, ss, t in carregar().get("amostras_ruido", []):
    src = next(p for p in (caminho("source", "orig", take + e) for e in (".MOV", ".mov", ".mp4")) if os.path.exists(p))
    ff(["-ss", str(ss), "-t", str(t), "-i", src, "-vn", "-ac", "1", "-ar", str(SR), "-af", f"{HUM},volume={g0:.2f}dB",
        "-c:a", "pcm_f32le", tmp("ruido.wav")])
    ruido.append(ler(tmp("ruido.wav")))
z = ler(tmp("v2_wpe.wav"))
if ruido:
    z = nr.reduce_noise(y=z, sr=SR, y_noise=np.concatenate(ruido), stationary=True, prop_decrease=0.9,
                        n_fft=2048, n_std_thresh_stationary=1.3, freq_mask_smooth_hz=300, time_mask_smooth_ms=60)
gravar(tmp("v3_rnn.wav"), z)
# (RNNoise testado aqui: baixava a voz junto com o ruído; fica de fora)
os.replace(tmp("v3_rnn.wav"), tmp("v4_nr.wav"))

# 4) caudas de eco entre palavras (expansor suave), 5) equalização, 6) compressão e volume
chain = ("agate=threshold=0.02:ratio=2.5:range=0.25:attack=4:release=140:knee=3,"
         "equalizer=f=180:t=q:w=1:g=-1.5,equalizer=f=400:t=q:w=1.2:g=-3.5,equalizer=f=900:t=q:w=1.4:g=-1.5,"
         "equalizer=f=3200:t=q:w=1.0:g=3,highshelf=f=9000:g=0.5,"
         "deesser=i=0.6:m=0.6:f=0.45,"
         "acompressor=threshold=-26dB:ratio=4:attack=6:release=110:knee=4:makeup=4,"
         "acompressor=threshold=-12dB:ratio=2.5:attack=2:release=60:makeup=1")
ff(["-i", tmp("v4_nr.wav"), "-af", chain, "-ar", str(SR), "-c:a", "pcm_f32le", tmp("v5_eq.wav")])
g = -14.0 - lufs(tmp("v5_eq.wav"))
ff(["-i", tmp("v5_eq.wav"), "-af", f"volume={g:.2f}dB,alimiter=limit=0.84:attack=1:release=50:level=false",
    "-ar", str(SR), "-c:a", "pcm_s16le", tmp("voice.wav")])
print(f"voz: {lufs(tmp('voice.wav')):.1f} LUFS")
for n in ("ruido.wav", "v0_hum.wav", "v5_eq.wav", "v1_hum.wav", "v2_wpe.wav", "v4_nr.wav"):
    if not os.environ.get("MANTER"): os.remove(tmp(n))
print("voz limpa:", tmp("voice.wav"))
