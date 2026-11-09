#!/usr/bin/env python3
"""Passo 4 — renderiza o corte da fala (vídeo + voz limpa) a partir dos ORIGINAIS 4K, usando assets/edl.json.

Each clip: frame-accurate seek, crop to the uniform framing, scale to 1080x1920, 30 fps,
12 ms audio micro-fades. Clips are concatenated, then the voice chain is applied.
Outputs assets/cut.mp4 (video, silent-safe) and assets/voice.wav (cleaned voice, 48 kHz).
"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

from plano import ROOT, caminho, carregar
PLANO = carregar()
ORIG = caminho("source", "orig")
TMP = os.path.join(ROOT, "assets", "clips")
# Limpeza de voz RNNoise: $RNNOISE_MODEL ou ~/tools/models/sh.rnnn
# (github.com/GregorR/rnnoise-models, somnolent-hogwash-2018-09-01/sh.rnnn). Sem ele, só a redução espectral.
RNN = os.environ.get("RNNOISE_MODEL") or os.path.expanduser("~/tools/models/sh.rnnn")
os.makedirs(TMP, exist_ok=True)
edl = json.load(open(os.path.join(ROOT, "assets", "edl.json")))



def _orig(take):
    for ext in (".MOV", ".mov", ".mp4", ".MP4"):
        p = os.path.join(ORIG, take + ext)
        if os.path.exists(p): return p
    sys.exit(f"original não encontrado: {take}")


def _size(path):  # largura/altura já com a rotação do celular aplicada
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:stream_side_data=rotation", "-of", "json", path],
                       capture_output=True, text=True).stdout
    st = json.loads(o)["streams"][0]
    w, h = st["width"], st["height"]
    rot = next((abs(int(float(d["rotation"]))) for d in st.get("side_data_list", []) if "rotation" in d), 0)
    return (h, w) if rot in (90, 270) else (w, h)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ffmpeg failed:\n" + r.stderr[-2000:])


def clip_job(k_c):
    k, c = k_c
    nfr = round((c["src_out"] - c["src_in"]) * 30)
    dur = nfr / 30
    cr = c["crop"]
    SW, SH = _size(_orig(c["take"]))
    w, h = round(cr["w"] * SW / 2) * 2, round(cr["w"] * SH / 2) * 2
    x, y = round(cr["x"] * SW), round(cr["y"] * SH)
    # correção de luz só quando ela pede ("corrigir_luz": true no plano): rosto mais claro, levemente quente, nitidez leve
    cc = ("eq=gamma=1.10:contrast=1.05:saturation=1.04,colorbalance=rm=0.03:bm=-0.03,unsharp=5:5:0.35,"
          if PLANO.get("corrigir_luz") else "")
    vf = (f"crop={w}:{h}:{x}:{y},scale=1080:1920:flags=lanczos,{cc}fps=30,setsar=1,"
          f"trim=end_frame={nfr},setpts=PTS-STARTPTS")
    af = (f"aresample=48000,apad,atrim=end={dur:.6f},asetpts=PTS-STARTPTS,"
          f"afade=t=in:d=0.012,afade=t=out:st={max(0, dur - 0.012):.3f}:d=0.012")
    out = os.path.join(TMP, f"c{k:02d}.mov")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{c['src_in']:.3f}", "-t", f"{dur:.3f}",
         "-i", _orig(c["take"]), "-frames:v", str(nfr), "-map", "0:v:0", "-map", "0:a:0",
         "-vf", vf, "-af", af, "-c:v", "libx264", "-crf", "14", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ac", "1", out])
    return out


with ThreadPoolExecutor(2) as ex:
    outs = list(ex.map(clip_job, enumerate(edl["clips"])))

lst = os.path.join(TMP, "list.txt")
open(lst, "w").write("".join(f"file '{o}'\n" for o in outs))
raw = os.path.join(ROOT, "assets", "cut_raw.mov")
run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", raw])

rnn = f"arnndn=m='{RNN}':mix=0.85," if os.path.exists(RNN) else ""
if not rnn: print("AVISO: modelo RNNoise não encontrado; voz tratada só com redução espectral.")
# zumbido medido no escritório (nov/2026): ~57 Hz e 113 Hz (+ 170) e apito ~3,87 kHz. A voz final sai do limpar_voz.py
voice = ("highpass=f=90,lowpass=f=14000,"
         "bandreject=f=57:width_type=h:w=8,bandreject=f=113:width_type=h:w=8,bandreject=f=170:width_type=h:w=10,"
         "bandreject=f=3870:width_type=h:w=60,"
         f"{rnn}afftdn=nf=-42,"
         "equalizer=f=200:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1.2:g=3,"
         "deesser=i=0.3,acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=3,"
         "loudnorm=I=-16:TP=-1.5:LRA=7")
run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-vn", "-af", voice, "-ar", "48000",
     "-c:a", "pcm_s16le", os.path.join(ROOT, "assets", "voice.wav")])
run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-i", os.path.join(ROOT, "assets", "voice.wav"),
     "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
     os.path.join(ROOT, "assets", "cut.mp4")])
print("ok", os.path.join(ROOT, "assets", "cut.mp4"))
