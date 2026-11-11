#!/usr/bin/env python3
"""Passo 5 — gera index.html (composição HyperFrames) no estilo da Dra. Annette, a partir de assets/plano.json.

- Legenda palavra por palavra: Montserrat 600, 58 px, letras normais, sombra difusa, caixa bordô na palavra falada.
- Gancho: linhas do plano ("sans" = Montserrat 700; "serifa" = Playfair itálico), surgindo na palavra indicada.
- Títulos de palavra-chave: linha pequena + palavra grande em Playfair itálico (entra com desfoque e zoom).
- Listas: cartão bege com borda bordô; cada item entra na palavra falada, com bolinha bordô.
- Film burn singelo em cada troca de bloco do plano (troca de assunto). Sem selo de tema no topo, sem cartão final.
Tempos: sempre os da fala já cortada (assets/transcript.json). Grava também assets/transitions.json.
Fontes: copie elementos/fontes/*.woff2 para assets/fonts/ do projeto.
"""
import json, os, html
from plano import ROOT, caminho, carregar, palavra

PLANO = carregar()
T = json.load(open(caminho("assets", "transcript.json")))
EDL = json.load(open(caminho("assets", "edl.json")))
W = T["words"]
VID = EDL["duration"]
DUR = VID  # sem cartão final (correção 2026-11-04)

BORDO, VERM, PRETO, BEGE, CINZA = "#8E1C24", "#C62828", "#1A1A1A", "#EFE6D8", "#6B6B6B"
HALO = "0 0 2px rgba(0,0,0,.55), 0 2px 6px rgba(0,0,0,.55), 0 0 22px rgba(0,0,0,.45)"


def p(ref):
    return palavra(W, ref)


def t(i):
    return W[i]["start"]


def fim_de(i):  # fim de um elemento que termina na palavra i: começo da próxima palavra (ou fim do vídeo)
    return round(t(i + 1) - 0.05, 3) if i + 1 < len(W) else VID


# ---- trechos cobertos por gráficos (a legenda some ali) ----
G = PLANO.get("gancho")
HOOK = (0, p(G["ate"])) if G else None
TITULOS = [dict(x, a=p(x["de"]), b=p(x["ate"])) for x in PLANO.get("titulos", [])]
LISTAS = [dict(x, a=p(x["de"]), b=p(x["ate"])) for x in PLANO.get("listas", [])]
TELAS = [dict(x, a=p(x["de"]), b=p(x["ate"])) for x in PLANO.get("telas", [])]
RANGES = ([HOOK] if HOOK else []) + [(x["a"], x["b"]) for x in TITULOS] + [(x["a"], x["b"]) for x in LISTAS] \
    + [(x["a"], x["b"]) for x in TELAS]  # correção 11/11/2026: texto de tela substitui a legenda, nada empilhado
covered = set()
for a, b in RANGES:
    covered.update(range(a, b + 1))

# ---- caption groups: 2-4 words, break on punctuation / pauses / graphics ----
DEST = set()
for a_, b_ in PLANO.get("destaques", []):
    DEST.update(range(p(a_), p(b_) + 1))
DEST_RANGES = {p(a_): p(b_) for a_, b_ in PLANO.get("destaques", []) + PLANO.get("juntos", [])}  # juntos: não divide entre blocos, sem destaque
JCONT = {k for a_, b_ in DEST_RANGES.items() for k in range(a_ + 1, b_ + 1)}
INNER = {k for a_, b_ in DEST_RANGES.items() for k in range(a_, b_)}  # vírgula dentro de um grupo que não se divide  # continuação de um grupo que não se divide
groups, cur = [], []
for i, w in enumerate(W):
    if i in covered:
        if cur: groups.append(cur); cur = []
        continue
    if cur and i in DEST_RANGES and len(cur) + DEST_RANGES[i] - i + 1 > 4:  # palavra-chave não se divide
        groups.append(cur); cur = []
    if cur and i not in JCONT and (w["start"] - W[cur[-1]]["end"] > 0.35 or len(cur) >= 4
                or sum(len(W[j]["text"]) for j in cur) + len(w["text"]) > 24):
        groups.append(cur); cur = []
    cur.append(i)
    if w["text"][-1:] in ".?!," and i not in INNER:
        groups.append(cur); cur = []
