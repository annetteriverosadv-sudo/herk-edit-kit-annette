# DESIGN — Reels da Dra. Annette Riveros (Riveros Advocacia)

Regras curtas para editar todo Reel deste projeto. Valem para qualquer vídeo novo,
salvo pedido diferente da Dra. Annette na hora.

**Correções:** cada correção que ela fizer vira regra nova na seção "Correções"
(no fim), com data. Correção nova vence regra antiga; ajuste a regra antiga também.

## Quem fala e para quem

- Advogada previdenciária e cível, mais de 18 anos de carreira, OAB/TO 3.066.
- Público: benefícios rurais, urbanos e de regime próprio (servidor público), além de cível.
- Linguagem simples: muita gente do campo assiste. Termo técnico (CNIS, carência, DTC) sempre explicado na tela ou na fala.
- Tom: firme, acolhedor e técnico. Sem sensacionalismo.
- Publicidade da advocacia (Provimento OAB 205/2021): nunca prometer resultado, nunca falar de valores de honorários e nunca usar captação agressiva.

## Paleta

Única cor de destaque: **bordô**. Os hex abaixo são estimados e devem ser confirmados com o arquivo da marca.

| Uso | Cor | Hex |
| --- | --- | --- |
| Destaque (palavra, caixa, filete) | bordô | #8E1C24 |
| Alerta pontual ("NEGADO", "CUIDADO") e light leak | vermelho | #C62828 |
| Texto e fundos escuros | preto suave | #1A1A1A |
| Fundos neutros e textos secundários | cinza | #6B6B6B / claro #E9E9E8 |
| Flash, cartões e fundo de encerramento | bege | #EFE6D8 |
| Legenda | branco | #FFFFFF |

- Vermelho aparece no máximo 2 vezes por vídeo. Nunca usar amarelo, azul, verde ou neon como destaque.
- Figurino nas cores da marca (preto, bordô, bege, cinza). A roupa combinando com a paleta deixa o vídeo "de marca".
- Fundo de cenário rosa ou colorido: dessaturar 10–15% para não competir com o rosto.

## Legendas

- 2 a 4 palavras por bloco, em 1 ou 2 linhas, centralizadas.
- Fonte Montserrat **Bold (700)** — mais grossa que a SemiBold (correção de 09/11/2026) —, em letras normais (sem CAIXA ALTA), branca, só com sombra suave — sem contorno preto grosso e sem fonte condensada pesada (correção de 04/11/2026).
- Tamanho: ~3% da altura do quadro (≈ 58 px em 1080×1920).
- Posição: bloco entre **62% e 72% da altura** (cintura). Nunca sobre o rosto e nunca abaixo de 75%, por causa da interface do Instagram.
- **Sem karaokê** (correção de 19/11/2026: "as legendas juntamente com as palavras em destaque fica estranho"): nada de caixa pulando de palavra em palavra. Só a **palavra-chave** do bloco ganha caixa bordô (uma caixa única para a expressão inteira, ex. "desconto indevido"), como no reel de referência dela (Reel-beneficios-contribuicao-v4). `"karaoke": false` no plano.
- **Quadro de destaque sozinho:** quando entra um quadro (linha pequena Montserrat 700 ~46 px + linha grande Montserrat 800 ~84 px com a palavra-chave em caixa bordô; vermelho só para PROIBIDO/NÃO VALE), ele fica **na mesma altura da legenda** e a legenda some — nunca legenda e quadro juntos.
- Troca de bloco por corte seco.
- Palavra-chave do tema (benefício, direito, prazo) pode ser destacada em bordô durante o bloco inteiro: no máximo 1 por bloco.
- Pontuação e ortografia revisadas sempre, principalmente nomes de benefícios e leis.

## Ênfase grande (títulos de palavra-chave)

- 3 a 4 por vídeo, nunca duas seguidas. Substituem a legenda naquele momento.
- Mistura de duas fontes na mesma frase: linha pequena em sans + palavra grande em **serifa itálica** (Playfair Display Italic), branca ou bege.
- Palavra grande com ~7–9% da altura do quadro, na faixa entre 40% e 60% da altura, alinhada à esquerda ou ao centro.
- Entrada: cada linha surge "fantasma" (transparente e desfocada) e fica nítida em 0,2 s. A frase vai empilhando linha por linha.
- Saída: corte seco ou fade de 0,15 s.

## Gancho (0–3 s)

