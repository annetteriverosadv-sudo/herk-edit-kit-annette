#!/usr/bin/env python3
"""Troca a voz do vídeo por um áudio gravado à parte (locução) e sincroniza a imagem com ele.

Correção de 09/11/2026: "o áudio do vídeo ficou muito ruim, vou te fornecer um áudio gravado à parte;
sincronize, não deixe atrasado nem fora de sincronização".

Como funciona
- A locução manda no tempo: as pausas dela (>= 0,30 s) viram cortes, como no edl.py.
- Para cada trecho, as palavras da locução são casadas com as mesmas palavras da gravação de vídeo
  (difflib). O início e o fim de cada palavra casada viram âncoras (tempo locução -> tempo vídeo).
- Entre âncoras a velocidade do vídeo é ajustada (setpts por partes, limitada entre 0,65x e 1,5x),
  então a boca começa e termina cada palavra junto com o som. Onde a locução usa outras palavras,
  o vídeo é interpolado.
- Saídas no mesmo formato do pipeline: assets/edl.json, assets/transcript.json, assets/cut.mp4,
  assets/voice.wav (locução tratada). Depois: gen_comp.py, make_audio.py, render.

Uso: python3 scripts/sync_vo.py [--plano]   (--plano só mostra os trechos, sem renderizar)
Config em assets/plano.json -> "locucao": {arquivo, transcricao, correcoes, emendas, blocos, planos, aproximacoes}
"""
import json, os, re, subprocess, sys, difflib, unicodedata
from concurrent.futures import ThreadPoolExecutor
import numpy as np, soundfile as sf

from plano import ROOT, caminho

PLANO = json.load(open(caminho("assets", "plano.json")))
L = PLANO["locucao"]
FACES = json.load(open(caminho("assets", "faces.json")))
FACE_TARGET, EYE_TARGET = 0.175, 0.28
PAUSA, PRE, POST = 0.30, 0.10, 0.14
FPS, SR = 30, 48000
R_MIN, R_MAX = 0.7, 1.75          # velocidade do vídeo permitida
A_MIN, A_MAX = 0.72, 1.35          # aceleração permitida da voz (WSOLA, sem mudar o tom)
DERIVA = 0.06                     # atraso/adiantamento máximo da boca antes de um jump cut (s)
SO_PLANO = "--plano" in sys.argv


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", s)


def ref(ws, r, a0=0):
    """'palavra', 'palavra#2', 'palavra#2+1' -> índice (procura a partir de a0)."""
    m = re.match(r"^(.+?)(?:#(\d+))?([+-]\d+)?$", r)
    alvo, n, off = norm(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 0)
    c = 0
    for i in range(a0, len(ws)):
        if norm(ws[i]["text"]) == alvo:
            c += 1
            if c == n: return i + off
    sys.exit(f"palavra não encontrada: {r}")


# ---------- 1. locução: palavras corrigidas + emendas no áudio ----------
vo_x, sr = sf.read(caminho(L["arquivo"]), dtype="float64")
if vo_x.ndim > 1: vo_x = vo_x.mean(1)
assert sr == SR, "converta a locução para 48 kHz mono"
W = []
for tr in L["transcricao"]:   # lista de {json, de, ate}: pedaços de transcrição (para corrigir tempos ruins)
    d = json.load(open(caminho(tr["json"])))
    W += [dict(w) for w in d["words"] if tr["de"] <= w["start"] < tr["ate"]]
W.sort(key=lambda w: w["start"])
for w in W:
    w["text"] = L.get("correcoes", {}).get(w["text"], w["text"])

# correções de sequência ("com a emenda" -> "ou convenção") aplicadas por posição
for seq_de, seq_para in L.get("correcoes_seq", []):
    de = seq_de.split(); para = seq_para.split()
    for i in range(len(W) - len(de) + 1):
        if [norm(W[i + k]["text"]) for k in range(len(de))] == [norm(x) for x in de]:
            t0, t1 = W[i]["start"], W[i + len(de) - 1]["end"]
            novos = [dict(text=p, start=t0 + (t1 - t0) * k / len(para), end=t0 + (t1 - t0) * (k + 1) / len(para))
                     for k, p in enumerate(para)]
            W[i:i + len(de)] = novos
            break

