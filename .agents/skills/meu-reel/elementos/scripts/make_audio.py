#!/usr/bin/env python3
"""Passo 6 — trilha + efeitos + mixagem final, com os sons da pasta elementos/audio (sons.py).

- Trilha de fundo: DESLIGADA por padrão (correção de 04/11/2026: "ficou com ruído e estragou o áudio").
  Só entra se o plano tiver "trilha": true — aí 18-22 dB abaixo da voz e abaixando quando ela fala.
- Transição (troca de assunto, junto com o film burn): sopro suave + tom quente, bem baixos.
- Toque abafado quando entra a palavra grande de cada título; clique seco em cada item de lista.
- Master: -14 LUFS medido em ESTÉREO (a mixagem é salva em estéreo; medir em mono dá +3 dB no vídeo final).
Copie elementos/audio/sons.py para a mesma pasta deste script.
"""
import json, os, re, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plano import caminho, carregar, palavra
from sons import SR, Sons, write, NIVEL_SOPRO, NIVEL_TOM, NIVEL_TOQUE, NIVEL_CLIQUE, FREQ_CLIQUES

PLANO = carregar()
EDL = json.load(open(caminho("assets", "edl.json")))
T = json.load(open(caminho("assets", "transcript.json")))["words"]
DUR = EDL["duration"]
N = int(round(DUR * SR))
s = Sons()

music = s.trilha(DUR)
sfx = np.zeros(N + SR)
sopro, tom = s.sopro(), s.tom()
for bt in json.load(open(caminho("assets", "transitions.json")))["burns"]:
    s.add(sfx, NIVEL_SOPRO * sopro, max(0, bt - 0.24))   # sopro cresce até o corte
    s.add(sfx, NIVEL_TOM * tom, max(0, bt - 0.04))       # tom abre no corte
toque = s.toque()
for x in PLANO.get("titulos", []):
    s.add(sfx, NIVEL_TOQUE * toque, T[palavra(T, x.get("grande_em", x["ate"]))]["start"] - 0.05)
itens = [palavra(T, it[1]) for lst in PLANO.get("listas", []) for it in lst["itens"]]
cliques = [s.clique(FREQ_CLIQUES[k % len(FREQ_CLIQUES)]) for k in range(len(itens))]
for k, i in enumerate(itens):
    s.add(sfx, NIVEL_CLIQUE * cliques[k], T[i]["start"] - 0.04)
sfx = sfx[:N]

A = caminho("assets")
write(os.path.join(A, "music.wav"), 0.5 * music)
write(os.path.join(A, "sfx.wav"), sfx)

if PLANO.get("trilha", False):
    fc = ("[0:a]aresample=48000,asplit=2[v][vk];"
          "[1:a]volume=-13dB[m];"
          "[m][vk]sidechaincompress=threshold=0.02:ratio=4:attack=30:release=350:makeup=1[md];"
          "[2:a]volume=-6dB[s];"
          "[v][md][s]amix=inputs=3:duration=first:normalize=0[out]")
else:  # sem música de fundo: só voz + efeitos
    fc = ("[0:a]aresample=48000[v];[1:a]volume=-140dB[m];[2:a]volume=-4dB[s];"
          "[v][s]amix=inputs=2:duration=first:normalize=0[out];[m]anullsink")
r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", os.path.join(A, "voice.wav"),
                    "-i", os.path.join(A, "music.wav"), "-i", os.path.join(A, "sfx.wav"), "-filter_complex", fc,
                    "-map", "[out]", "-ar", "48000", "-c:a", "pcm_f32le", os.path.join(A, "mix_pre.wav")],
                   capture_output=True, text=True)
if r.returncode: sys.exit(r.stderr)


def lufs(path):
    o = subprocess.run(["ffmpeg", "-nostdin", "-i", path, "-ac", "2", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[0-9.]+) LUFS", o)[-1])


pre, out = os.path.join(A, "mix_pre.wav"), os.path.join(A, "mix.wav")
ALVO = float(PLANO.get("lufs", -12.0))  # 2026-11-09: voz mais alta (era -14)
g = ALVO - lufs(pre)
for _ in range(3):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", pre, "-af",
                        f"volume={g:.2f}dB,alimiter=limit=0.85:attack=1:release=60:level=false",
                        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", out], capture_output=True, text=True)
    if r.returncode: sys.exit(r.stderr)
    got = lufs(out)
    if abs(got - ALVO) <= 0.3: break
    g += ALVO - got
print(f"mixagem: {got} LUFS (ganho {g:.1f} dB), {DUR:.2f} s, trilha {'ligada' if PLANO.get('trilha') else 'desligada'}")
