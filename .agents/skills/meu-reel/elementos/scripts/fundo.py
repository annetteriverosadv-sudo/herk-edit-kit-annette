#!/usr/bin/env python3
"""Fundo desfocado e um pouco mais escuro, rosto em destaque (19/11: "melhore o enquadramento e a iluminação";
DESIGN: "fundo desfocado quando estiver poluído"). Recorte da pessoa com MODNet (retrato, licença Apache 2.0;
~/tools/models/modnet.onnx de huggingface.co/Xenova/modnet). Máscara suavizada no tempo dentro de cada trecho
(sem tremer a borda), zerada a cada corte. Lê assets/cut.mp4 (guarda assets/cut_sem_fundo.mp4) e regrava assets/cut.mp4.
Plano: "fundo": {"desfoque": 14, "escurece": 0.74, "dessatura": 0.85, "realce_pessoa": 1.06}"""
import json, os, subprocess, sys, numpy as np, cv2, onnxruntime as ort
from plano import caminho, carregar
P = carregar().get("fundo", {})
BL, ESC, DES, RL = P.get("desfoque", 14), P.get("escurece", 0.74), P.get("dessatura", 0.85), P.get("realce_pessoa", 1.06)
MOD = os.environ.get("MODNET_MODEL") or os.path.expanduser("~/tools/models/modnet.onnx")
S = ort.InferenceSession(MOD, providers=["CPUExecutionProvider"])
src, keep = caminho("assets", "cut.mp4"), caminho("assets", "cut_sem_fundo.mp4")
if not os.path.exists(keep): os.rename(src, keep)
E = json.load(open(caminho("assets", "edl.json")))["clips"]
cortes = {round(c["out_in"] * 30) for c in E}
LUT = np.array([255 * (i / 255) ** (1 / RL) for i in range(256)], np.float32)  # clareia meios-tons da pessoa


def alpha(fr, ref=512):
    h, w = fr.shape[:2]; s = ref / max(h, w)
    nh, nw = int(round(h * s / 32) * 32), int(round(w * s / 32) * 32)
    x = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB), (nw, nh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    m = S.run(None, {"input": ((x - 0.5) / 0.5).transpose(2, 0, 1)[None]})[0][0, 0]
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)


cap = cv2.VideoCapture(keep); W_, H_ = int(cap.get(3)), int(cap.get(4)); N = int(cap.get(7))
ff = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W_}x{H_}",
                       "-r", "30", "-i", "-", "-i", keep, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "15",
                       "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", src], stdin=subprocess.PIPE)
prev, i = None, 0
while True:
    ok, fr = cap.read()
    if not ok: break
    a = alpha(fr)
    if prev is not None and i not in cortes:
        a = 0.6 * a + 0.4 * prev                      # suaviza a borda no tempo (sem atravessar corte)
    prev = a
    a3 = np.clip(a, 0, 1)[..., None]
    bg = cv2.GaussianBlur(fr, (0, 0), BL).astype(np.float32)
    g = cv2.cvtColor(bg.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)[..., None]
    bg = (g + (bg - g) * DES) * ESC
    pessoa = LUT[fr]
    out = np.clip(pessoa * a3 + bg * (1 - a3), 0, 255).astype(np.uint8)
    ff.stdin.write(out.tobytes()); i += 1
    if i % 300 == 0: print(f"{i}/{N} quadros", flush=True)
ff.stdin.close(); ff.wait()
print("ok fundo:", src, i, "quadros")
