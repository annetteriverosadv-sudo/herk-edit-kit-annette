#!/usr/bin/env python3
"""Gera index.html no padrão de legenda do reel de referência do escritório (Reel-beneficios-contribuicao-v4).

Pedido de 26/11/2026: "reproduza o mesmo padrão de legendas do vídeo de referência (fonte, tamanho, cores,
posição, alinhamento, destaques e estilo); não utilize um estilo de legenda diferente por preferência própria".

Medido na referência (1080x1920):
- Legenda: a FRASE inteira aparece de uma vez (sem caixa pulando de palavra em palavra), Montserrat Bold ~54 px,
  branca, sombra suave, centralizada, linha a ~66% da altura (centro ≈ 1272 px). Troca por corte seco.
- Destaque: só a expressão-chave da frase ganha caixa bordô (cantos levemente arredondados), texto branco.
- Título (palavra-chave): linha pequena (Montserrat 700, ~44 px) com filete bordô curto embaixo + linha grande
  (Montserrat 800, ~72 px) com a palavra-chave em caixa bordô. A linha pequena entra primeiro; a grande entra
  com desfoque. Substitui a legenda naquele trecho.
- Lista: itens empilhados e centralizados, Montserrat 800 ~64 px, bolinha bordô antes; cada item entra
  (desfoque → nítido) na palavra falada.
Plano (assets/plano.json): "titulos" [{de, ate, pequeno, grande, caixa, grande_em}], "listas" [{de, ate, itens:[[texto, palavra]]}],
"destaques" [[de, ate]]. Tempos sempre da fala já cortada (assets/transcript.json).
"""
import json, os, html
from plano import ROOT, caminho, carregar, palavra

PLANO = carregar()
T = json.load(open(caminho("assets", "transcript.json")))
EDL = json.load(open(caminho("assets", "edl.json")))
W = T["words"]
VID = EDL["duration"]
DUR = VID  # sem cartão final (correção 2026-11-04)
VIDEO = "cut_final.mp4" if PLANO.get("desfoques") and os.path.exists(caminho("assets", "cut_final.mp4")) else "cut.mp4"  # desfocar.py

BORDO = PLANO.get("cor_destaque", "#8E1C24")
# a referência usa sombra suave sobre blazer escuro; com roupa clara a sombra fica mais densa (sem contorno)
SOMBRA = PLANO.get("sombra_legenda", "0 2px 4px rgba(0,0,0,.45), 0 0 14px rgba(0,0,0,.30)")
CAP_TOP = 1236          # topo da linha de legenda (centro ≈ 1272 px = 66%)
TIT_TOP = 1030          # topo da linha pequena do título (linha grande ≈ 1140–1230 px)
LIS_TOP = 1010


def p(ref):
    return palavra(W, ref)


def t(i):
    return W[i]["start"]


def fim_de(i):
    return round(t(i + 1) - 0.05, 3) if i + 1 < len(W) else VID


def esc(s):
    return html.escape(s, quote=True)


TITULOS = [dict(x, a=p(x["de"]), b=p(x["ate"])) for x in PLANO.get("titulos", [])]
LISTAS = [dict(x, a=p(x["de"]), b=p(x["ate"])) for x in PLANO.get("listas", [])]
RANGES = [(x["a"], x["b"]) for x in TITULOS] + [(x["a"], x["b"]) for x in LISTAS]
covered = set()
for a, b in RANGES:
    covered.update(range(a, b + 1))

# ---- grupos de legenda: frase curta (até 4 palavras / ~24 letras), quebra em pontuação e pausa ----
DEST_RANGES = {p(a_): p(b_) for a_, b_ in PLANO.get("destaques", [])}
DEST = {k for a_, b_ in DEST_RANGES.items() for k in range(a_, b_ + 1)}
JCONT = {k for a_, b_ in DEST_RANGES.items() for k in range(a_ + 1, b_ + 1)}
MAXW, MAXC = 4, 27
groups, cur = [], []
for i, w in enumerate(W):
    if i in covered:
        if cur: groups.append(cur); cur = []
        continue
    if cur and i in DEST_RANGES and (len(cur) + DEST_RANGES[i] - i + 1 > MAXW + 1
            or sum(len(W[j]["text"]) + 1 for j in cur + list(range(i, DEST_RANGES[i] + 1))) > MAXC + 1):
        groups.append(cur); cur = []
    if cur and i not in JCONT and (w["start"] - W[cur[-1]]["end"] > 0.35 or len(cur) >= MAXW
                                   or sum(len(W[j]["text"]) + 1 for j in cur) + len(w["text"]) > MAXC):
        groups.append(cur); cur = []
    cur.append(i)
    if w["text"][-1:] in ".?!," and i not in DEST_RANGES and (i + 1) not in JCONT:
        groups.append(cur); cur = []
