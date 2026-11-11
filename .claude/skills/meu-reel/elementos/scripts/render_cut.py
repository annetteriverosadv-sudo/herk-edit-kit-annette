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


def _hdr(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return "b67" in o or "2084" in o


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
    # Gravação do iPhone em HDR (HLG): converte para SDR com tonemap (correção 11/11/2026: "que iluminação é essa?"
    # — sem isso a imagem fica lavada e acinzentada) e baixa um pouco o fundo claro com uma curva suave.
    hdr = _hdr(_orig(c["take"]))
    tm = ("zscale=tin=arib-std-b67:pin=bt2020:min=bt2020nc:t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
          "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,"
          "curves=master='0/0 0.25/0.24 0.5/0.52 0.8/0.80 1/0.92',eq=saturation=1.05,") if hdr else ""
    # (2ª correção 11/11/2026: "tá muito estourado de luz" — mobius deixava cortina e rosto claros demais; hable + curva
    #  mantém o preto do blazer firme, cortina neutra e pele natural)
    vf = (f"crop={w}:{h}:{x}:{y},scale=1080:1920:flags=lanczos,{tm}"
          f"colorchannelmixer=rr={g:.3f}:gg={g:.3f}:bb={g:.3f},"
          "unsharp=5:5:0.3:5:5:0,fps=30,setsar=1,"
          f"trim=end_frame={nfr},setpts=PTS-STARTPTS")
    af = (f"aresample=48000,apad,atrim=end={dur:.6f},asetpts=PTS-STARTPTS,"
          f"afade=t=in:d=0.012,afade=t=out:st={max(0, dur - 0.012):.3f}:d=0.012")
    out = os.path.join(TMP, f"c{k:02d}.mov")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{c['src_in']:.3f}", "-t", f"{dur:.3f}",
         "-i", _orig(c["take"]), "-frames:v", str(nfr), "-map", "0:v:0", "-map", "0:a:0",
         "-vf", vf, "-af", af, "-c:v", "libx264", "-crf", "14", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
         "-c:a", "pcm_s16le", "-ac", "1", out])
    return out


with ThreadPoolExecutor(2) as ex:
    outs = list(ex.map(clip_job, enumerate(edl["clips"])))

lst = os.path.join(TMP, "list.txt")
open(lst, "w").write("".join(f"file '{o}'\n" for o in outs))
raw = os.path.join(ROOT, "assets", "cut_raw.mov")
run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", raw])

rnn = f"arnndn=m='{RNN}':mix=1," if os.path.exists(RNN) else ""
if not rnn: print("AVISO: modelo RNNoise não encontrado; voz tratada só com redução espectral.")
# Correções 2026-11-09 ("banheiro", "como microfone perto", "voz mais alta"):
# 1) tira o zumbido de motor/ar-condicionado (~57/112 Hz e harmônicos);
# 2) dereverb.py: WPE + supressão do rabo de reverberação (precisa de: pip install nara_wpe soundfile);
# 3) RNNoise, expansor bem suave, "corpo" de microfone próximo (+3 dB em 170 Hz),
#    corte da caixa (380 Hz), presença (3 kHz) e compressão.
hum = ("highpass=f=90:poles=2,equalizer=f=57:t=h:w=5:g=-30,equalizer=f=112.5:t=h:w=6:g=-30,"
       "equalizer=f=169:t=h:w=6:g=-20,equalizer=f=225:t=h:w=6:g=-15")
# (sem afftdn depois do dereverb: ele "comia" o fim das palavras — ex. "jornada de trabalho")
voice = (f"{rnn}loudnorm=I=-20:TP=-3:LRA=11:linear=true,"
         "agate=threshold=0.012:ratio=1.8:range=0.3:attack=8:release=150:knee=6,"
         "lowshelf=f=170:g=3,equalizer=f=380:t=q:w=1.2:g=-3.5,"
         "equalizer=f=3000:t=q:w=1.2:g=3,equalizer=f=8500:t=q:w=1:g=1.5,deesser=i=0.35,"
         "acompressor=threshold=-24dB:ratio=3:attack=6:release=120:makeup=3,"
         "loudnorm=I=-16:TP=-1.5:LRA=6")
A = os.path.join(ROOT, "assets")
VOZ = json.load(open(os.path.join(ROOT, "assets", "plano.json"))).get("voz", "tratada")
if VOZ == "natural":
    # Correção 11/11/2026 ("que voz é essa, tá tudo estranho"): gravação de lapela limpa (ruído ~44 dB abaixo da fala).
    # Nada de dereverb/RNNoise/expansor: só tira o grave de manuseio, suaviza o "s", compressão leve e nivelamento.
    natural = ("highpass=f=75:poles=2,equalizer=f=250:t=q:w=1:g=-1.5,equalizer=f=3200:t=q:w=1.2:g=1.2,"
               "deesser=i=0.25,acompressor=threshold=-26dB:ratio=2.2:attack=12:release=180:knee=6:makeup=2,"
               "loudnorm=I=-16:TP=-2:LRA=7")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-vn", "-ac", "1", "-af", natural, "-ar", "48000",
         "-c:a", "pcm_s16le", os.path.join(A, "voice.wav")])
else:
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-vn", "-ac", "1", "-af", hum, "-ar", "48000",
         "-c:a", "pcm_s16le", os.path.join(A, "voice_hum.wav")])
    r_ = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "dereverb.py"),
                         os.path.join(A, "voice_hum.wav"), os.path.join(A, "voice_dry.wav"), "0.5", "0.6"],
                        capture_output=True, text=True)
    if r_.returncode: sys.exit(r_.stderr[-1500:])
    raw_voice = os.path.join(A, "voice_dry.wav")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw_voice, "-vn", "-af", voice, "-ar", "48000",
         "-c:a", "pcm_s16le", os.path.join(ROOT, "assets", "voice.wav")])

run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-i", os.path.join(ROOT, "assets", "voice.wav"),
     "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
     "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
     os.path.join(ROOT, "assets", "cut.mp4")])
print("ok", os.path.join(ROOT, "assets", "cut.mp4"))