if cur: groups.append(cur)
# merge single-word groups into a neighbour when it stays short
merged = []
for g in groups:
    if merged and len(g) == 1 and g[0] - merged[-1][-1] == 1 and len(merged[-1]) < 4 \
            and W[merged[-1][-1]]["text"][-1:] not in ".?!":
        merged[-1] = merged[-1] + g
    else:
        merged.append(g)
groups = merged
# a lone word that does not end a phrase joins the following group (max 4 words;
# an overflow word moves on to the group after that when it fits)
k = 0
while k < len(groups) - 1:
    g, nx = groups[k], groups[k + 1]
    if len(g) == 1 and len(W[g[0]]["text"]) <= 12 and W[g[0]]["text"][-1:] not in ".?!," and nx[0] == g[0] + 1:
        joined = g + nx
        groups[k] = joined[:4]
        rest = joined[4:]
        if rest:
            if k + 2 < len(groups) and groups[k + 2][0] == rest[-1] + 1 and len(rest) + len(groups[k + 2]) <= 4:
                groups[k + 1] = rest + groups[k + 2]; del groups[k + 2]
            else:
                groups[k + 1] = rest
        else:
            del groups[k + 1]
    k += 1

gtimes = []
for k, g in enumerate(groups):
    st = max(0.0, t(g[0]) - 0.05)
    nxt = t(groups[k + 1][0]) - 0.05 if k + 1 < len(groups) else VID
    nxt_graphic = min([t(a) - 0.06 for a, b in RANGES if a > g[-1]] or [VID])
    en = min(nxt, nxt_graphic, W[g[-1]]["end"] + 0.45)
    gtimes.append((round(st, 3), round(max(en, st + 0.4), 3)))
for k in range(len(gtimes) - 1):  # no overlap
    if gtimes[k][1] > gtimes[k + 1][0]:
        gtimes[k] = (gtimes[k][0], gtimes[k + 1][0])


def esc(s):
    return html.escape(s, quote=True)


cap_html, cap_js = [], []
for k, (g, (st, en)) in enumerate(zip(groups, gtimes)):
    spans = "".join(f'<span class="w" id="w{i}">{esc(W[i]["text"])}</span> ' for i in g)
    cap_html.append(f'<div class="cg" id="cg{k}">{spans.strip()}</div>')
    cap_js.append(f"tl.set('#cg{k}',{{opacity:1,visibility:'visible'}},{st});")
    for n, i in enumerate(g):
        if i in DEST:  # palavra-chave: caixa bordô durante o bloco inteiro
            cap_js.append(f"tl.set('#w{i}',{{backgroundColor:'{BORDO}'}},{st:.3f});")
            continue
        # (correção 11/11/2026: sem caixa pulando em toda palavra — só as importantes ganham destaque)
    cap_js.append(f"tl.set('#cg{k}',{{opacity:0,visibility:'hidden'}},{en});")

burns = [c["out_in"] for c in EDL["clips"] if c.get("burn")]
# transições por bloco (pedido de 11/11/2026: film burn só uma vez; desfoque, chicote e corte seco)
TRANS = {b["nome"]: b.get("transicao", "burn" if b.get("burn", True) else "seco") for b in PLANO["blocos"]}
BSTART, _seen = [], set()
for c in EDL["clips"]:
    if c["block"] not in _seen:
        _seen.add(c["block"]); BSTART.append((c["out_in"], TRANS.get(c["block"], "seco")))
BSTART = BSTART[1:]
WHIPS = [bt for bt, tr in BSTART if tr == "whip"]
BLURS = [bt for bt, tr in BSTART if tr == "blur"]
CLIP_ENDS = sorted(c["out_out"] for c in EDL["clips"])
def clip_end(tm):
    return next((e for e in CLIP_ENDS if e > tm + 1e-3), VID)
PUNCH = [(t(p(x["em"])) - 0.04, x.get("escala", 1.08)) for x in PLANO.get("punches", [])]
LENTOS = [(t(p(x["de"])) - 0.04, W[p(x["ate"])]["end"], x.get("escala", 1.05)) for x in PLANO.get("lentos", [])]
ZOOMS = [(c["out_in"], c.get("zoom_ate", c["out_out"])) for c in EDL["clips"] if c.get("zoom")]
json.dump(dict(burns=sorted(burns + WHIPS + BLURS), whips=WHIPS, blurs=BLURS), open(caminho("assets", "transitions.json"), "w"))


