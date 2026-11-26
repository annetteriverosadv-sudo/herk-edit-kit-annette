#!/usr/bin/env python3
"""Junta os pedaços de voz numa locução única: source/vo/vo.wav + transcripts/vo.json.

26/11/2026 (escolha da Dra. Annette): 1ª dica com o SOM DOS PRÓPRIOS VÍDEOS (IMG_3868 até "contratos" + IMG_3867
"fora da loja física… não vale") — o áudio separado QD_6 era de outra tomada e a boca não batia.
2ª e 3ª dicas com os áudios separados QD_6_2 e QD_6_3 (gravados junto com IMG_3871 / IMG_3872).

Cada pedaço: limpo com o perfil do PRÓPRIO chiado; depois os pedaços são igualados em timbre e volume
("os áudios estão diferentes, coloque todos no mesmo volume e deixe igual"). Imprime o "deslocamento"
(tempo na locução − tempo no vídeo) de cada pedaço para o plano.
"""
import json
import numpy as np, soundfile as sf, scipy.signal as ss
import noisereduce as nr
from plano import caminho

SR, GAP, REDUCAO = 48000, 0.6, 0.92
# arquivo (source/vo/<arq>_hp.wav), de, ate, transcrição, deslocamento áudio->vídeo, trechos sem fala (perfil do chiado)
PEDACOS = [
    ("IMG_3868_cam", 6.50, 24.30, "IMG_3868", 0.0, [(0.3, 2.7), (3.0, 5.2), (5.9, 6.5), (24.4, 25.3)]),  # 5,5 s = "Vai" de quem grava
    ("IMG_3867_cam", 27.45, 31.35, "IMG_3867", 0.0, [(0.3, 0.9), (1.1, 2.6), (4.0, 5.3), (31.4, 32.1)]),
    ("QD_6_2", 5.35, 19.35, "QD_6_2.p", 2.655, [(0.2, 3.4), (19.6, 21.5)]),
    ("QD_6_3", 5.10, 28.10, "QD_6_3.p", 2.932, [(1.0, 3.5), (4.0, 5.0), (28.3, 29.4)]),
]
CORR = {
    "IMG_3868": {"para": "pra", "contratos.": "contratos"},
    "IMG_3867": {"fícica.": "física.", "fícicas,": "físicas,"},
    "QD_6_2": {}, "QD_6_3": {"durávels,": "duráveis,", "eletrodoméstico.": "eletrodomésticos.", "resolvei": "resolver",
                             "abaitemento": "abatimento", "preços.": "preço."},
}
DIVIDIR = {"QD_6_2": {"além": ["A", "lei"]}}
# 26/11: "no lugar de comprados tá contratos… é apenas produtos comprados" (Whisper ouvia "feitos e contratos")
# 26/11: "faz o corte nessa parte que ela fala feitos e deixa apenas comprados" (começo de "fei…" + pausa)
REMOVER = {"IMG_3868": [(23.18, 23.57)]}
TROCA = {"IMG_3868": (23.30, 24.30, [("comprados", 23.585, 24.16)])}
# início da fala dela no IMG_3868 (o Whisper do arquivo inteiro juntou o "Vai" de quem grava com o dela)
INICIO = {"IMG_3868": (8.19, [("Vai", 6.76, 6.96), ("comprar", 6.96, 7.14), ("na", 7.14, 7.32), ("Black", 7.32, 7.72), ("Friday?", 7.76, 8.20)])}
FIX_T = {("QD_6_2", "Segundo,"): (5.45, 6.10), ("IMG_3868", "produtos"): (22.82, 23.16)}  # "s" de produtos termina em 23,14 s
SEQ = {("QD_6_3", "de", "preços."): "do"}


def limpar(x, ruido):
    amostra = np.concatenate([x[int(a * SR):int(b * SR)] for a, b in ruido])
    return nr.reduce_noise(y=x, sr=SR, y_noise=amostra, stationary=True, prop_decrease=REDUCAO,
                           n_fft=2048, freq_mask_smooth_hz=250, time_mask_smooth_ms=50)