- Começa já com a frase-problema, sem "olá" nem apresentação.
- **Sem selo/rótulo de tema em cima da cabeça dela** (ex.: "AUXÍLIO-ACIDENTE" no topo) — correção de 04/11/2026.
- Título empilhado de 2–3 linhas (sans pesada + palavra em serifa itálica), entrando linha por linha. Posição: terço superior (25–45%), sem tapar os olhos.
- Opção: pergunta direta no topo ("VOCÊ SABE O QUE É…?") com a resposta aparecendo na legenda.
- O primeiro corte ou mudança visual acontece antes de 3 s.

## Ritmo e cortes

- Mudança visual a cada **2,5–4,5 s** (b-roll, punch-in, título ou flash). Nunca mais de 6 s parado.
- Jump cut em todo silêncio ≥ 0,18 s que deixe pelo menos 0,1 s para tirar (correção de 19/11/2026: "nos pontos em que ela demora a falar a palavra, corte e já deixe na palavra sendo dita"): respiro de 0,06 s antes e 0,15 s depois da fala (menos que 0,15 s comeu o "-ram" de "contrataram"); trecho com menos de 0,5 s não vira corte próprio. Pausas medidas na mesma voz que vai ao ar. Nunca cortar no meio de palavra; não acelerar a fala.
- ~~Punch-in alternando aberto e fechado~~ (substituído em 19/11/2026 pelo enquadramento fixo; ver Imagem).
- B-roll de 2–4 s, coerente com a frase (trabalhador rural, gestante, documento, INSS, servidor), escurecido 20–30% quando tem legenda por cima.
- Lista falada ("print, extratos, comprovantes"): texto digitado letra a letra, alinhado à esquerda, com cursor ▌.

## Transições

- **Padrão:** corte seco ou punch-in.
- **Film burn singelo: no máximo UM por vídeo**, num único momento estratégico de virada (correção de 19/11/2026: "está ficando excessivamente repetitivo e deixa o vídeo com aparência padronizada"). Brilho quente âmbar/bordô entrando pela lateral, ~0,6 s, discreto, em camada com transparência normal. Nas outras trocas de assunto: corte seco/match cut, ou véu escuro leve que se abre (opacidade 40%→0 em 0,4 s — nunca tela preta). Sem movimentos de câmera nas transições (19/11/2026: enquadramento fixo).
- **Aproximações suaves** só nos momentos-chave da fala (prejuízo, pergunta, proibição, requisito, direito, chamada final): 100%→106–107% em 1,2–1,6 s, sine.inOut, desfeitas no corte seguinte. Nunca em todos os cortes.
- **Whip/borrão de movimento** (1–2 quadros) para entrar no b-roll.
- **Light leak vermelho→âmbar**: no máximo 2 por vídeo, só em palavra de impacto.
- Proibido: cubo, giro, slide, glitch pesado.

## Imagem

- 9:16, 1080×1920, 30 fps.
- **Enquadramento fixo e igual em todos os cortes** (correção de 19/11/2026: "o enquadramento tá bem estranho, corta um pouco"): rosto com ~23% da altura do quadro e olhos a 28% do topo, como no reel de referência; sem alternar aberto/fechado a cada frase e sem movimentos de câmera nas transições (`"rosto_fixo": 0.23` no plano). Só as aproximações suaves dos momentos-chave (100%→106%).
- Grade quente e sóbria: pele natural, fundo um pouco mais escuro que o rosto. (Filtro de cor, vinheta e grão ainda não foram aplicados em nenhum reel — só usar se ela pedir.)
- **Fundo desfocado e um pouco mais escuro quando estiver poluído** (correção de 19/11/2026: "melhore o enquadramento e a iluminação"): recorte da pessoa com MODNet (`fundo.py`; desfoque 14, fundo a 74% do brilho e 85% da cor, pessoa com meios-tons +6%), máscara suavizada no tempo e zerada a cada corte. O rosto vira o ponto mais claro do quadro, como na referência. Prefira cenário neutro (cinza claro, bege ou estante).
- Logo Riveros no canto: ainda não usado (falta o arquivo oficial do logo) — só com o arquivo dela e se ela pedir.

## Música e som