def items_html(prefix, items):
    return "".join(f'<div class="item" id="{prefix}{n}"><span class="tick"></span>{esc(txt)}</div>'
                   for n, (txt, _) in enumerate(items))


T_IDS = ",".join(f"#t{n + 1}" for n in range(max(1, len(TITULOS))))
T_SMALL = ",".join(f"#t{n + 1} .small" for n in range(max(1, len(TITULOS))))
T_BIG = ",".join(f"#t{n + 1} .big" for n in range(max(1, len(TITULOS))))
L_TOPS = " ".join(f"#l{n + 1}{{{{top:1010px}}}}" for n in range(len(LISTAS))).replace("{{", "{").replace("}}", "}")
css = f"""
@font-face{{font-family:'Playfair Display';src:url(assets/fonts/playfair-display-latin-800-italic.woff2) format('woff2');font-weight:800;font-style:italic}}
@font-face{{font-family:'Montserrat';src:url(assets/fonts/montserrat-latin-600-normal.woff2) format('woff2');font-weight:600}}
@font-face{{font-family:'Montserrat';src:url(assets/fonts/montserrat-latin-700-normal.woff2) format('woff2');font-weight:700}}
@font-face{{font-family:'Montserrat';src:url(assets/fonts/montserrat-latin-800-normal.woff2) format('woff2');font-weight:800}}
*{{box-sizing:border-box}}
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:{PRETO}}}
#reel{{position:relative;width:1080px;height:1920px;overflow:hidden;background:{PRETO}}}
#vwrap{{position:absolute;inset:0;transform-origin:540px 538px}}
#vwrap video{{width:1080px;height:1920px;object-fit:cover;display:block}}
/* film burn */
.burn{{position:absolute;inset:0;z-index:20;opacity:0;pointer-events:none;overflow:hidden}}
.burn .bi{{position:absolute;inset:-10%;
  background:radial-gradient(ellipse 55% 48% at 10% 42%,rgba(255,196,128,.85),rgba(226,104,52,.45) 42%,rgba(160,40,36,0) 75%),
             radial-gradient(ellipse 38% 55% at 96% 72%,rgba(255,224,180,.55),rgba(198,60,40,.25) 50%,rgba(142,28,36,0) 80%)}}
/* hook */
#hook{{position:absolute;left:70px;right:70px;top:790px;text-align:center;z-index:12}}
#hook .h1{{font-family:'Montserrat';font-weight:800;font-size:72px;line-height:1.15;color:#fff;
  text-shadow:{HALO}}}
#hook .h3{{font-family:'Montserrat';font-weight:700;font-size:66px;line-height:1.3;color:#fff;margin-top:6px;
  text-shadow:{HALO}}}
#hook .h2{{font-family:'Playfair Display';font-style:italic;font-weight:800;font-size:124px;line-height:1.0;
  color:#fff;margin-top:2px;text-shadow:{HALO}}}
/* lista digitada */
.typed{{position:absolute;left:80px;right:60px;top:1080px;z-index:12}}
.typed .ti{{font-family:'Montserrat';font-weight:800;font-size:60px;line-height:1.25;color:#fff;white-space:pre;
  border-left:10px solid {BORDO};padding:4px 0 4px 26px;margin-bottom:26px;text-shadow:{HALO}}}
.typed .ch,.typed .cur{{display:none}}
.typed .cur{{color:#fff;font-weight:600;margin-left:2px}}
/* light leak (só na palavra de impacto) */
.leak{{position:absolute;inset:0;z-index:11;opacity:0;pointer-events:none;overflow:hidden}}
.leak .li{{position:absolute;inset:-15%;
  background:radial-gradient(ellipse 50% 60% at 100% 35%,rgba(198,40,40,.85),rgba(198,40,40,.35) 40%,rgba(198,40,40,0) 70%),
             radial-gradient(ellipse 45% 45% at 85% 70%,rgba(255,178,92,.6),rgba(255,150,70,.2) 45%,rgba(255,150,70,0) 75%)}}
/* textos de tela do roteiro (correção 11/11/2026: harmonioso, sem caixas, substitui a legenda) */
.tela{{position:absolute;left:60px;right:60px;top:1060px;text-align:center;z-index:13}}
.tela .glow{{position:absolute;left:-60px;right:-60px;top:-90px;bottom:-90px;z-index:-1;
  background:radial-gradient(ellipse 60% 55% at 50% 50%,rgba(20,14,14,.42),rgba(20,14,14,0) 72%)}}
.tela .tl1{{font-family:'Montserrat';font-weight:700;font-size:50px;line-height:1.2;color:#fff;letter-spacing:.5px;
  text-shadow:0 1px 3px rgba(0,0,0,.55),0 3px 16px rgba(0,0,0,.4)}}
.tela .fil{{width:84px;height:5px;border-radius:3px;background:{BORDO};margin:16px auto 10px}}
.tela .tl2{{font-family:'Playfair Display';font-style:italic;font-weight:800;font-size:92px;line-height:1.08;color:#fff;
  text-shadow:0 2px 4px rgba(0,0,0,.5),0 4px 22px rgba(0,0,0,.45)}}
.tela .tl2 em{{font-style:italic;color:{BEGE}}}
.tela .pl{{font-family:'Playfair Display';font-style:italic;font-weight:800;font-size:84px;line-height:1.12;color:#fff;
  text-shadow:0 2px 4px rgba(0,0,0,.5),0 4px 22px rgba(0,0,0,.45)}}
.tela .pl .dot{{display:inline-block;width:16px;height:16px;border-radius:50%;background:{BORDO};margin-right:22px;vertical-align:middle}}
/* captions */
#caps{{position:absolute;left:90px;right:90px;top:1230px;height:200px;z-index:10}}
.cg{{position:absolute;left:0;right:0;top:0;text-align:center;opacity:0;visibility:hidden;
  font-family:'Montserrat';font-weight:700;font-size:56px;line-height:1.35;color:#fff;word-spacing:-8px}}
.w{{display:inline-block;padding:0 8px 3px;border-radius:12px;background:rgba(142,28,36,0);
  text-shadow:0 1px 3px rgba(0,0,0,.5),0 2px 14px rgba(0,0,0,.35)}}
/* emphasis title */
{T_IDS}{{position:absolute;left:70px;right:70px;top:1090px;text-align:center;z-index:12}}
{T_SMALL}{{font-family:'Montserrat';font-weight:700;font-size:56px;color:#fff;text-shadow:{HALO}}}
{T_BIG}{{font-family:'Playfair Display';font-style:italic;font-weight:800;font-size:116px;line-height:1.0;color:#fff;
  text-shadow:{HALO}}}
/* list cards */
.card{{position:absolute;left:90px;right:150px;background:rgba(239,230,216,.95);border-radius:28px;
  padding:34px 44px 30px;z-index:12;box-shadow:0 14px 40px rgba(0,0,0,.35);border-left:12px solid {BORDO}}}
{L_TOPS}
.card .head{{font-family:'Montserrat';font-weight:800;font-size:40px;color:{BORDO};text-transform:uppercase;letter-spacing:2px;margin-bottom:14px}}
.card .item{{font-family:'Montserrat';font-weight:700;font-size:54px;line-height:1.35;color:{PRETO};display:flex;align-items:center;gap:22px}}
.card .tick{{flex:0 0 26px;height:26px;border-radius:50%;background:{BORDO};display:inline-block}}
.card .foot{{font-family:'Playfair Display';font-style:italic;font-weight:800;font-size:58px;color:{BORDO};margin-top:12px}}
"""

