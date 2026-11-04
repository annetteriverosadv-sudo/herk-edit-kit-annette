#!/usr/bin/env python3
"""Passo 1 — prepara as gravações originais do projeto.

Para cada arquivo em source/orig/ (MOV/MP4 do celular, de preferência o original, não o do WhatsApp):
  - cria a cópia de trabalho source/work/<nome>.mov (1080x1920, 30 fps, áudio PCM) para transcrever e medir;
  - mede o rosto (posição e tamanho) e grava assets/faces.json, usado para igualar o enquadramento.
Detector de rosto: arquivo Haar do OpenCV em $HAAR_XML ou ~/tools/models/haar.xml
(baixe de github.com/opencv/opencv, data/haarcascades/haarcascade_frontalface_default.xml).
"""
import glob, json, os, subprocess, sys
import numpy as np
from plano import caminho

HAAR = os.environ.get("HAAR_XML") or os.path.expanduser("~/tools/models/haar.xml")
orig = sorted(glob.glob(caminho("source", "orig", "*.MOV")) + glob.glob(caminho("source", "orig", "*.mov"))
              + glob.glob(caminho("source", "orig", "*.mp4")))
if not orig:
    sys.exit("Coloque as gravações em source/orig/ primeiro.")
os.makedirs(caminho("source", "work"), exist_ok=True)
os.makedirs(caminho("assets"), exist_ok=True)

for f in orig:
    nome = os.path.splitext(os.path.basename(f))[0]
    out = caminho("source", "work", nome + ".mov")
    if not os.path.exists(out):
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", f, "-map", "0:v:0", "-map", "0:a:0",
                            "-vf", "fps=30,scale=1080:1920:flags=lanczos", "-c:v", "libx264", "-crf", "14",
                            "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ar", "48000", out],
                           capture_output=True, text=True)
        if r.returncode: sys.exit(r.stderr[-1500:])
    print("cópia de trabalho:", os.path.basename(out))

import cv2
casc = cv2.CascadeClassifier(HAAR)
if casc.empty():
    sys.exit(f"Detector de rosto não encontrado em {HAAR}")
faces = {}
for f in sorted(glob.glob(caminho("source", "work", "*.mov"))):
    cap = cv2.VideoCapture(f); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W, H = int(cap.get(3)), int(cap.get(4)); boxes = []
    for i in np.linspace(10, max(10, n - 10), 24).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i)); ok, fr = cap.read()
        if not ok: continue
        fs = casc.detectMultiScale(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), 1.1, 6, minSize=(60, 60))
        if len(fs): boxes.append(max(fs, key=lambda b: b[2] * b[3]))
    nome = os.path.splitext(os.path.basename(f))[0]
    if not boxes:
        print("AVISO: rosto não encontrado em", nome, "- usando centro do quadro"); faces[nome] = dict(cx=0.5, eye=0.36, fh=0.15)
        continue
    x, y, w, h = np.median(np.array(boxes), axis=0)
    faces[nome] = dict(cx=round((x + w / 2) / W, 4), eye=round((y + 0.42 * h) / H, 4), fh=round(h / H, 4))
    print(nome, faces[nome])
json.dump(faces, open(caminho("assets", "faces.json"), "w"), indent=1)