# emendas: troca um trecho da locução por outro trecho dela mesma (ex.: "24 horas" dito errado -> "42 horas")
for e in L.get("emendas", []):
    a1, b1, a2, b2 = e["troca_de"], e["troca_ate"], e["por_de"], e["por_ate"]
    pedaco = vo_x[int(a2 * SR):int(b2 * SR)].copy()
    tempo = e.get("tempo", 1.0)
    if abs(tempo - 1) > 1e-3:
        tmp_i, tmp_o = "/tmp/_emenda_i.wav", "/tmp/_emenda_o.wav"
        sf.write(tmp_i, pedaco, SR)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp_i, "-af", f"atempo={tempo}", tmp_o], check=True)
        pedaco, _ = sf.read(tmp_o, dtype="float64")
    f = int(0.01 * SR)
    pedaco[:f] *= np.linspace(0, 1, f); pedaco[-f:] *= np.linspace(1, 0, f)
    antes, depois = vo_x[:int(a1 * SR)].copy(), vo_x[int(b1 * SR):].copy()
    antes[-f:] *= np.linspace(1, 0, f); depois[:f] *= np.linspace(0, 1, f)
    vo_x = np.concatenate([antes, pedaco, depois])
    delta = len(pedaco) / SR - (b1 - a1)
    novos = []
    for w in W:
        if w["end"] <= a1 + 0.02: novos.append(w)
        elif w["start"] >= b1 - 0.02: novos.append(dict(w, start=w["start"] + delta, end=w["end"] + delta))
    dur = len(pedaco) / SR
    ins = [dict(text=t, start=a1 + dur * k / len(e["palavras"]), end=a1 + dur * (k + 1) / len(e["palavras"]))
           for k, t in enumerate(e["palavras"])]
    W = sorted(novos + ins, key=lambda w: w["start"])
    print(f"emenda: {b1 - a1:.2f}s em {a1:.2f}s trocados por {dur:.2f}s ({' '.join(e['palavras'])})")

sf.write(caminho("assets", "vo_emendada.wav"), vo_x, SR, subtype="PCM_16")  # para o conferir_sync.py

# ---------- 2. fala da locução por energia (pausas >= 0,30 s viram cortes) ----------
hop = SR // 100
nfr = len(vo_x) // hop
edb = 20 * np.log10(np.sqrt(np.mean(vo_x[:nfr * hop].reshape(nfr, hop) ** 2, 1)) + 1e-9)
voiced = edb > L.get("limiar_db", -30)  # fala -10..-30 dB; respiração/rabo -33..-40; pausa -45..-60
runs, i = [], 0
while i < nfr:
    if voiced[i]:
        j = i
        while j < nfr and voiced[j]: j += 1
        if runs and i / 100 - runs[-1][1] < PAUSA: runs[-1][1] = j / 100
        else: runs.append([i / 100, j / 100])
        i = j
    else: i += 1
runs = [r for r in runs if r[1] - r[0] >= 0.08]
for dref in L.get("divisoes", []):  # troca de plano no meio de uma frase sem pausa
    w = W[ref(W, dref)]; t = w["start"] - 0.02
    for k, r in enumerate(runs):
        if r[0] + 0.3 < t < r[1] - 0.3:
            runs[k:k + 1] = [[r[0], t], [t, r[1]]]; break
for w in W:  # cada palavra vai para o trecho de fala mais próximo do seu meio
    m = (w["start"] + w["end"]) / 2
    w["run"] = min(range(len(runs)), key=lambda k: 0 if runs[k][0] <= m <= runs[k][1] else min(abs(m - runs[k][0]), abs(m - runs[k][1])))
    r = runs[w["run"]]
    w["s"], w["e"] = min(max(w["start"], r[0]), r[1] - 0.04), min(max(w["end"], r[0] + 0.04), r[1])

# ---------- 3. alinhamento som a som (DTW) entre a locução e o áudio do vídeo ----------
from scipy.fft import dct
from scipy.signal import resample_poly
take_words = {t: json.load(open(caminho("transcripts", f"{t}.json")))["words"] for t in FACES}
_src_cache = {}


