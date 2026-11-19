"""Elementos próprios deste reel (descontos indevidos no INSS), carregados pelo gen_comp.py.

19/11 (v3), no estilo do reel de referência dela ("Reel-beneficios-contribuicao-v4"):
- quadro de destaque = linha pequena em cima + linha grande com a palavra-chave em caixa bordô,
  na MESMA altura da legenda; enquanto o quadro está na tela, a legenda some (fica só ele);
- enquadramento fixo; aproximações suaves só nos momentos-chave; um único film burn (vem do plano).
montar(...) devolve dict(css, html, js, ocultar=[(i0, i1)], sons=[(tipo, tempo)]).
"""
import html as _h, re

BORDO, VERM = "#8E1C24", "#C62828"
HALO = "0 0 2px rgba(0,0,0,.55), 0 2px 6px rgba(0,0,0,.55), 0 0 22px rgba(0,0,0,.45)"
TOPO = 1075   # topo do quadro (a legenda fica em 1190; o quadro ocupa ~1075-1330)


def montar(W, p, t, EDL, VID, PLANO):
    clips = EDL["clips"]
    blocos = []
    for c in clips:
        if not blocos or blocos[-1]["nome"] != c["block"]:
            blocos.append(dict(nome=c["block"], a=c["out_in"], b=c["out_out"]))
        else:
            blocos[-1]["b"] = c["out_out"]

    def fim_clip(x):
        return next(c["out_out"] for c in clips if c["out_in"] - 1e-3 <= x < c["out_out"])

    def fim_bloco(x):
        return next(b["b"] for b in blocos if b["a"] - 1e-3 <= x < b["b"])

    def ate(i):  # fim de um quadro que vai até a palavra i: começo da palavra seguinte
        return round(t(i + 1) - 0.06, 3) if i + 1 < len(W) else VID

    css, html, js, ocultar, sons = [], [], [], [], []
    css.append(f"""
.qd{{position:absolute;z-index:12;left:60px;right:60px;top:{TOPO}px;text-align:center}}
.qd .pq{{font-family:'Montserrat';font-weight:700;font-size:46px;line-height:1.25;color:#fff;text-shadow:{HALO}}}
.qd .gd{{font-family:'Montserrat';font-weight:800;font-size:84px;line-height:1.22;color:#fff;text-shadow:{HALO};margin-top:6px}}
.qd .kb{{display:inline-block;background:{BORDO};border-radius:12px;padding:0 18px 6px;text-shadow:none}}
.qd .kb.vm{{background:{VERM};letter-spacing:2px}}
.dip{{position:absolute;inset:0;z-index:9;background:#1A1A1A;opacity:0;pointer-events:none}}
""")
    n_q = [0]

    def quadro(i0, i1, pequeno, grande, t0=None, t1=None, som=True, tg=None):
        """quadro que cobre as palavras i0..i1 (a legenda some nesse trecho)."""
        k = n_q[0]; n_q[0] += 1
        a = round(t0 if t0 is not None else t(i0) - 0.06, 3)
        z = round(t1 if t1 is not None else ate(i1), 3)
        html.append(f'<div id="qd{k}" class="qd clip" data-start="{a}" data-duration="{round(z - a, 3)}" data-track-index="{30 + k}">'
                    f'<div class="pq" id="qd{k}p">{pequeno}</div><div class="gd" id="qd{k}g">{grande}</div></div>')
        js.append(f"tl.from('#qd{k}p',{{opacity:0,y:14,filter:'blur(8px)',duration:0.22,ease:'power2.out'}},{a:.3f});")
        g0 = tg if tg is not None else a + 0.12   # linha grande pode entrar depois (na palavra dita)
        js.append(f"tl.from('#qd{k}g',{{opacity:0,scale:1.12,filter:'blur(12px)',duration:0.26,ease:'expo.out'}},{g0:.3f});")
        js.append(f"tl.from('#qd{k} .kb',{{scaleX:0.6,opacity:0,duration:0.22,ease:'back.out(1.7)'}},{g0 + 0.08:.3f});")
        js.append(f"tl.to('#qd{k}',{{opacity:0,duration:0.14,ease:'power1.in'}},{z - 0.14:.3f});")
        ocultar.append((i0, i1))
        if som: sons.append(("toque", g0))
        return k, a, z

    kb = lambda s, vm=False: f'<span class="kb{" vm" if vm else ""}">{s}</span>'

    # 1. gancho: "R$ 30 por mês, parece pouco, não é?" -> quadro; depois "R$ 1.800" com contador
    i30, inao1 = p("R$\u00a030"), p("não")
    quadro(i30, inao1 + 1, "R$&nbsp;30 por mês", f"parece {kb('pouco?')}", t0=0.0, som=False)
    i18 = p("R$\u00a01.800")
    k, a, z = quadro(i18, i18 + 4, "R$&nbsp;30/mês em 5 anos =", kb('R$&nbsp;<span id="eqN">1.800</span>'))
    n = 18; tB = a + 0.2
    vals = [f"{round(1800 * (1 - (1 - j / n) ** 3) / 10) * 10:,}".replace(",", ".") for j in range(n + 1)]
    spans = "".join(f'<span id="eqN{j}" style="display:{"inline" if j == n else "none"}">{v}</span>' for j, v in enumerate(vals))
    html[-1] = html[-1].replace('<span id="eqN">1.800</span>', f'<span id="eqN">{spans}</span>')
    js.append(f"tl.set('#eqN{n}',{{display:'none'}},0);tl.set('#eqN0',{{display:'inline'}},0);")
    for j in range(1, n + 1):
        js.append(f"tl.set('#eqN{j - 1}',{{display:'none'}},{tB + j / 30:.3f});tl.set('#eqN{j}',{{display:'inline'}},{tB + j / 30:.3f});")

    # 2. virada: "Você autorizou isso?" sobre "que, na maioria das vezes, as pessoas não contrataram."
    ique, icon = p("que#2"), p("contrataram")
    quadro(ique, icon, "Você", f"{kb('autorizou')} isso?", t1=round(fim_bloco(t(ique)) - 0.06, 3))

    # 3a. "é proibido, mesmo com contratação" -> Associação ou sindicato: PROIBIDO
    ipr, ictr = p("é#2"), p("contratação")
    quadro(ipr, ictr, "Associação ou sindicato:", kb("PROIBIDO", True), t1=round(fim_bloco(t(ipr)) - 0.06, 3))

    # 3b. "pessoalmente com biometria" -> Só vale; "não é válido" -> NÃO VALE
    ipe, ibio = p("pessoalmente"), p("biometria")
    quadro(ipe, ibio, "Só vale", f"pessoalmente,<br>com {kb('biometria')}")
    ipor, inao3, ival = p("por#2"), p("não#3"), p("válido#2")
    quadro(ipor, ival, "Por telefone ou procuração:", kb("NÃO VALE", True),
           t1=round(fim_bloco(t(inao3)) - 0.06, 3), tg=round(t(inao3) - 0.06, 3))

    # 4. "a restituição do valor integral" -> Dinheiro de volta; "em dobro mais indenização..." -> + indenização
    ires, iint = p("restituição"), p("integral")
    quadro(ires - 2, iint, "A lei prevê", kb("dinheiro de volta"))
    iem, imor = p("em"), p("morais")
    quadro(iem, imor, "Em dobro (CDC)", f"+ {kb('indenização')}", t1=round(fim_bloco(t(iem)) - 0.06, 3))

    # 5. "aplicativo Meu INSS ... extrato do INSS." -> Meu INSS › extrato
    iapl, iins = p("aplicativo"), p("INSS#3")
    quadro(iapl, iins, "Aplicativo", f"{kb('Meu INSS')} › extrato")

    # ---------- movimentos (#vwrap): aproximações suaves + véu de opacidade (sem mexer no enquadramento) ----------
    mov = []
    for ref, alvo, dur in PLANO.get("aproximacoes_suaves", []):
        x = t(p(ref)) - 0.1
        mov.append((x, fim_clip(x + 0.11), 1.0, alvo, dur, "sine.inOut"))
    for bl in blocos[1:]:
        if PLANO.get("transicoes", {}).get(bl["nome"]) == "escurecer":
            nd = sum(1 for h_ in html if 'class="dip' in h_)
            html.append(f'<div id="dip{nd}" class="dip clip" data-start="{bl["a"]}" data-duration="0.4" data-track-index="{50 + nd}"></div>')
            js.append(f"tl.fromTo('#dip{nd}',{{opacity:0.4}},{{opacity:0,duration:0.38,ease:'sine.out'}},{bl['a']:.3f});")
    mov.sort()
    for k, (a, r, s0, s1, dur, ease) in enumerate(mov):
        if k + 1 < len(mov) and mov[k + 1][0] < r:
            r = mov[k + 1][0]
        js.append(f"tl.fromTo('#vwrap',{{scale:{s0}}},{{scale:{s1},duration:{min(dur, r - a):.3f},ease:'{ease}',immediateRender:false}},{a:.3f});")
        js.append(f"tl.set('#vwrap',{{scale:1}},{r:.3f});")

    # invólucro: o HyperFrames controla o clip; as animações (e o fechamento) ficam no elemento interno
    out = []
    for h_ in html:
        m = re.match(r'<div id="([^"]+)" class="([^"]*?)\s*clip" (data-start="[^"]+" data-duration="[^"]+" data-track-index="[^"]+")(.*)$', h_, re.S)
        if not m:
            out.append(h_); continue
        id_, cls, attrs, rest = m.groups()
        out.append(f'<div id="{id_}_c" class="clip" {attrs}><div id="{id_}" class="{cls}"{rest}</div>')
        fim = float(re.search(r'data-start="([^"]+)"', attrs).group(1)) + float(re.search(r'data-duration="([^"]+)"', attrs).group(1))
        js.append(f"tl.set('#{id_}',{{opacity:0}},{fim:.3f});")
    return dict(css="".join(css), html="\n ".join(out), js="\n".join(js), ocultar=ocultar, sons=sons, mov=mov)