def ativos(x, hop=SR // 50):
    n = len(x) // hop; fr = x[:n * hop].reshape(n, hop); e = (fr ** 2).mean(1)
    return fr[e > np.percentile(e, 45)].ravel()


def ltas(x):
    f, P = ss.welch(ativos(x), SR, nperseg=4096); return f, 10 * np.log10(P + 1e-15)


partes, words, t = [], [], 0.0
fd = int(0.01 * SR)
for k, (arq, a, b, tr, desl, ruido) in enumerate(PEDACOS):
    nome = tr.split(".")[0]
    x, sr = sf.read(caminho("source", "vo", f"{arq}_hp.wav"), dtype="float64"); assert sr == SR
    x = limpar(x, ruido)
    # janelas que ficam (tirando os trechos de REMOVER), emendadas com cruzamento de 10 ms
    jan, ini = [], a
    for r0, r1 in REMOVER.get(arq.replace("_cam", ""), []):
        jan.append((ini, r0)); ini = r1
    jan.append((ini, b))
    seg = None
    for j0, j1 in jan:
        q = x[int(j0 * SR):int(j1 * SR)].copy()
        if seg is None: seg = q
        else:
            cf = np.linspace(0, 1, fd); seg[-fd:] = seg[-fd:] * (1 - cf) + q[:fd] * cf; seg = np.concatenate([seg, q[fd:]])
    seg[:fd] *= np.linspace(0, 1, fd); seg[-fd:] *= np.linspace(1, 0, fd)
    if k: partes.append(np.zeros(int(GAP * SR))); t += GAP
    shift = t - a
    ws = json.load(open(caminho("transcripts", f"{tr}.json")))["words"]
    if nome in INICIO:
        lim, novas = INICIO[nome]
        ws = [dict(text=a_, start=s_, end=e_) for a_, s_, e_ in novas] + [w for w in ws if w["start"] >= lim]
    if nome in TROCA:
        t0, t1, novas = TROCA[nome]
        ws = sorted([w for w in ws if not (t0 <= w["start"] < t1)] + [dict(text=a_, start=s_, end=e_) for a_, s_, e_ in novas],
                    key=lambda w: w["start"])
    out = []
    for j, w in enumerate(ws):
        if (nome, w["text"]) in FIX_T:
            w = dict(w, start=FIX_T[(nome, w["text"])][0], end=FIX_T[(nome, w["text"])][1])
        if not (a <= w["start"] < b): continue
        if any(r0 <= w["start"] < r1 for r0, r1 in REMOVER.get(arq.replace("_cam", ""), [])): continue
        corte = sum(r1 - r0 - fd / SR for r0, r1 in REMOVER.get(arq.replace("_cam", ""), []) if w["start"] >= r1)
        txt = CORR.get(nome, {}).get(w["text"], w["text"])
        if j + 1 < len(ws) and (nome, w["text"], ws[j + 1]["text"]) in SEQ:
            txt = SEQ[(nome, w["text"], ws[j + 1]["text"])]
        if w["text"] in DIVIDIR.get(nome, {}):
            pp = DIVIDIR[nome][w["text"]]; d = (w["end"] - w["start"]) / len(pp)
            out += [dict(text=q, start=round(w["start"] + i * d + shift - corte, 3), end=round(w["start"] + (i + 1) * d + shift - corte, 3), type="word")
                    for i, q in enumerate(pp)]
            continue
        out.append(dict(text=txt, start=round(w["start"] + shift - corte, 3), end=round(w["end"] + shift - corte, 3), type="word"))
    words += out
    partes.append(seg)
    tot = 0.0
    for j0, j1 in jan:
        print(f"{arq}: {j0:.2f}-{j1:.2f} -> locução {t + j0 - a - tot:.2f} | deslocamento p/ vídeo: {shift - tot + desl:.3f}")
        tot += 0  # (o deslocamento de cada janela já desconta os cortes anteriores)
        if (j0, j1) != jan[-1]:
            tot_next = jan[jan.index((j0, j1)) + 1][0] - j1 - fd / SR
            tot += tot_next
    t += len(seg) / SR

idx = [i for i, q in enumerate(partes) if np.any(q)]
curvas = [ltas(partes[i]) for i in idx]
f = curvas[0][0]
alvo = np.mean([c[1] for c in curvas], axis=0)
bandas = 1000 * 2 ** (np.arange(-17, 13) / 3)
for i, (_, c) in zip(idx, curvas):
    d = alvo - c
    g = np.array([np.mean(d[m]) if np.any(m := (f >= bb / 2 ** (1 / 6)) & (f < bb * 2 ** (1 / 6))) else 0 for bb in bandas])
    g = np.clip(g, -6, 6); g[bandas < 90] = np.minimum(g[bandas < 90], 0)
    ff = np.r_[0, bandas, SR / 2] / (SR / 2); gg = 10 ** (np.r_[g[0], g, g[-1]] / 20)
    partes[i] = ss.fftconvolve(partes[i], ss.firwin2(2047, np.clip(ff, 0, 1), gg), mode="same")
ref_rms = np.sqrt(np.mean(np.concatenate([ativos(partes[i]) for i in idx]) ** 2))
for i in idx:
    partes[i] *= ref_rms / np.sqrt(np.mean(ativos(partes[i]) ** 2))
    print(f"pedaço {i // 2 + 1}: fala {20 * np.log10(np.sqrt(np.mean(ativos(partes[i]) ** 2))):.1f} dBFS")
vo = np.concatenate(partes)
vo *= 0.5 / max(1e-9, np.max(np.abs(vo)))
sf.write(caminho("source", "vo", "vo.wav"), vo, SR, subtype="PCM_16")

PONT = [("mudou,", "mudou?"), ("resolver,", "resolver")]
for w in words:
    for de, para in PONT:
        if w["text"] == de: w["text"] = para
json.dump(dict(words=words, language="pt", text=" ".join(w["text"] for w in words)),
          open(caminho("transcripts", "vo.json"), "w"), indent=1, ensure_ascii=False)
print(f"vo.wav {len(vo) / SR:.2f}s, {len(words)} palavras")
print(" ".join(w["text"] for w in words))