def src_audio(take):
    if take not in _src_cache:
        p = caminho("assets", f"src16_{take}.wav")
        if not os.path.exists(p):
            orig = next(os.path.join(caminho("source", "orig"), take + e) for e in (".MOV", ".mov", ".mp4", ".MP4")
                        if os.path.exists(os.path.join(caminho("source", "orig"), take + e)))
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", orig, "-vn", "-ac", "1", "-af",
                            "highpass=f=100:poles=2,equalizer=f=57:t=h:w=5:g=-30,equalizer=f=112.5:t=h:w=6:g=-30,"
                            "equalizer=f=169:t=h:w=6:g=-20,equalizer=f=225:t=h:w=6:g=-15", "-ar", "16000", p], check=True)
        _src_cache[take], _ = sf.read(p, dtype="float64")
    return _src_cache[take]


VO16 = resample_poly(vo_x, 1, 3)
_MEL = None


def feats(y):
    """MFCC simples (40 mel, 20 coef. sem c0) + deltas, 10 ms, normalizado (tira a diferença de microfone)."""
    global _MEL
    n_fft, hop_ = 512, 160
    if _MEL is None:
        f = np.linspace(0, 8000, n_fft // 2 + 1)
        mel = lambda h: 2595 * np.log10(1 + h / 700); imel = lambda m: 700 * (10 ** (m / 2595) - 1)
        pts = imel(np.linspace(mel(60), mel(7600), 42))
        _MEL = np.array([np.clip(np.minimum((f - pts[k]) / (pts[k + 1] - pts[k]), (pts[k + 2] - f) / (pts[k + 2] - pts[k + 1])), 0, None) for k in range(40)])
    y = np.pad(y, (n_fft // 2, n_fft // 2))
    n = 1 + (len(y) - n_fft) // hop_
    fr = np.lib.stride_tricks.as_strided(y, (n, n_fft), (y.strides[0] * hop_, y.strides[0])) * np.hanning(n_fft)
    P = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    m = dct(np.log(P @ _MEL.T + 1e-10), type=2, axis=1, norm="ortho")[:, 1:21]
    m = (m - m.mean(0)) / (m.std(0) + 1e-8)
    d = np.gradient(m, axis=0)
    return np.hstack([m, d * 0.5])


def dtw(A, B):
    """passos (1,1),(1,2),(2,1): inclinação entre 0,5 e 2; sem dependência na mesma linha (vetorizado)."""
    An = A / np.linalg.norm(A, axis=1, keepdims=True); Bn = B / np.linalg.norm(B, axis=1, keepdims=True)
    C = 1 - An @ Bn.T
    N, M = C.shape; INF = 1e18
    D = np.full((N, M), INF); T = np.zeros((N, M), np.int8)
    LIVRE = min(M, 60)                      # início e fim livres no vídeo (até 0,6 s)
    D[0, :LIVRE] = C[0, :LIVRE]
    for i in range(1, N):
        c0 = np.full(M, INF); c0[1:] = D[i - 1, :-1]
        c1 = np.full(M, INF); c1[2:] = D[i - 1, :-2]
        c2 = np.full(M, INF)
        if i >= 2: c2[1:] = D[i - 2, :-1]
        st = np.vstack([c0, c1, c2]); k = st.argmin(0)
        D[i] = C[i] + st[k, np.arange(M)]; T[i] = k
    i, path = N - 1, []
    j = M - LIVRE + int(np.argmin(D[N - 1, M - LIVRE:]))
    while i > 0 and j > 0:
        path.append((i, j)); k = T[i, j]
        i, j = (i - 1, j - 1) if k == 0 else ((i - 1, j - 2) if k == 1 else (i - 2, j - 1))
    path.append((i, j))
    return path[::-1]


def ref_t(tw, r): return tw[ref(tw, r)]


blocos, pos = [], 0
for bv, bp in zip(L["blocos"], PLANO["blocos"]):
    a = ref(W, bv["de"], pos); b = ref(W, bv["ate"], a); pos = b + 1
    tw = take_words[bp["take"]]
    sa = ref(tw, bp["de"]); sb = ref(tw, bp["ate"], sa)
    blocos.append(dict(nome=bp["nome"], take=bp["take"], vo=(a, b), src=(sa, sb),
                       burn=bp.get("burn", True), fixo=bp.get("plano")))


def mapa_bloco(bl):
    a, b = bl["vo"]; sa, sb = bl["src"]; tw = take_words[bl["take"]]
    v0, v1 = runs[W[a]["run"]][0] - 0.15, runs[W[b]["run"]][1] + 0.15
    s0, s1 = max(0, tw[sa]["start"] - 0.6), tw[sb]["end"] + 0.6
    return mapa_trecho(bl["take"], v0, v1, s0, s1)


def mapa_trecho(take, v0, v1, s0, s1):
    ys = src_audio(take)
    A = feats(VO16[int(v0 * 16000):int(v1 * 16000)]); B = feats(ys[int(s0 * 16000):int(s1 * 16000)])
    path = dtw(A, B)
    vi = np.array([p[0] for p in path]); sj = np.array([p[1] for p in path])
    xs = np.arange(A.shape[0])
    ymap = np.array([sj[vi == k].mean() if np.any(vi == k) else np.nan for k in xs])
    ok = ~np.isnan(ymap); ymap = np.interp(xs, xs[ok], ymap[ok])
    return v0 + xs / 100, s0 + ymap / 100


def f_map(m, t):
    tx, ty = m
    if t <= tx[0]: return ty[0] - (tx[0] - t)
    if t >= tx[-1]: return ty[-1] + (t - tx[-1])
    return float(np.interp(t, tx, ty))


def crop_for(take, punch):
    f = FACES[take]
    base = max(FACE_TARGET / f["fh"], (1 - EYE_TARGET) / (1 - f["eye"]))
    s = base * punch; wh = 1 / s
    y0 = min(max(f["eye"] - EYE_TARGET * wh, 0), 1 - wh)
    x0 = min(max(f["cx"] - 0.5 * wh, 0), 1 - wh)
    return dict(zoom=round(s, 4), x=round(x0, 4), y=round(y0, 4), w=round(wh, 4),
                eye_out=round((f["eye"] - y0) / wh, 3), face_out=round(f["fh"] * s, 3))


VPL = {ref(W, z["em"]): z["plano"] for z in L.get("planos", [])}
# trecho da locução que começa noutra palavra do vídeo (ex.: locução "cai para…", vídeo "essas 42 horas caem para…")
GSRC = {ref(W, z["em"]): z["src"] for z in L.get("inicio_no_video", [])}
RITMO = [(W[ref(W, z["de"])]["s"], W[ref(W, z["ate"])]["e"], z.get("voz_max", 1.1), z.get("video_min", 0.55))
         for z in L.get("ritmo", [])]
VZM = {ref(W, z["em"]) for z in L.get("aproximacoes", [])}
PASSO = 0.20

clips, out_words, t_out, punch, AUDIO = [], [], 0.0, 1.0, []
for bi, bl in enumerate(blocos):
    m = mapa_bloco(bl)
    a, b = bl["vo"]
    rids = sorted({W[i]["run"] for i in range(a, b + 1)})
    print(f"[{bl['nome']}] {len(rids)} trechos de fala")
    for si, rid in enumerate(rids):
        g = [i for i in range(a, b + 1) if W[i]["run"] == rid]
        r = runs[rid]
        va = max(0.0, r[0] - PRE, (runs[rid - 1][1] + r[0]) / 2 if rid > 0 else 0)
        vb = r[1] + POST
        if rid + 1 < len(runs): vb = min(vb, (r[1] + runs[rid + 1][0]) / 2)
        n = max(1, round((vb - va) * FPS)); vb = va + n / FPS
        if g[0] in GSRC:
            tw_ = take_words[bl["take"]]; sw = tw_[ref(tw_, GSRC[g[0]])]
            s0_ = sw["start"] - (W[g[0]]["s"] - va) - 0.15
            m = mapa_trecho(bl["take"], va, vb, s0_, min(s0_ + (vb - va) * 1.8, tw_[bl["src"][1]]["end"] + 0.25))
        ts = list(np.arange(va, vb, PASSO)) + [vb]
        if len(ts) > 2 and ts[-1] - ts[-2] < PASSO / 2: ts.pop(-2)
        ts = np.array(ts)
        yv = np.array([f_map(m, t) for t in ts])
        if len(yv) > 2: yv = np.convolve(np.pad(yv, 1, mode="edge"), [0.25, 0.5, 0.25], mode="valid")
        # 09/11 "velocidade correta": o vídeo fica perto da velocidade real e a VOZ se ajusta (sem mudar o tom)
        dvo = np.diff(ts); dsrc = np.maximum(np.diff(yv), 0.01)
        amax = np.full(len(dvo), A_MAX); rmin_k = np.full(len(dvo) + 1, R_MIN)
        for rr in RITMO:  # trechos em que a voz não deve acelerar (fala fica embolada); o vídeo desacelera
            sel = (ts[:-1] + dvo / 2 >= rr[0] - 0.1) & (ts[:-1] + dvo / 2 <= rr[1] + 0.1)
            amax[sel] = rr[2]; rmin_k[np.r_[sel, False] | np.r_[False, sel]] = rr[3]
        tempo = dvo / np.clip(dsrc, dvo / amax, dvo / A_MIN)          # aceleração da voz em cada passo
        for _ in range(2):
            if len(tempo) > 2: tempo = np.convolve(np.pad(tempo, 1, mode="edge"), [0.25, 0.5, 0.25], mode="valid")
        u = np.r_[0, np.cumsum(dvo / tempo)]
        n = max(1, round(u[-1] * FPS)); u *= (n / FPS) / u[-1]
        AUDIO.append(dict(out_in=round(t_out, 4), frames=n, mapa=[(round(float(x), 5), round(float(y), 5)) for x, y in zip(u, ts)]))
        # vídeo: segue o alinhamento no tempo de saída u; velocidade limitada; se sair > DERIVA, jump cut
        segs, cur = [], [(u[0], max(0.0, yv[0]))]
        for t, y, rm in zip(u[1:], yv[1:], rmin_k[1:]):
            dv = t - cur[-1][0]
            yc = cur[-1][1] + min(max((y - cur[-1][1]) / dv, rm), R_MAX) * dv
            if abs(yc - y) > DERIVA and t < u[-1] - 0.4 and t - cur[0][0] >= 0.4:
                tq = round(t * FPS) / FPS  # corte no quadro
                cur.append((tq, yc)); segs.append(cur); cur = [(tq, y)]
            else:
                cur.append((t, yc))
        segs.append(cur)
        zoom = g[0] in VZM
        if si == 0: punch = 1.0
        elif clips and clips[-1]["last_text"][-1:] in ".?!:": punch = 1.0 if punch != 1.0 else 1.10
        if g[0] in VPL: punch = VPL[g[0]]
        zcrop = punch
        if zoom:  # aproximação suave parte do plano anterior (sem "voltar" antes de aproximar)
            zcrop = clips[-1]["punch"] if clips and clips[-1]["block"] == bl["nome"] else 1.0
            punch = 1.10
        if bl["fixo"]: punch, zoom, zcrop = bl["fixo"], False, bl["fixo"]
        for k, pts in enumerate(segs):
            f0, f1 = round(pts[0][0] * FPS), round(pts[-1][0] * FPS)
            if f1 <= f0: continue
            clip = dict(take=bl["take"], out_in=round(t_out + f0 / FPS, 4), out_out=round(t_out + f1 / FPS, 4),
                        frames=f1 - f0, block=bl["nome"], punch=punch,
                        burn=bool(bl["burn"] and si == 0 and bi > 0 and k == 0), zoom=bool(zoom and k == 0),
                        zoom_ate=round(t_out + n / FPS, 4), crop=crop_for(bl["take"], zcrop if zoom else punch),
                        src_in=round(pts[0][1], 4), src_out=round(pts[-1][1], 4),
                        pecas=[(round(p[0] - pts[0][0], 4), round(p[1] - pts[0][1], 4)) for p in pts],
                        last_text=W[g[-1]]["text"] if k == len(segs) - 1 else "", jump=k > 0)
            clips.append(clip)
        for i in g:
            out_words.append(dict(text=W[i]["text"], start=round(t_out + float(np.interp(max(W[i]["s"], va), ts, u)), 3),
                                  end=round(t_out + float(np.interp(min(W[i]["e"], vb), ts, u)), 3), type="word"))
        t_out = round(t_out + n / FPS, 4)

for k, c in enumerate(clips):
    rs = [(c["pecas"][j + 1][1] - c["pecas"][j][1]) / (c["pecas"][j + 1][0] - c["pecas"][j][0]) for j in range(len(c["pecas"]) - 1)]
    print(f"{k:2d} {c['out_in']:6.2f}-{c['out_out']:6.2f} {c['take']} src {c['src_in']:6.2f}-{c['src_out']:6.2f} "
          f"vel {min(rs):.2f}-{max(rs):.2f} p={c['punch']} z={int(c['zoom'])} b={int(c['burn'])} j={int(c['jump'])} | "
          + " ".join(w["text"] for w in out_words if c["out_in"] - 1e-3 <= w["start"] < c["out_out"]))
print(f"duração final {t_out:.2f}s")
json.dump(dict(clips=clips, audio=AUDIO, duration=round(t_out, 3)), open(caminho("assets", "edl.json"), "w"), indent=1, ensure_ascii=False)
json.dump(dict(words=out_words, language="pt"), open(caminho("assets", "transcript.json"), "w"), indent=1, ensure_ascii=False)
if SO_PLANO: sys.exit(0)

# ---------- 3. vídeo: cada trecho com velocidade por partes ----------
ORIG, TMP = caminho("source", "orig"), caminho("assets", "clips_vo")
os.makedirs(TMP, exist_ok=True)
COR = PLANO.get("cor", {})


def _orig(take):
    for ext in (".MOV", ".mov", ".mp4", ".MP4"):
        p = os.path.join(ORIG, take + ext)
        if os.path.exists(p): return p


def _size(path):
    o = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height:stream_side_data=rotation", "-of", "json", path],
                                  capture_output=True, text=True).stdout)["streams"][0]
    rot = next((abs(int(float(d["rotation"]))) for d in o.get("side_data_list", []) if "rotation" in d), 0)
    return (o["height"], o["width"]) if rot in (90, 270) else (o["width"], o["height"])


def setpts_expr(pecas):
    # T = tempo de entrada (relativo); saída = y(T) linear por partes. pecas: (out, in)
    ex = None
    for j in range(len(pecas) - 2, -1, -1):
        (o0, i0), (o1, i1) = pecas[j], pecas[j + 1]
        k = (o1 - o0) / (i1 - i0)
        seg = f"({o0:.5f}+(T-{i0:.5f})*{k:.6f})"
        ex = seg if ex is None else f"if(lt(T,{i1:.5f}),{seg},{ex})"
    return ex


def job(kc):
    k, c = kc
    src = _orig(c["take"]); SW, SH = _size(src); cr = c["crop"]
    w, h = round(cr["w"] * SW / 2) * 2, round(cr["w"] * SH / 2) * 2
    x, y = round(cr["x"] * SW), round(cr["y"] * SH)
    g = COR.get(c["take"], 1.0)
    dur_in = c["src_out"] - c["src_in"] + 0.2
    vf = (f"setpts=PTS-STARTPTS,setpts='({setpts_expr(c['pecas'])})/TB',"
          f"crop={w}:{h}:{x}:{y},scale=1080:1920:flags=lanczos,"
          f"colorchannelmixer=rr={0.98 * g:.3f}:gg={g:.3f}:bb={1.035 * g:.3f},"
          f"eq=contrast=1.03:saturation=1.02,unsharp=5:5:0.35:5:5:0,fps={FPS},setsar=1,"
          f"trim=end_frame={c['frames']},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop={c['frames']}")
    out = os.path.join(TMP, f"v{k:02d}.mp4")
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{max(0, c['src_in']):.3f}",
                        "-t", f"{dur_in:.3f}", "-i", src, "-an", "-vf", vf, "-frames:v", str(c["frames"]),
                        "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-pix_fmt", "yuv420p", out],
                       capture_output=True, text=True)
    if r.returncode: sys.exit(r.stderr[-1500:])
    return out