hook_html = ""
if G:
    hook_end = fim_de(HOOK[1]) - 0.03
    linhas = "".join(f'<div class="{ {"serifa": "h2", "fina": "h3"}.get(l.get("estilo"), "h1") }" id="hq{n + 1}"' + (f' style="font-size:{l["px"]}px"' if l.get("px") else "") + f'>{esc(l["texto"])}</div>'
                     for n, l in enumerate(G["linhas"]))
    hook_html = f'<div id="hook" class="clip" data-start="0" data-duration="{round(hook_end, 3)}" data-track-index="4">{linhas}</div>'
tit_html = "".join(
    f'<div id="t{n + 1}" class="clip" data-start="{round(t(x["a"]) - 0.05, 3)}" data-duration="{round(fim_de(x["b"]) - round(t(x["a"]) - 0.05, 3), 3)}" data-track-index="{6 if n == 0 else 19 + n}">'
    f'<div class="small" id="t{n + 1}a">{esc(x["pequeno"])}</div><div class="big" id="t{n + 1}b">{esc(x["grande"])}</div></div>'
    for n, x in enumerate(TITULOS))
LEAKS = [round(t(p(x.get("grande_em", x["ate"]))) - 0.12, 3) for x in TITULOS if x.get("leak")]
leak_html = "".join(f'<div id="lk{n}" class="leak clip" data-start="{lt}" data-duration="0.9" data-track-index="{15 + n}"><div class="li"></div></div>'
                    for n, lt in enumerate(LEAKS))