- **Sem música de fundo** (correção de 04/11/2026: a trilha "ficou com ruído e estragou o áudio"). O som é a voz, limpa, mais os efeitos suaves.
- **Voz alta, seca e "de microfone perto"** (correções de 09/11/2026: "parece que está dentro de um banheiro", "deixa como se tivesse gravado por microfone"): tirar zumbido de motor/ar-condicionado (filtros estreitos nas frequências do zumbido, ex. 57/112 Hz); tirar o eco da sala com `dereverb.py` (WPE + supressão do rabo, força 0,6); RNNoise; expansor bem suave; corpo de microfone próximo (+3 dB em 170 Hz), corte da caixa (380 Hz) e presença (3 kHz). Não usar afftdn depois do dereverb (come o fim das palavras). Conferir com o Whisper, em trechos de ~13 s, que nenhuma palavra foi "comida".
- **Áudio externo gravado AO MESMO TEMPO que o vídeo** (outro celular, enviado pelo WhatsApp) (19/11/2026): é a voz principal, sem esticar nada. Sincronizar pelo som da câmera (que é sincronizado de fábrica) com `alinhar_externo.py`: deslocamento exato por GCC-PHAT na faixa 300–3500 Hz, conferido em janelas de 3 s (no reel dos descontos: 0–5 ms do início ao fim, sem deriva). Tratar a voz de cada gravação inteira antes de cortar (`tratar_voz.py`): zumbido medido nas pausas (58,6 Hz), RNNoise a 0,7 (a 0,9 deformava "desconto indevido"), volume da fala igual entre gravações. **Conferir palavra-chave por palavra-chave** (números, nomes de benefício) com o Whisper medium no áudio externo e no da câmera: se no externo a palavra sair embolada e na câmera clara, mandar um A/B curto e perguntar (no gancho dos descontos ela escolheu o som da câmera tratado). Gravação sem áudio externo correspondente: som da câmera com dereverb + EQ de casamento de timbre (±5 dB) — perguntar antes.
- **Áudio gravado à parte (locução)** (correções de 09/11/2026: "o áudio do vídeo ficou muito ruim… sincronize, não deixe atrasado"; "coloca na velocidade correta"): a locução enviada à parte vira a voz do reel. **A voz fica intacta, exatamente como ela mandou** (correção de 10/11/2026: esticar a voz deixou o áudio "estranho" e embolou palavras) e **só a imagem se ajusta** com `sync_vo.py`, com velocidade entre 0,65× e 1,6× (até 0,5× onde ele fala mais devagar na locução, via `"ritmo"`) (alinhamento som a som/DTW com o som original; vídeo 0,7×–1,75×; jump cut se a boca sair mais de 60 ms). Se a locução usar outras palavras que o vídeo (ex.: "cai para" x "essas 42 horas caem para"), usar `"inicio_no_video"`. **Nunca mostrar ele fechando os olhos, engolindo ou abaixando a cabeça nas pausas da gravação** (correção de 10/11/2026): conferir os quadros no fim de cada trecho e, se aparecer, prender o fim no instante anterior com `"fim_no_video"` (`src_ate`) — a imagem desacelera até quase parar, sem mudar o tempo da voz. Conferir com `conferir_sync.py` (por bloco perto de 0 ms) e **transcrever o áudio final inteiro e comparar palavra por palavra com a locução enviada**: nenhuma palavra repetida, faltando ou embolada, e nenhum silêncio no meio da fala. Legendas e títulos seguem as palavras **da locução**. Termo dito errado e dito certo noutro ponto: emendar e confirmar com o Whisper que não sobrou resto da palavra errada.
- **Locução limpa e harmoniosa** (correção de 10/11/2026: "retire os ruídos e deixe harmonioso"): adeclip (picos estourados do WhatsApp); medir o zumbido nos silêncios da locução e tirar com filtros estreitos (`"zumbido"` no plano; no 6x1: 55,7/114/176/290 Hz); RNNoise cheio; **sem afftdn** (comia palavras curtas como "ou"); presença suave em 3 kHz e agudos amaciados (−1,5 dB em 9 kHz); compressão e **expansor depois da compressão** (pausas −58 dB, ~44 dB abaixo da voz). Silenciar ruído antes da primeira palavra (`"inicio"` no plano): o vídeo começa direto na fala.
- Trilha só se ela pedir num vídeo específico: aí batida leve e discreta, 18–22 dB abaixo da voz, com abaixamento automático quando ela fala.
- Voz isolada e limpa, sempre na frente.
- **Todas as gravações com o mesmo som** (correção de 19/11/2026: "deixe todos os sons parecidos e igualados, a diferença é muito grande"): depois do tratamento, `igualar_voz.py` leva o timbre de todas a um alvo comum (som da câmera abafado ganha brilho leve com aexciter; excesso de agudo do WhatsApp amaciado; corte comum em 8,5 kHz) e o volume da fala ao mesmo nível. Conferir no vídeo final: LUFS por bloco dentro de ±0,5 dB e faixas de timbre dentro de ~3 dB.
- Efeitos sutis: "pop" no título grande, som de teclado na lista digitada.
- **Som da transição:** mistura de dois sons (sopro suave + tom delicado e harmônico), **bem baixo — cerca de 27 dB abaixo do pico da voz** (correção de 09/11/2026: "achei muito alto"), nunca um whoosh seco/grosso (correção de 04/11/2026).
- **Voz mais alta e encorpada** (correção de 19/11/2026: "ajuste o volume e a voz, coloque mais alto"): antes da mixagem, +1,5 dB em 180 Hz, +1,5 dB em 2,8 kHz e compressor suave (`"voz_mix"` no plano); entrega a −9,5 LUFS, pico ≤ −1 dBTP, mesmo volume em todos os blocos (±0,3 dB).
- Entrega a **−10 LUFS ou mais alto** (voz mais alta — correções de 09/11/2026; antes −14, depois −12; no 6x1 com locução, alvo −9 e limitador a −1 dBFS), pico ≤ −1 dBTP. As referências variaram de −8 a −28 LUFS; padronizar.
- Se ela pedir trilha: a batida original da skill (`elementos/audio/sons.py`) ou música de biblioteca licenciada (CapCut ou Instagram). Nunca copiar a faixa das referências nem usar as músicas de exemplo do kit.