with ThreadPoolExecutor(2) as ex:
    outs = list(ex.map(job, enumerate(clips)))
lst = os.path.join(TMP, "list.txt")
open(lst, "w").write("".join(f"file '{o}'\n" for o in outs))

# ---------- 4. áudio: a voz é esticada/encolhida (WSOLA, mesmo tom) para caber no tempo da imagem ----------
from scipy.signal import decimate


def wsola(x, mapa, n_out):
    """mapa: [(t_saida, t_entrada)] em s. Quadros de 32 ms, salto de 16 ms, busca de ±5 ms pela melhor emenda."""
    N, Hs, TOL = 1536, 768, 240
    win = np.hanning(N); mu = np.array([p[0] for p in mapa]); mv = np.array([p[1] for p in mapa])
    y = np.zeros(n_out + N); wsum = np.zeros(n_out + N)
    prev = None
    for k in range(0, n_out, Hs):
        c = int(round(np.interp((k + N / 2) / SR, mu, mv) * SR)) - N // 2
        if prev is not None:
            nat = prev + Hs
            lo, hi = max(0, c - TOL), min(len(x) - N, c + TOL)
            if hi > lo and 0 <= nat <= len(x) - N:
                ref_ = x[nat:nat + N:6]; seg_ = x[lo:hi + N:6]
                cc = np.correlate(seg_, ref_, mode="valid")
                c = lo + int(np.argmax(cc)) * 6
        c = min(max(c, 0), len(x) - N)
        y[k:k + N] += x[c:c + N] * win; wsum[k:k + N] += win
        prev = c
    return (y / np.maximum(wsum, 1e-3))[:n_out]


