---
name: meu-reel
description: Edita uma gravação da Dra. Annette Riveros (Riveros Advocacia) em Reel 9:16 no estilo dela — legenda palavra por palavra, film burn singelo, batida leve. Use em todo vídeo novo dela para o Instagram.
---

# Meu reel — Riveros Advocacia

Ela não programa: antes de cada passo, diga em **uma frase simples** o que vai fazer. Tudo em português.

## Antes de começar

1. Leia o [DESIGN.md](DESIGN.md). Ele manda sobre qualquer padrão do kit (cores, letras, transições, som).
2. Mantenha **as palavras dela**. Pode mudar a ordem das frases; não pode inventar fala, número ou promessa
   (Provimento OAB 205/2021).
3. Ferramentas (uma vez por máquina): whisper.cpp com o modelo `ggml-small.bin` (variáveis `WHISPER_*` no `.env`),
   detector de rosto Haar e modelo de voz RNNoise em `~/tools/models/` (ou `HAAR_XML` / `RNNOISE_MODEL`).
   Se o render não achar navegador: `export HYPERFRAMES_BROWSER_PATH=` com o caminho do Chrome.

## A ordem que seguimos

1. **Projeto.** `npm run new-video -- <nome>`. Copie para `video-projects/<nome>/`:
   este `DESIGN.md`; `elementos/scripts/*.py` e `elementos/audio/sons.py` → `scripts/`;
   `elementos/fontes/*` → `assets/fonts/`.
2. **Gravações originais.** Peça os arquivos do celular (WhatsApp comprime: enviar como *Documento*).
   Coloque em `source/orig/` e rode `python3 scripts/preparar.py` (cópias de trabalho + medida do rosto).
3. **Transcrever com o Whisper local** (nada vai para a internet), uma gravação por vez:
   `npm run transcribe -- video-projects/<nome>/source/work/<take>.mov -o video-projects/<nome>/transcripts/<take>.json --prompt "<termos do tema>"`.
   O `--prompt` com os termos jurídicos do tema (ex.: auxílio-acidente, indenizatória) corrige a grafia.
   Leia a transcrição inteira; a fala só sai pela transcrição (não dá para "ouvir").
4. **Plano.** Escreva `assets/plano.json` a partir de [plano_exemplo.json](elementos/scripts/plano_exemplo.json):
   ordem dos blocos (segue o roteiro dela), gancho, títulos e listas.
   - **Abertura:** compare 3 aberturas com a mesma fala e use a mais forte — de preferência a frase que o
     público diz ("Já voltei a trabalhar. Não tenho mais direito?"). Nada que ela não tenha dito.
   - Títulos (1 a 3) só no conceito central; listas só quando ela enumera. Animação só onde ajuda a entender.
5. **Cortes de erro — mostrar antes de aplicar.** Liste começos falsos, "vai!", "ok", "pode iniciar", voz de
   outra pessoa e repetições. Monte `review/cortes-de-erro.mp4` (cada trecho com rótulo "CORTE n — SERÁ REMOVIDO"),
   envie e **espere ela aprovar**. Pausas ≥ 0,30 s podem ser cortadas sem perguntar.
6. **Cortar.** `python3 scripts/edl.py` e `python3 scripts/render_cut.py` (usa os originais 4K, limpa a voz).
   Confira uma folha de contato: olhos na mesma altura em todos os trechos.
7. **Legenda e animações.** `python3 scripts/gen_comp.py`, depois `npx hyperframes lint` (0 erros).
   Legenda palavra por palavra: Montserrat, letras normais, caixa bordô na palavra falada.
8. **Som.** `python3 scripts/make_audio.py` (batida leve, transições, toques; mixagem a −14 LUFS).
9. **Rascunho antes de polir.** `npx hyperframes render --quality draft --output renders/rascunho-v1.mp4`.
   Confira quadros-chave, envie e **espere a aprovação** dela.
10. **Polir.** `--quality high`. Meça o volume no arquivo final (−14 LUFS), confira o film burn e o último quadro,
    registre em `VERIFY.md` e envie. Diga sempre que o som foi conferido só por medição.
11. **Correções.** Toda correção dela vira regra nova, com data, na seção "Correções" do [DESIGN.md](DESIGN.md)
    (e a regra antiga é ajustada). Se for sobre o processo, ajuste esta skill também.

## Elementos — quando usar cada um

| Elemento | Onde | Quando usar |
| --- | --- | --- |
| Fontes Montserrat (600/700/800) e Playfair Display itálico | [elementos/fontes](elementos/fontes) | Sempre: Montserrat na legenda, cartões e gancho; Playfair na palavra grande dos títulos e na 2ª linha do gancho |
| Batida leve (trilha) | [sons.py](elementos/audio/sons.py) `trilha()` | Sempre, do começo ao fim, 18–22 dB abaixo da voz (o `make_audio.py` já faz) |
| Som de transição (sopro + tom) | `sons.py` `sopro()` + `tom()` | Só nas trocas de assunto, junto com o film burn. Sempre baixo |
| Toque abafado | `sons.py` `toque()` | Quando entra a palavra grande de um título |
| Cliques secos | `sons.py` `clique()` | Um por item de lista, alternando o tom |
| Film burn singelo | `gen_comp.py` (classe `.burn`) | Em cada troca de bloco do plano — nunca em todo corte |
| Scripts | [elementos/scripts](elementos/scripts) | Em todo vídeo, na ordem acima |

Para ouvir os sons soltos (ou usar no CapCut): `python3 elementos/audio/sons.py <pasta> 60`.
**Filtro de cor, vinheta e logo ainda não fazem parte do estilo** — nenhum reel usou. Só crie se ela pedir
(o logo, só com o arquivo oficial dela).

## Correções feitas no reel do auxílio-acidente (04/11/2026)

- Sem cartão final de comentários: o vídeo termina na última fala dela.
- Trilha: batida leve e discreta (não piano).
- Legenda menor e suave: Montserrat SemiBold, ~58 px, letras normais, só sombra — nada de fonte condensada em caixa alta com contorno.
- Nada de selo de tema em cima da cabeça ("AUXÍLIO-ACIDENTE" no topo saiu).
- Transição: film burn singelo nas trocas de assunto, no lugar do flash bege.
- Som da transição: dois sons misturados (sopro + tom), harmônico e bem mais baixo.

## Armadilhas técnicas (já custaram tempo)

- `mix-blend-mode` não funciona sobre o vídeo no render (o vídeo é composto à parte): use camada com transparência normal.
- O `hyperframes snapshot` não mostra fades pela metade; confira efeitos curtos no vídeo renderizado.
- Meça o volume em **estéreo**: mixagem medida em mono sai 3 dB mais alta no vídeo final.
- Não use as músicas de exemplo do kit (licença incerta); a trilha da skill é original.
- Para baixar o modelo do Whisper, a rede precisa liberar `huggingface.co` e `*.hf.co`.
