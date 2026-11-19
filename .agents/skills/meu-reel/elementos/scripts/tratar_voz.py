#!/usr/bin/env python3
"""Trata a voz de cada gravação inteira ANTES de cortar (volume uniforme entre os trechos).
- Áudio externo (WhatsApp, gravado junto com o vídeo; source/ext/<take>.wav, já no tempo do vídeo):
  zumbido 58,6 Hz (medido nas pausas), RNNoise, presença suave, agudos amaciados, compressão,
  expansor bem suave depois da compressão, volume.
- Som da câmera (só onde não há áudio externo; ex. IMG_3737): zumbido/graves, dereverb.py (eco da sala),
  RNNoise e a mesma cadeia; depois um EQ de casamento que aproxima o timbre do som da câmera ao dos
  áudios externos (espectro médio da fala, limitado a ±6 dB).
Saída: source/voz/<take>.wav (48 kHz mono, mesmo tempo do vídeo).  Config: assets/externo.json + "camera": [takes]
"""
import json, os, subprocess, sys, numpy as np, soundfile as sf
from scipy.signal import welch, firwin2, fftconvolve
from plano import caminho
SR = 48000
CFG = json.load(open(caminho("assets", "externo.json")))
CAM = json.load(open(caminho("assets", "plano.json"))).get("camera_audio", [])
RNN = os.environ.get("RNNOISE_MODEL") or os.path.expanduser("~/tools/models/sh.rnnn")
os.makedirs(caminho("source", "voz"), exist_ok=True)
def ff(i, o, af):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", i, "-af", af, "-ac", "1", "-ar", str(SR),
                    "-c:a", "pcm_s24le", o], check=True)
COMUM = ("loudnorm=I=-20:TP=-3:LRA=11:linear=true,deesser=i=0.3,"
         "equalizer=f=200:t=q:w=1:g=-1,equalizer=f=3000:t=q:w=1.2:g=2,highshelf=f=9000:g=-1.5,"
         "acompressor=threshold=-24dB:ratio=3:attack=6:release=130:makeup=3,"
         "agate=threshold=0.02:ratio=2:range=0.12:attack=4:release=180:knee=4")
HUM = "highpass=f=80:poles=2,equalizer=f=58.6:t=h:w=4:g=-30,equalizer=f=117.2:t=h:w=5:g=-12,"
# RNNoise a 0,7 (a 0,9 já deformava "desconto indevido"); no gancho (áudio mais ruidoso) o RNNoise deformava
# "parece pouco, não é?": lá vai uma redução espectral leve e sem expansor.
LEVE = json.load(open(caminho("assets", "plano.json"))).get("ruido_leve", [])
for take in CFG:
    if take in LEVE:
        af = HUM + "afftdn=nr=10:nf=-45:tn=1," + COMUM.rsplit(",agate", 1)[0]
    else:
        af = HUM + f"arnndn=m='{RNN}':mix=0.7," + COMUM
    ff(caminho("source", "ext", take + ".wav"), caminho("source", "voz", take + ".wav"), af)
    print("voz tratada (externo):", take)

def ltas(x):
    h = SR // 100; n = len(x) // h
    db = 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-9)
    v = db > np.percentile(db, 60)
    seg = np.concatenate([x[i * h:(i + 1) * h] for i in np.where(v)[0]])
    f, P = welch(seg, SR, nperseg=4096); return f, 10 * np.log10(P + 1e-20)

for take in CAM:
    raw = caminho("source", "ext", f"_cam_{take}.wav")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", next(caminho("source", "orig", take + e) for e in (".MOV", ".mov", ".mp4") if os.path.exists(caminho("source", "orig", take + e))),
                    "-vn", "-ac", "1", "-ar", str(SR), raw], check=True)
    hum = caminho("source", "voz", f"_{take}_hum.wav"); dry = caminho("source", "voz", f"_{take}_dry.wav")
    ff(raw, hum, "highpass=f=90:poles=2")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "dereverb.py"), hum, dry, "0.5", "0.6"], check=True)
    pre = caminho("source", "voz", f"_{take}_pre.wav")
    ff(dry, pre, f"arnndn=m='{RNN}':mix=0.7," + COMUM)
    # EQ de casamento: espectro médio da fala da câmera -> o dos áudios externos tratados
    alvo = np.mean([ltas(sf.read(caminho("source", "voz", t + ".wav"))[0])[1] for t in CFG], axis=0)
    x, _ = sf.read(pre); f, cur = ltas(x)
    d = alvo - cur
    d -= np.average(d[(f > 300) & (f < 3000)])          # só a forma, não o volume
    # suaviza em ~1/3 de oitava e limita
    sm = np.array([d[(f >= fc / 1.12) & (f <= fc * 1.12)].mean() if fc > 40 else 0 for fc in f])
    sm = np.clip(sm, -5, 4)  # agudos no máximo +4 dB (mais que isso realça chiado); sm[f < 70] = 0; sm[f > 12000] = np.clip(sm[f > 12000], -6, 0)
    taps = firwin2(2047, f / (SR / 2), 10 ** (sm / 20))
    y = fftconvolve(x, taps, mode="same")
    sf.write(caminho("source", "voz", f"_{take}_eq.wav"), y, SR, subtype="PCM_24")
    ff(caminho("source", "voz", f"_{take}_eq.wav"), caminho("source", "voz", take + ".wav"), "loudnorm=I=-20:TP=-3:LRA=11:linear=true")
    # a cadeia (dereverb + EQ) atrasa a voz ~11 ms em relação à imagem (medido contra o som original): adianta
    z, _ = sf.read(caminho("source", "voz", take + ".wav")); dd = int(0.011 * SR)
    sf.write(caminho("source", "voz", take + ".wav"), np.concatenate([z[dd:], np.zeros(dd)]), SR, subtype="PCM_24")
    print("voz tratada (câmera + casamento de timbre):", take, "EQ aplicado (dB) em 150/500/1k/3k/6k/10k:",
          [round(float(np.interp(h, f, sm)), 1) for h in (150, 500, 1000, 3000, 6000, 10000)])

# volume igual entre as gravações (fala ativa)
for take in list(CFG) + CAM:
    p = caminho("source", "voz", take + ".wav"); x, _ = sf.read(p)
    h = SR // 100; n = len(x) // h
    db = 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-9)
    print(f"{take}: fala p90 {np.percentile(db, 90):.1f} dB, pausa p10 {np.percentile(db, 10):.1f} dB")