lis_html = ""
for n, x in enumerate(LISTAS):
    if x.get("estilo") == "digitada":
        ls, le = round(t(x["a"]) - 0.05, 3), fim_de(x["b"])
        its = ""
        for m, (txt, _) in enumerate(x["itens"]):
            chs = "".join(f'<span class="ch" id="l{n + 1}i{m}c{k}">{esc(ch)}</span>' for k, ch in enumerate(txt))
            its += f'<div class="ti" id="l{n + 1}i{m}">{chs}<span class="cur" id="l{n + 1}i{m}k">▌</span></div>'
        lis_html += f'<div id="l{n + 1}" class="typed clip" data-start="{ls}" data-duration="{round(le - ls, 3)}" data-track-index="{7 + n}">{its}</div>'
        continue
    ls, le = round(t(x["a"]) - 0.05, 3), fim_de(x["b"])
    foot = f'<div class="foot" id="l{n + 1}f">{esc(x["rodape"][0])}</div>' if x.get("rodape") else ""
    lis_html += (f'<div id="l{n + 1}" class="card clip" data-start="{ls}" data-duration="{round(le - ls, 3)}" data-track-index="{7 + n}">'
                 f'<div class="head" id="l{n + 1}h">{esc(x["titulo"])}</div>{items_html(f"l{n + 1}i", [(i[0], p(i[1])) for i in x["itens"]])}{foot}</div>')

tela_html = ""
for n, x in enumerate(TELAS):
    ts, te = round(max(0, t(x["a"]) - 0.08), 3), fim_de(x["b"])
    if x.get("partes"):
        inner = "".join(f'<div class="pl" id="tp{n}_{m}"><span class="dot"></span>{esc(txt)}</div>' for m, (txt, _) in enumerate(x["partes"]))
    else:
        l2 = esc(x.get("linha2", ""))
        if x.get("destaque"):
            l2 = l2.replace(esc(x["destaque"]), f"<em>{esc(x['destaque'])}</em>")
        inner = (f'<div class="tl1" id="tl{n}a">{esc(x["linha1"])}</div><div class="fil" id="tf{n}"></div>'
                 + (f'<div class="tl2" id="tl{n}b" style="font-size:{x.get("px2", 92)}px">{l2}</div>' if x.get("linha2") else ""))
    top = x.get("top")
    sty = f' style="top:{top}px"' if top else ""
    tela_html += f'<div id="tela{n}" class="tela clip"{sty} data-start="{ts}" data-duration="{round(te - ts, 3)}" data-track-index="{30 + n}"><div class="glow"></div>{inner}</div>'

body = f"""
<div id="reel" data-composition-id="reel" data-start="0" data-duration="{DUR}" data-width="1080" data-height="1920">
 <div id="vwrap"><video id="v" src="assets/{'cut_fx.mp4' if os.path.exists(caminho('assets', 'cut_fx.mp4')) else 'cut.mp4'}" muted playsinline data-start="0" data-duration="{VID}" data-track-index="0"></video></div>
 <audio id="voice" src="assets/mix.wav" data-start="0" data-duration="{VID}" data-track-index="1" data-volume="1"></audio>
 {''.join(f'<div id="fb{n}" class="burn clip" data-start="{max(0, round(bt - 0.28, 3))}" data-duration="0.62" data-track-index="3"><div class="bi"></div></div>' for n, bt in enumerate(burns))}
 {hook_html}
 <div id="caps" class="clip" data-start="0" data-duration="{VID}" data-track-index="5">{''.join(cap_html)}</div>
 {tit_html}
 {leak_html}
 {lis_html}
 {tela_html}
</div>
"""