if cur: groups.append(cur)
# palavra solta: junta com a vizinha se couber
merged = []
for g in groups:
    if merged and len(g) == 1 and g[0] - merged[-1][-1] == 1 and len(merged[-1]) < MAXW \
            and W[merged[-1][-1]]["text"][-1:] not in ".?!" \
            and sum(len(W[j]["text"]) + 1 for j in merged[-1] + g) <= MAXC + 2:
        merged[-1] = merged[-1] + g
    else:
        merged.append(g)
groups = merged
k = 0
while k < len(groups) - 1:
    g, nx = groups[k], groups[k + 1]
    if len(g) == 1 and W[g[0]]["text"][-1:] not in ".?!," and nx[0] == g[0] + 1 \
            and len(nx) < MAXW and sum(len(W[j]["text"]) + 1 for j in g + nx) <= MAXC + 2:
        groups[k] = g + nx; del groups[k + 1]
        continue
    k += 1

gtimes = []
for k, g in enumerate(groups):
    st = max(0.0, t(g[0]) - 0.05)
    nxt = t(groups[k + 1][0]) - 0.05 if k + 1 < len(groups) else VID
    nxt_graphic = min([t(a) - 0.06 for a, b in RANGES if a > g[-1]] or [VID])
    en = min(nxt, nxt_graphic, W[g[-1]]["end"] + 0.5)
    gtimes.append((round(st, 3), round(max(en, st + 0.4), 3)))
for k in range(len(gtimes) - 1):
    if gtimes[k][1] > gtimes[k + 1][0]:
        gtimes[k] = (gtimes[k][0], gtimes[k + 1][0])


def frase_html(g):
    """Texto da frase com a expressão de destaque (se houver) dentro de uma caixa bordô única."""
    out, k = [], 0
    while k < len(g):
        i = g[k]
        if i in DEST:
            run = [j for j in g[k:] if j in DEST]
            n = 0
            while n < len(run) and g[k + n] == run[n]: n += 1
            out.append(f'<span class="bx">{esc(" ".join(W[j]["text"] for j in g[k:k + n]))}</span>')
            k += n
        else:
            out.append(esc(W[i]["text"])); k += 1
    return " ".join(out)


cap_html, js = [], ["const tl=gsap.timeline({paused:true});"]
for k, (g, (st, en)) in enumerate(zip(groups, gtimes)):
    cap_html.append(f'<div class="cg" id="cg{k}">{frase_html(g)}</div>')
    js.append(f"tl.set('#cg{k}',{{opacity:1,visibility:'visible'}},{st});")
    js.append(f"tl.set('#cg{k}',{{opacity:0,visibility:'hidden'}},{en});")


def com_caixa(texto, caixa):
    if not caixa or caixa not in texto:
        return esc(texto)
    a, b = texto.split(caixa, 1)
    return f'{esc(a)}<span class="bx">{esc(caixa)}</span>{esc(b)}'


tit_html = ""
for n, x in enumerate(TITULOS):
    st = round(t(x["a"]) - 0.05, 3); en = fim_de(x["b"])
    tit_html += (f'<div id="t{n}" class="tit clip" data-start="{st}" data-duration="{round(en - st, 3)}" data-track-index="{6 + n}"><div id="t{n}w">'
                 f'<div class="small" id="t{n}a">{esc(x["pequeno"])}</div><div class="rule" id="t{n}r"></div>'
                 f'<div class="big" id="t{n}b">{com_caixa(x["grande"], x.get("caixa"))}</div></div></div>')
    gb = t(p(x.get("grande_em", x["ate"]))) - 0.05
    js.append(f"tl.from('#t{n}a',{{opacity:0,y:10,duration:0.18,ease:'power2.out'}},{st});")
    js.append(f"tl.from('#t{n}r',{{scaleX:0,duration:0.22,ease:'power2.out'}},{st + 0.08:.3f});")
    js.append(f"tl.from('#t{n}b',{{opacity:0,scale:1.06,filter:'blur(12px)',duration:0.24,ease:'power2.out'}},{max(st, gb):.3f});")
    if en < VID:
        js.append(f"tl.to('#t{n}w',{{opacity:0,filter:'blur(6px)',duration:0.16,ease:'power1.in'}},{en - 0.16:.3f});")
        js.append(f"tl.set('#t{n}w',{{opacity:0}},{en:.3f});")