## Encerramento (últimos 3–5 s)

- **Sem cartão final de comentários** ("Ficou alguma dúvida?…"): o vídeo termina logo depois da última palavra dela (correção de 04/11/2026).
- Texto de encerramento só se for fala dela. Cartão do perfil ou de logo só quando ela pedir.
- Sem telefone, preço ou promessa.

## Referências analisadas (04/11/2026)

| # | Vídeo | O que levar |
| --- | --- | --- |
| 1 | Engenheira, alvará (externa) | Pergunta no topo como gancho, karaokê por palavra, whip para b-roll, alternância aberto/fechado a cada ~2 s |
| 2 | Arquiteta, regularização (fundo cinza) | Caixa de destaque que pula de palavra em palavra, figurino na paleta, cartão de logo no fim |
| 3 | Advogada, dano moral (estante) | Serifa itálica grande na palavra de impacto, flash P&B→bege, lista digitada com cursor |
| 4 | @alicebelli_adv (tomada única) | Texto empilhado sans + serifa itálica entrando "fantasma"; tomada única segura pelo texto |
| 5 | Escritório, servidor público | Karaokê em 2 linhas, punch-in em rampa, troca de pessoa para cada "direito" |
| 6–7 | Riveros (salário-maternidade, facultativo 5%) | B-roll emocional e cartão do perfil no final |
| 8 | @dantas.advocacia (pensão autistas) | Acabamento, luz no rosto, fundo escuro, documento destacado |

Limitação: não foi possível ouvir as trilhas para dizer gênero ou batida. Só a presença contínua delas e o volume foram medidos.

## Correções