ghost = "{opacity:0,scale:1.08,filter:'blur(14px)',duration:0.22,ease:'power2.out'}"
js = ["const tl=gsap.timeline({paused:true});"]
for n, bt in enumerate(burns):
    s0 = max(0, round(bt - 0.28, 3))
    js.append(f"tl.fromTo('#fb{n}',{{opacity:0}},{{opacity:0.85,duration:0.28,ease:'sine.in'}},{s0});")
    js.append(f"tl.fromTo('#fb{n}',{{opacity:0.85}},{{opacity:0,duration:0.32,ease:'sine.out',immediateRender:false}},{s0 + 0.29:.3f});")
    js.append(f"tl.fromTo('#fb{n} .bi',{{x:-140,scale:1.05}},{{x:90,scale:1.18,duration:0.62,ease:'none'}},{s0});")
for n, lt in enumerate(LEAKS):
    js.append(f"tl.fromTo('#lk{n}',{{opacity:0}},{{opacity:0.8,duration:0.3,ease:'sine.out'}},{lt});")
    js.append(f"tl.to('#lk{n}',{{opacity:0,duration:0.5,ease:'sine.in'}},{lt + 0.38:.3f});")
    js.append(f"tl.fromTo('#lk{n} .li',{{x:120}},{{x:-60,duration:0.9,ease:'none'}},{lt});")
for a_, b_ in ZOOMS:  # aproximação suave (punch-in) pedida no plano
    js.append(f"tl.fromTo('#vwrap',{{scale:1}},{{scale:1.12,duration:0.4,ease:'power2.out',immediateRender:false}},{a_:.3f});")
    js.append(f"tl.set('#vwrap',{{scale:1}},{b_:.3f});")
for a_, s_ in PUNCH:  # punch-in seco no meio do trecho (troca de ideia)
    js.append(f"tl.set('#vwrap',{{scale:{s_}}},{a_:.3f});")
    js.append(f"tl.set('#vwrap',{{scale:1}},{clip_end(a_):.3f});")
for a_, b_, s_ in LENTOS:  # aproximação progressiva e volta gradual
    ce = clip_end(a_)
    b2 = min(b_, ce)
    js.append(f"tl.fromTo('#vwrap',{{scale:1}},{{scale:{s_},duration:{b2 - a_:.3f},ease:'sine.inOut',immediateRender:false}},{a_:.3f});")
    if ce - b2 > 0.55:
        js.append(f"tl.to('#vwrap',{{scale:1,duration:0.5,ease:'sine.inOut'}},{b2 + 0.01:.3f});")
    js.append(f"tl.set('#vwrap',{{scale:1}},{ce:.3f});")
for bt in WHIPS:  # chicote discreto: deslocamento lateral curto (o borrão de movimento vem do fx_transicoes.py)
    js.append(f"tl.fromTo('#vwrap',{{x:0,scale:1}},{{x:-70,scale:1.06,duration:0.08,ease:'power2.in',immediateRender:false}},{bt - 0.08:.3f});")
    js.append(f"tl.fromTo('#vwrap',{{x:70,scale:1.06}},{{x:0,scale:1,duration:0.16,ease:'power3.out',immediateRender:false}},{bt:.3f});")
for bt in BLURS:  # desfoque: leve respiro de escala junto com o desfoque do fx_transicoes.py
    js.append(f"tl.fromTo('#vwrap',{{scale:1.04}},{{scale:1,duration:0.3,ease:'sine.out',immediateRender:false}},{bt:.3f});")
if G:
    for n, l in enumerate(G["linhas"]):
        em = p(l["em"])
        js.append(f"tl.from('#hq{n + 1}',{ghost},{max(0.05, t(em) - 0.05):.3f});")
for n, x in enumerate(TITULOS):
    js.append(f"tl.from('#t{n + 1}a',{{opacity:0,y:18,duration:0.2,ease:'power2.out'}},{round(t(x['a']) - 0.05, 3)});")
    js.append(f"tl.from('#t{n + 1}b',{{opacity:0,scale:1.3,filter:'blur(18px)',duration:0.26,ease:'expo.out'}},{t(p(x.get('grande_em', x['ate']))) - 0.05:.3f});")