lis_html = ""
for n, x in enumerate(LISTAS):
    st = round(t(x["a"]) - 0.05, 3); en = fim_de(x["b"])
    its = "".join(f'<div class="li" id="l{n}i{m}"><span class="dot"></span>{com_caixa(txt, x.get("caixas", {}).get(txt))}</div>'
                  for m, (txt, _) in enumerate(x["itens"]))
    head = f'<div class="small" id="l{n}h">{esc(x["titulo"])}</div><div class="rule" id="l{n}r"></div>' if x.get("titulo") else ""
    lis_html += f'<div id="l{n}" class="lis clip" data-start="{st}" data-duration="{round(en - st, 3)}" data-track-index="{10 + n}"><div id="l{n}w">{head}{its}</div></div>'
    if x.get("titulo"):
        js.append(f"tl.from('#l{n}h',{{opacity:0,y:10,duration:0.18,ease:'power2.out'}},{st});")
        js.append(f"tl.from('#l{n}r',{{scaleX:0,duration:0.22,ease:'power2.out'}},{st + 0.08:.3f});")
    for m, (txt, ref) in enumerate(x["itens"]):
        ti = max(st, t(p(ref)) - 0.05)
        js.append(f"tl.from('#l{n}i{m}',{{opacity:0,y:14,filter:'blur(10px)',duration:0.22,ease:'power2.out'}},{ti:.3f});")
    if en < VID:
        js.append(f"tl.to('#l{n}w',{{opacity:0,filter:'blur(6px)',duration:0.16,ease:'power1.in'}},{en - 0.16:.3f});")
        js.append(f"tl.set('#l{n}w',{{opacity:0}},{en:.3f});")

burns = [c["out_in"] for c in EDL["clips"] if c.get("burn")]
ZOOMS = [(c["out_in"], c.get("zoom_ate", c["out_out"])) for c in EDL["clips"] if c.get("zoom")]
json.dump(dict(burns=burns), open(caminho("assets", "transitions.json"), "w"))
for n, bt in enumerate(burns):
    s0 = max(0, round(bt - 0.28, 3))
    js.append(f"tl.fromTo('#fb{n}',{{opacity:0}},{{opacity:0.7,duration:0.28,ease:'sine.in'}},{s0});")
    js.append(f"tl.fromTo('#fb{n}',{{opacity:0.7}},{{opacity:0,duration:0.34,ease:'sine.out',immediateRender:false}},{s0 + 0.29:.3f});")
    js.append(f"tl.fromTo('#fb{n} .bi',{{x:-140,scale:1.05}},{{x:90,scale:1.18,duration:0.62,ease:'none'}},{s0});")
for a_, b_ in ZOOMS:  # aproximação suave e gradual (pedido: "aproximações e afastamentos gradativos")
    d = min(1.6, max(0.6, b_ - a_ - 0.1))
    js.append(f"tl.fromTo('#vwrap',{{scale:1}},{{scale:1.07,duration:{d:.2f},ease:'sine.inOut',immediateRender:false}},{a_:.3f});")
    js.append(f"tl.set('#vwrap',{{scale:1}},{b_:.3f});")
js.append("window.__timelines=window.__timelines||{};window.__timelines['reel']=tl;")

