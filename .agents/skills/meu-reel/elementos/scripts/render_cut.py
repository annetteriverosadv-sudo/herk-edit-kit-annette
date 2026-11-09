#!/usr/bin/env python3
"""Passo 4 — renderiza o corte da fala (vídeo + voz limpa) a partir dos ORIGINAIS 4K, usando assets/edl.json.

Each clip: frame-accurate seek, crop to the uniform framing, scale to 1080x1920, 30 fps,
12 ms audio micro-fades. Clips are concatenated, then the voice chain is applied.
Outputs assets/cut.mp4 (video, silent-safe) and assets/voice.wav (cleaned voice, 48 kHz).
"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

from plano import ROOT, caminho
ORIG = caminho("source", "orig")
TMP = os.path.join(ROOT, "assets", "clips")
# Limpeza de voz RNNoise: $RNNOISE_MODEL ou ~/tools/models/sh.rnnn
# (github.com/GregorR/rnnoise-models, somnolent-hogwash-2018-09-01/sh.rnnn). Sem ele, só a redução espectral.
RNN = os.environ.get("RNNOISE_MODEL") or os.path.expanduser("~/tools/models/sh.rnnn")
os.makedirs(TMP, exist_ok=True)
edl = json.load(open(os.path.join(ROOT, "assets", "edl.json")))
COR = json.load(open(os.path.join(ROOT, "assets", "plano.json"))).get("cor", {})



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
    g = COR.get(c["take"], 1.0)  # correção de exposição/balanço de branco por gravação (sem filtro de estilo)
    vf = (f"crop={w}:{h}:{x}:{y},scale=1080:1920:flags=lanczos,"
          f"colorchannelmixer=rr={0.98 * g:.3f}:gg={g:.3f}:bb={1.035 * g:.3f},"
          "eq=contrast=1.03:saturation=1.02,unsharp=5:5:0.35:5:5:0,fps=30,setsar=1,"
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

rnn = f"arnndn=m='{RNN}':mix=1," if os.path.exists(RNN) else ""
if not rnn: print("AVISO: modelo RNNoise não encontrado; voz tratada só com redução espectral.")
# Correção 2026-11-09 ("parece que está dentro de um banheiro"): tira o zumbido de motor/ar-condicionado
# (~57/112 Hz e harmônicos), RNNoise cheio, redução espectral, expansor suave que encurta o eco entre
# as palavras, corte da caixa (300 Hz), presença (3,2 kHz) e compressão para a voz ficar na frente.
voice = ("highpass=f=90:poles=2,equalizer=f=57:t=h:w=5:g=-30,equalizer=f=112.5:t=h:w=6:g=-30,"
         "equalizer=f=169:t=h:w=6:g=-20,equalizer=f=225:t=h:w=6:g=-15,"
         f"{rnn}afftdn=nr=12:nf=-50:tn=1,loudnorm=I=-20:TP=-3:LRA=11:linear=true,"
         "agate=threshold=0.025:ratio=2.5:range=0.18:attack=4:release=80:knee=4,"
         "equalizer=f=300:t=q:w=1.2:g=-4,equalizer=f=600:t=q:w=1.5:g=-1.5,"
         "equalizer=f=3200:t=q:w=1.2:g=3.5,equalizer=f=8500:t=q:w=1:g=1.5,deesser=i=0.35,"
         "acompressor=threshold=-24dB:ratio=3.5:attack=6:release=110:makeup=3,"
         "loudnorm=I=-16:TP=-1.5:LRA=6")
run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-vn", "-af", voice, "-ar", "48000",
     "-c:a", "pcm_s16le", os.path.join(ROOT, "assets", "voice.wav")])
run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-i", os.path.join(ROOT, "assets", "voice.wav"),
     "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
     os.path.join(ROOT, "assets", "cut.mp4")])
print("ok", os.path.join(ROOT, "assets", "cut.mp4"))