for n, x in enumerate(LISTAS):
    ls, le = round(t(x["a"]) - 0.05, 3), fim_de(x["b"])
    if x.get("estilo") == "digitada":
        starts = [t(p(it[1])) - 0.04 for it in x["itens"]]
        for m, (txt, _) in enumerate(x["itens"]):
            t0 = starts[m]; dt = min(0.035, 0.85 / max(1, len(txt)))
            js.append(f"tl.set('#l{n + 1}i{m}k',{{display:'inline'}},{t0:.3f});")
            for k in range(len(txt)):
                js.append(f"tl.set('#l{n + 1}i{m}c{k}',{{display:'inline'}},{t0 + k * dt:.3f});")
            if m + 1 < len(starts):
                js.append(f"tl.set('#l{n + 1}i{m}k',{{display:'none'}},{starts[m + 1]:.3f});")
            else:  # cursor do último item pisca até a lista sair
                tb, on = t0 + len(txt) * dt + 0.45, False
                while tb < le - 0.2:
                    js.append(f"tl.set('#l{n + 1}i{m}k',{{opacity:{1 if on else 0}}},{tb:.3f});"); on = not on; tb += 0.45
        js.append(f"tl.from('#l{n + 1}',{{opacity:0,duration:0.15}},{ls});")
        if le < VID:
            js.append(f"tl.to('#l{n + 1}',{{opacity:0,duration:0.15,ease:'power1.in'}},{le - 0.15:.3f});")
        continue
    js.append(f"tl.from('#l{n + 1}',{{opacity:0,x:-60,duration:0.28,ease:'power3.out'}},{ls});")
    for m, it in enumerate(x["itens"]):
        i = p(it[1])
        js.append(f"tl.from('#l{n + 1}i{m}',{{opacity:0,x:-24,filter:'blur(8px)',duration:0.2,ease:'power2.out'}},{t(i) - 0.04:.3f});")
        js.append(f"tl.from('#l{n + 1}i{m} .tick',{{scale:0,duration:0.18,ease:'back.out(2)'}},{t(i) - 0.04:.3f});")
    if x.get("rodape"):
        js.append(f"tl.from('#l{n + 1}f',{{opacity:0,y:16,duration:0.22,ease:'sine.out'}},{t(p(x['rodape'][1])) - 0.04:.3f});")
    if le < VID:
        js.append(f"tl.to('#l{n + 1}',{{opacity:0,duration:0.15,ease:'power1.in'}},{le - 0.15:.3f});")
for n, x in enumerate(TELAS):
    ts, te = round(max(0, t(x["a"]) - 0.08), 3), fim_de(x["b"])
    js.append(f"tl.from('#tela{n} .glow',{{opacity:0,duration:0.3,ease:'sine.out'}},{ts:.3f});")
    if x.get("partes"):
        for m, (txt, ref) in enumerate(x["partes"]):
            tm = ts if m == 0 else t(p(ref)) - 0.04
            js.append(f"tl.from('#tp{n}_{m}',{{opacity:0,y:16,filter:'blur(10px)',duration:0.26,ease:'power2.out'}},{tm:.3f});")
    else:
        js.append(f"tl.from('#tl{n}a',{{opacity:0,y:12,filter:'blur(8px)',duration:0.26,ease:'power2.out'}},{ts:.3f});")
        js.append(f"tl.from('#tf{n}',{{scaleX:0,duration:0.32,ease:'power3.out'}},{ts + 0.12:.3f});")
        if x.get("linha2"):
            js.append(f"tl.from('#tl{n}b',{{opacity:0,scale:1.06,filter:'blur(12px)',duration:0.3,ease:'power2.out'}},{ts + 0.2:.3f});")
    if te < VID:
        js.append(f"tl.to('#tela{n}',{{opacity:0,duration:0.2,ease:'power1.in'}},{te - 0.2:.3f});")
js += cap_js
js.append("window.__timelines=window.__timelines||{};window.__timelines['reel']=tl;")

doc = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>{esc(PLANO.get("titulo", "Reel"))}</title>
<script src="assets/gsap.min.js"></script>
<style>{css}</style></head><body>{body}
<script>
{chr(10).join(js)}
</script></body></html>
"""
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(doc)
print(f"index.html: {len(groups)} blocos de legenda, {DUR}s, film burn em {burns}")
for g, (st, en) in zip(groups, gtimes):
    print(f"  {st:6.2f}-{en:6.2f}  {' '.join(W[i]['text'] for i in g)}")