css = f"""
@font-face{{font-family:'Montserrat';src:url(assets/fonts/montserrat-latin-700-normal.woff2) format('woff2');font-weight:700}}
@font-face{{font-family:'Montserrat';src:url(assets/fonts/montserrat-latin-800-normal.woff2) format('woff2');font-weight:800}}
*{{box-sizing:border-box}}
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#1A1A1A}}
#reel{{position:relative;width:1080px;height:1920px;overflow:hidden;background:#1A1A1A}}
#vwrap{{position:absolute;inset:0;transform-origin:540px 538px}}
#vwrap video{{width:1080px;height:1920px;object-fit:cover;display:block}}
.burn{{position:absolute;inset:0;z-index:20;opacity:0;pointer-events:none;overflow:hidden}}
.burn .bi{{position:absolute;inset:-10%;
  background:radial-gradient(ellipse 55% 48% at 10% 42%,rgba(255,196,128,.85),rgba(226,104,52,.45) 42%,rgba(160,40,36,0) 75%),
             radial-gradient(ellipse 38% 55% at 96% 72%,rgba(255,224,180,.55),rgba(198,60,40,.25) 50%,rgba(142,28,36,0) 80%)}}
.bx{{background:{BORDO};color:#fff;border-radius:8px;padding:2px 14px 6px;text-shadow:none;
  -webkit-box-decoration-break:clone;box-decoration-break:clone}}
#caps{{position:absolute;left:60px;right:60px;top:{CAP_TOP}px;height:200px;z-index:10}}
.cg{{position:absolute;left:0;right:0;top:0;text-align:center;opacity:0;visibility:hidden;
  font-family:'Montserrat';font-weight:700;font-size:54px;line-height:1.5;color:#fff;word-spacing:4px;
  text-shadow:{SOMBRA}}}
.tit,.lis{{position:absolute;left:50px;right:50px;text-align:center;z-index:12}}
.tit{{top:{TIT_TOP}px}} .lis{{top:{LIS_TOP}px}}
.small{{font-family:'Montserrat';font-weight:700;font-size:44px;line-height:1.2;color:#fff;text-shadow:{SOMBRA}}}
.rule{{width:62px;height:5px;border-radius:3px;background:{BORDO};margin:8px auto 16px;transform-origin:50% 50%}}
.big{{font-family:'Montserrat';font-weight:800;font-size:72px;line-height:1.35;color:#fff;text-shadow:{SOMBRA};word-spacing:2px}}
.li{{font-family:'Montserrat';font-weight:800;font-size:64px;line-height:1.38;color:#fff;text-shadow:{SOMBRA}}}
.li .dot{{display:inline-block;width:16px;height:16px;border-radius:50%;background:{BORDO};margin-right:16px;vertical-align:middle;
  position:relative;top:-6px;box-shadow:0 0 6px rgba(0,0,0,.35)}}
"""
body = f"""
<div id="reel" data-composition-id="reel" data-start="0" data-duration="{DUR}" data-width="1080" data-height="1920">
 <div id="vwrap"><video id="v" src="assets/{VIDEO}" muted playsinline data-start="0" data-duration="{VID}" data-track-index="0"></video></div>
 <audio id="voice" src="assets/mix.wav" data-start="0" data-duration="{VID}" data-track-index="1" data-volume="1"></audio>
 {''.join(f'<div id="fb{n}" class="burn clip" data-start="{max(0, round(bt - 0.28, 3))}" data-duration="0.62" data-track-index="3"><div class="bi"></div></div>' for n, bt in enumerate(burns))}
 <div id="caps" class="clip" data-start="0" data-duration="{VID}" data-track-index="5">{''.join(cap_html)}</div>
 {tit_html}
 {lis_html}
</div>
"""
doc = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>{esc(PLANO.get("titulo", "Reel"))}</title>
<script src="assets/gsap.min.js"></script>
<style>{css}</style></head><body>{body}
<script>
{chr(10).join(js)}
</script></body></html>
"""
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(doc)
print(f"index.html: {len(groups)} frases de legenda, {len(TITULOS)} títulos, {len(LISTAS)} listas, {DUR}s, film burn em {burns}")
for g, (st, en) in zip(groups, gtimes):
    print(f"  {st:6.2f}-{en:6.2f}  {' '.join(('[' + W[i]['text'] + ']') if i in DEST else W[i]['text'] for i in g)}")
for x in TITULOS:
    print(f"  TÍTULO {t(x['a']):6.2f}  {x['pequeno']} / {x['grande']}")
for x in LISTAS:
    print(f"  LISTA  {t(x['a']):6.2f}  " + " | ".join(i[0] for i in x["itens"]))