partes = []
for g_ in AUDIO:
    n = int(round(g_["frames"] / FPS * SR))
    seg = wsola(vo_x, g_["mapa"], n)
    f = int(0.012 * SR); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
    partes.append(seg)
voz = np.concatenate(partes)
sf.write(caminho("assets", "voice_vo_raw.wav"), voz, SR, subtype="PCM_16")
# tratamento leve: a locução já é limpa e de perto; conserta picos estourados (adeclip), graves, chiado e uniformidade
RNN = os.environ.get("RNNOISE_MODEL") or os.path.expanduser("~/tools/models/sh.rnnn")
# 09/11 "reduz os ruídos, isola a voz, retira o barulho do fundo": RNNoise cheio + redução espectral leve +
# expansor nas pausas; depois presença, compressão e volume.
cadeia = ("adeclip,highpass=f=90:poles=2,lowpass=f=12500,"
          f"arnndn=m='{RNN}':mix=1,afftdn=nr=12:nf=-60:tn=1,"
          "loudnorm=I=-20:TP=-3:LRA=11:linear=true,"
          "deesser=i=0.35,equalizer=f=250:t=q:w=1.2:g=-1.5,equalizer=f=3000:t=q:w=1.2:g=2,"
          "acompressor=threshold=-24dB:ratio=3:attack=6:release=120:makeup=3,"
          # expansor DEPOIS da compressão: as pausas ficam realmente quietas (o compressor levantava o fundo)
          "agate=threshold=0.035:ratio=4:range=0.03:attack=3:release=160:knee=3,"
          "loudnorm=I=-15:TP=-1.5:LRA=6")
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", caminho("assets", "voice_vo_raw.wav"),
                "-af", cadeia, "-ar", str(SR), "-c:a", "pcm_s16le", caminho("assets", "voice.wav")], check=True)
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                "-i", caminho("assets", "voice.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-shortest", caminho("assets", "cut.mp4")], check=True)
print("ok: assets/cut.mp4 + assets/voice.wav", f"({len(voz) / SR:.2f}s de voz, {sum(c['frames'] for c in clips) / FPS:.2f}s de vídeo)")
