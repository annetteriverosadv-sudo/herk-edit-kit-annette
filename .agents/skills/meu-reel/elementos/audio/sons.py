#!/usr/bin/env python3
"""Sons da Dra. Annette (Riveros) — trilha e efeitos originais, sintetizados aqui (sem direitos de terceiros).

Use como módulo (make_audio.py importa) ou rode sozinho para gerar os arquivos de exemplo:
    python3 sons.py <pasta-de-saida> [segundos-de-trilha]

- trilha(): batida leve e discreta, 88 BPM, lá menor (Am7 - Fmaj7 - Cmaj7 - G6), bumbo/aro/chimbal suaves
  e piano elétrico morno, com passa-baixa. Começa mais baixa no 1,5 s inicial e termina com fade curto.
- transicao(): mistura de dois sons — sopro suave + tom quente (lá/mi levemente desafinados). Vai nas trocas
  de assunto, junto com o film burn. Sempre baixo.
- clique(freq): clique seco e curto para cada item que aparece num cartão de lista (varie a frequência).
- toque(): batidinha abafada quando um título de palavra-chave aparece.
A ordem das chamadas ao gerador aleatório é fixa (semente 20261104), então o resultado é sempre igual.
"""
import os, sys, wave
import numpy as np

SR = 48000


class Sons:
    def __init__(self, seed=20261104):
        self.rng = np.random.default_rng(seed)

    # ---------- utilidades ----------
    @staticmethod
    def env(n, a, d, sustain=0.0):
        a_n, d_n = max(1, int(a * SR)), max(1, int(d * SR))
        e = np.zeros(n)
        e[:a_n] = np.linspace(0, 1, a_n)[:n]
        end = min(n, a_n + d_n)
        if a_n < n:
            e[a_n:end] = np.exp(-np.linspace(0, 6, end - a_n)) * (1 - sustain) + sustain
        if end < n:
            e[end:] = sustain
        return e

    @staticmethod
    def lp(x, fc):
        a = np.exp(-2 * np.pi * fc / SR)
        y = np.empty_like(x); acc = 0.0
        for i, v in enumerate(x):
            acc = (1 - a) * v + a * acc; y[i] = acc
        return y

    @staticmethod
    def add(buf, sig, t):
        i = int(round(t * SR))
        if i >= len(buf): return
        j = min(len(buf), i + len(sig))
        buf[i:j] += sig[: j - i]

    # ---------- trilha ----------
    def trilha(self, dur):
        N = int(round(dur * SR))
        bpm = 88.0; beat = 60 / bpm; bar = 4 * beat
        music = np.zeros(N + SR)
        tk = np.arange(int(0.45 * SR)) / SR
        kick = np.sin(2 * np.pi * (48 * tk + 70 * (1 - np.exp(-tk * 30)) / 30)) * np.exp(-tk * 9)
        rim_n = int(0.12 * SR)
        rim = self.lp(self.rng.standard_normal(rim_n), 2600) * np.exp(-np.arange(rim_n) / SR * 45)
        hat_n = int(0.05 * SR)
        hn = self.rng.standard_normal(hat_n)
        hat = (hn - self.lp(hn, 6000)) * np.exp(-np.arange(hat_n) / SR * 90)
        chords = [[57, 60, 64, 67], [53, 57, 60, 64], [48, 55, 59, 64], [55, 59, 62, 64]]
        bass = [45, 41, 48, 43]
        midi = lambda m: 440 * 2 ** ((m - 69) / 12)

        def epiano(freq, n):
            t = np.arange(n) / SR
            s = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 3)
                 + 0.12 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-t * 5))
            return s * (1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)) * self.env(n, 0.012, 2.2, 0.25)

        for b in range(int(np.ceil(dur / bar)) + 1):
            t0 = b * bar; ci = b % 4; n = int(bar * SR)
            self.add(music, 0.32 * sum(epiano(midi(m), n) for m in chords[ci]) / 4, t0)
            tb = np.arange(n) / SR
            self.add(music, 0.30 * np.sin(2 * np.pi * midi(bass[ci]) * tb) * self.env(n, 0.01, 1.4, 0.35), t0)
            for q in range(4):
                tq = t0 + q * beat
                if q in (0, 2): self.add(music, 0.55 * kick, tq)
                if q == 2 and b % 2 == 1: self.add(music, 0.35 * kick, tq + beat / 2)
                if q in (1, 3): self.add(music, 0.22 * rim, tq)
                for e8 in (0, 0.5):
                    self.add(music, (0.07 if e8 else 0.10) * hat, tq + e8 * beat + (0.035 if e8 else 0))
        music = self.lp(music, 5200)[:N]
        music *= np.clip(np.arange(N) / (1.5 * SR), 0.45, 1.0) * np.clip((N - np.arange(N)) / (0.6 * SR), 0, 1)
        return music / (np.max(np.abs(music)) + 1e-9)

    # ---------- efeitos ----------
    def sopro(self):
        wn = int(0.32 * SR); tw = np.arange(wn) / SR
        air = self.lp(self.rng.standard_normal(wn), 1800) - self.lp(self.rng.standard_normal(wn), 250)
        return air * np.sin(np.pi * np.clip(tw / 0.32, 0, 1)) ** 2

    def tom(self):
        t2 = np.arange(int(0.9 * SR)) / SR
        tone = sum(a * np.sin(2 * np.pi * f * t2) for f, a in ((440.0, 0.5), (441.2, 0.3), (659.3, 0.35), (880.0, 0.12)))
        tone = self.lp(tone * np.minimum(1, t2 / 0.06) * np.exp(-t2 * 4.2), 3500)
        return tone / np.max(np.abs(tone))

    def toque(self):
        tt = np.arange(int(0.18 * SR)) / SR
        return (np.sin(2 * np.pi * 180 * tt) + 0.4 * self.lp(self.rng.standard_normal(len(tt)), 900)) * np.exp(-tt * 28)

    def clique(self, freq):
        t = np.arange(int(0.06 * SR)) / SR
        return (np.sin(2 * np.pi * freq * t) * 0.6 + 0.4 * self.lp(self.rng.standard_normal(len(t)), 4000)) * np.exp(-t * 80)


# Níveis aprovados (04/11/2026) — mantenha baixos.
NIVEL_SOPRO, NIVEL_TOM, NIVEL_TOQUE, NIVEL_CLIQUE = 0.13, 0.07, 0.45, 0.22
FREQ_CLIQUES = [1450, 1300, 1550, 1380]


def write(path, x, channels=1):
    x = np.clip(x, -1, 1)
    with wave.open(path, "w") as w:
        w.setnchannels(channels); w.setsampwidth(2); w.setframerate(SR)
        data = (x * 32767).astype(np.int16)
        if channels == 2: data = np.repeat(data, 2)
        w.writeframes(data.tobytes())


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    os.makedirs(out, exist_ok=True)
    s = Sons()
    write(os.path.join(out, "trilha-batida-leve.wav"), 0.5 * s.trilha(secs))
    tr = np.zeros(int(1.2 * SR)); s.add(tr, NIVEL_SOPRO * s.sopro(), 0.0); s.add(tr, NIVEL_TOM * s.tom(), 0.20)
    write(os.path.join(out, "transicao.wav"), tr)
    write(os.path.join(out, "toque-titulo.wav"), NIVEL_TOQUE * s.toque())
    for k, f in enumerate(FREQ_CLIQUES):
        write(os.path.join(out, f"clique-item-{k + 1}.wav"), NIVEL_CLIQUE * s.clique(f))
    print("ok ->", out)