<!-- Formato: - AAAA-MM-DD — regra nova (o que estava errado → como deve ser). -->
- 2026-11-04 — Cartão final "Ficou alguma dúvida? / Deixe aqui nos comentários." tirado: o reel termina na última fala dela.
- 2026-11-04 — Trilha: batida leve e discreta (preferida a piano suave).
- 2026-11-04 — Legenda estava grande e "grosseira" (Anton caixa alta com contorno): agora Montserrat SemiBold, letras normais, ~58 px, só sombra suave.
- 2026-11-04 — Tirar o rótulo "AUXÍLIO-ACIDENTE" em cima da cabeça: nada de selo de tema no topo.
- 2026-11-04 — Transição: film burn singelo nas trocas de assunto (como nas referências), no lugar do flash bege.
- 2026-11-04 — Som da transição estava grosseiro: mistura de dois sons mais harmônica e bem mais baixa.
- 2026-11-04 — Música de fundo retirada ("ficou com ruído e estragou o áudio"): reel sem trilha; só voz + efeitos suaves. Substitui a escolha da batida leve.
- 2026-11-09 — Letras mais grossas: legenda e linhas pequenas dos títulos passam de Montserrat 600 para 700 (lista digitada em 800).
- 2026-11-09 — Áudio "dentro de um banheiro": voz tratada contra zumbido (motor ~57/112 Hz), ruído e eco (expansor suave); a cadeia nova está no render_cut.py.
- 2026-11-09 — Voz mais alta: entrega a −12 LUFS (era −14), limitador a −1,4 dBFS.
- 2026-11-09 — Som da transição estava alto: sopro e tom baixados ~8 dB (≈ 27 dB abaixo da voz); toque e cliques ~3 dB; efeitos entram −6 dB na mixagem.
- 2026-11-09 — Ainda com eco e voz baixa ("deixa como se tivesse gravado por microfone, perto"): eco da sala tirado com WPE + supressão do rabo (dereverb.py), corpo de microfone próximo (+3 dB em 170 Hz), sem afftdn e com expansor bem suave; entrega a −10 LUFS (substitui a regra de −12).
- 2026-11-09 — Som da gravação ruim mesmo tratado: ela mandou locução gravada à parte (WhatsApp). Voz trocada pela locução, imagem sincronizada a ela (sync_vo.py), picos estourados consertados (adeclip). "24 horas" dito por engano na locução foi trocado pelo "42 horas" dito certo no 3º ponto.
- 2026-11-09 — Reel com locução: "reduz os ruídos, aumenta o volume, isola a voz, coloca na velocidade correta, retira o barulho do fundo". Vídeo voltou à velocidade real (a voz se ajusta à boca), pausas silenciosas (expansor depois do compressor), volume mais alto; confirmado que é 42 h (emenda refeita sem sobrar o "vinte").
- 2026-11-10 — Nova locução (WhatsApp) com zumbido de motor/ventilador a 55,7 Hz e harmônicos e ruído antes da primeira palavra: zumbido tirado com filtros estreitos, sem afftdn, agudos amaciados, ruído inicial silenciado. Sincronia: −30 a 0 ms por bloco.
- 2026-11-10 — "Na primeira parte ele fecha os olhos e engole para iniciar a nova fala": fim do trecho "Entenda os três principais pontos" preso a 9,36 s da gravação (ele fecha os olhos a partir de 9,40 s). Regra: conferir o fim de cada trecho quadro a quadro.
- 2026-11-19 — Film burn "excessivamente repetitivo": no máximo um por vídeo, num momento estratégico; nas outras trocas, técnicas variadas (corte seco/match cut, câmera que assenta, dolly lento, véu de opacidade). Aproximações suaves só nos momentos-chave. Substitui "film burn em cada troca de assunto".
- 2026-11-19 — Áudio externo gravado junto com o vídeo (WhatsApp): voz principal, sincronizada pelo som da câmera (erro medido de 0,1 ms no vídeo final). No gancho, o "Trinta reais" ficava embolado no externo: ela escolheu o som da câmera tratado (A/B). Gravação sem áudio externo (o arquivo veio repetido): som da câmera tratado, com aviso.
- 2026-11-19 — Legenda com karaokê + quadros juntos "fica estranho": legenda sem karaokê (só a palavra-chave em caixa bordô) e, quando há quadro de destaque, só o quadro, na altura da legenda (modelo: reel de referência dela).
- 2026-11-19 — "Deixe todos os sons parecidos e igualados": timbre e volume de todas as gravações igualados (igualar_voz.py); blocos com som da câmera estavam 2 dB mais baixos e sem agudos.
- 2026-11-19 — "O enquadramento tá bem estranho, corta um pouco": rosto fixo em ~23%, olhos a 28%, sem alternar planos e sem movimentos de câmera nas transições (o rosto variava de 20% a 25% entre cortes). Substitui a alternância aberto/fechado e os movimentos "assentar"/"dolly".
- 2026-11-19 — "Ajuste o volume e a voz, coloque mais alto, melhore o enquadramento e a iluminação, corte onde ela demora a falar, deixe harmonioso": voz encorpada e a −9,5 LUFS; rosto fixo em ~25%; fundo desfocado e escurecido (MODNet); cortes em pausas ≥ 0,18 s com respiro 0,06/0,15 s; legenda sem palavra solta ("sindicato no benefício do INSS" junto).
- 2026-11-10 — "O áudio tá estranho, não tá sincronizado, tem palavras repetidas, tem horas que fica calado": (1) um trecho de fala compartilhado entre dois blocos entrava duas vezes ("Segundo, segundo") — o sync_vo.py agora divide o trecho; (2) a voz esticada/encolhida embolava palavras ("acordo ou convenção", "ou menos") — voz volta a ficar intacta e só a imagem se ajusta. Conferência obrigatória: transcrição do áudio final x locução, palavra por palavra.
