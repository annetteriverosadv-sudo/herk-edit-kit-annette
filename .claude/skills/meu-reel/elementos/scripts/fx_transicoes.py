#!/usr/bin/env python3
"""Passo 4b — transições no próprio vídeo cortado (pedido de 11/11/2026: film burn só uma vez).

Lê assets/plano.json ("transicao" de cada bloco) e assets/edl.json; grava assets/cut_fx.mp4.
- "blur": desfoque que cresce até o corte e se desfaz logo depois (~0,27 s no total).
- "whip": borrão de movimento horizontal curto (5 quadros) no corte; o deslocamento lateral vem do gen_comp.py.
- "seco" e "burn": nada aqui (o film burn é uma camada da composição).
O áudio é copiado sem mudança.
"""
import json, os, subprocess, sys
from plano import ROOT, caminho, carregar

PLANO = carregar()
EDL = json.load(open(caminho("assets", "edl.json")))
TRANS = {b["nome"]: b.get("transicao", "seco") for b in PLANO["blocos"]}
F = 1 / 30
starts, seen = [], set()
for c in EDL["clips"]:
    if c["block"] not in seen:
        seen.add(c["block"]); starts.append((c["out_in"], TRANS.get(c["block"], "seco")))
starts = starts[1:]

filt = []
for tc, tr in starts:
    if tr == "blur":
        steps = [(-3, 3), (-2, 6), (-1, 10), (0, 12), (1, 8), (2, 5), (3, 3), (4, 1.5)]
        for k, sg in steps:
            a = tc + k * F
            filt.append(f"gblur=sigma={sg}:steps=2:enable='between(t,{a - 0.004:.3f},{a + F - 0.006:.3f})'")
    elif tr == "whip":
        steps = [(-2, 18), (-1, 45), (0, 60), (1, 35), (2, 14)]
        for k, r in steps:
            a = tc + k * F
            filt.append(f"dblur=angle=0:radius={r}:enable='between(t,{a - 0.004:.3f},{a + F - 0.006:.3f})'")
# correção leve de luz e cor (pedido de 11/11/2026): contraste, pele um pouco mais quente, sem filtro de estilo
# 12/11/2026 "ela tá muito amarela": tira o amarelado da pele (R−B do rosto 60 → 47) sem acinzentar
filt.insert(0, "colorbalance=rs=-0.02:bs=0.03:rm=-0.04:gm=-0.005:bm=0.05:rh=-0.02:bh=0.03,eq=saturation=0.92")
src, out = caminho("assets", "cut.mp4"), caminho("assets", "cut_fx.mp4")
r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", src, "-vf", ",".join(filt), "-c:v", "libx264",
                    "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "copy", "-movflags", "+faststart", out],
                   capture_output=True, text=True)
if r.returncode: sys.exit(r.stderr[-1500:])
print("ok", out, [(round(tc, 2), tr) for tc, tr in starts])
