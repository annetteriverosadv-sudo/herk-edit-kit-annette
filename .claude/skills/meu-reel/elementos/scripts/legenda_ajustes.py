#!/usr/bin/env python3
"""Ajustes de legenda na transcrição final (assets/transcript.json), depois do edl.py:
junta palavras faladas em um só termo escrito ("mil e oitocentos reais" -> "R$ 1.800"),
mantendo o início da primeira e o fim da última. Config: plano["juntar_legenda"] = [[seq, texto]].
Guarda a original em assets/transcript_falado.json (rodar de novo parte sempre da falada)."""
import json, os, re, unicodedata
from plano import caminho, carregar
P = carregar()
orig = caminho("assets", "transcript_falado.json"); dst = caminho("assets", "transcript.json")
d = json.load(open(dst))
if os.path.exists(orig) and os.path.getmtime(orig) > os.path.getmtime(caminho("assets", "edl.json")):
    d = json.load(open(orig))
else:
    json.dump(d, open(orig, "w"), indent=1, ensure_ascii=False)
def n(s):
    s = unicodedata.normalize("NFD", s.lower()); s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", s)
W = d["words"]
for seq, texto in P.get("juntar_legenda", []):
    alvo = [n(x) for x in seq.split()]
    for i in range(len(W) - len(alvo) + 1):
        if [n(W[i + k]["text"]) for k in range(len(alvo))] == alvo:
            pont = re.findall(r"[.,!?;:]+$", W[i + len(alvo) - 1]["text"])
            novo = dict(W[i], text=texto + (pont[0] if pont else ""), end=W[i + len(alvo) - 1]["end"])
            W[i:i + len(alvo)] = [novo]
            print("legenda:", seq, "->", novo["text"])
            break
    else:
        print("AVISO: não achei", seq)
d["words"] = W; d["text"] = " ".join(w["text"] for w in W)
json.dump(d, open(dst, "w"), indent=1, ensure_ascii=False)
