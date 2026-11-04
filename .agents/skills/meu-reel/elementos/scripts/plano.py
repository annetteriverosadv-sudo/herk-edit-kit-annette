"""Leitura do assets/plano.json e localização de palavras ("texto#ocorrência+deslocamento")."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # pasta do projeto (scripts/..)


def caminho(*p):
    return os.path.join(ROOT, *p)


def carregar():
    return json.load(open(caminho("assets", "plano.json"), encoding="utf-8"))


def _norm(s):
    return s.strip(".,!?;:“”\"'").lower()


def palavra(words, ref):
    """Índice da palavra indicada por ref em words.
    'inicio' = 0, 'fim' = última; 'texto#n+k' = n-ésima ocorrência de texto, deslocada k (k pode ser negativo)."""
    if ref == "inicio":
        return 0
    if ref == "fim":
        return len(words) - 1
    m = re.fullmatch(r"(.+?)(?:#(\d+))?([+-]\d+)?", ref)
    if not m:
        raise SystemExit(f"referência inválida: {ref}")
    texto, n, k = m.group(1), int(m.group(2) or 1), int(m.group(3) or 0)
    achadas = [i for i, w in enumerate(words) if _norm(w["text"]) == _norm(texto)]
    if len(achadas) < n:
        raise SystemExit(f"palavra não encontrada: {ref} (achei {len(achadas)} ocorrência(s) de '{texto}')")
    i = achadas[n - 1] + k
    if not 0 <= i < len(words):
        raise SystemExit(f"deslocamento fora da fala: {ref}")
    return i
