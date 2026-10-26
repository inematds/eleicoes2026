# Como o INEMA Eleições 2026 foi construído — e por que aguenta milhões de pessoas

**🌐 Página com esta explicação (PT/EN/ES):** https://inematds.github.io/eleicoes2026/guia/arquitetura/

## Em resumo

O painel eleicoes.inema.club mostrou a apuração do 2º turno de 2026 ao vivo, com os dados oficiais do TSE, e
depois ganhou análises e um chat. O desenho é simples: **um único coletor** lê o TSE e grava arquivos prontos;
esses arquivos ficam **na borda do Cloudflare** (os servidores dele espalhados pelo mundo); o navegador de cada
visitante só lê esses arquivos. Nenhum servidor nosso fica no caminho do visitante. Por isso o número de pessoas
olhando não muda a carga do TSE nem da nossa máquina. Uma VPS de reserva estava pronta para assumir em
minutos e, desde 26/10, é ela que roda tudo.

Marcação usada aqui: **FATO** = medido ou conferido no projeto (com a fonte); **ESTIMATIVA** = conta feita a
partir de fatos, não medida em produção.

---

## 1. Linha do tempo (FATO, pelo `git log`)

| Quando | O que entrou |
|---|---|
| 24/10 madrugada | Verificação dos arquivos públicos do TSE e decisão de arquitetura (`ANALISE.md`) |
| 24/10 04:19 | 1º commit: coletor + contrato + painel com dados reais do 1º turno |
| 24/10 05:50 | Sistema de municípios (5.571 cidades no mapa), separado do painel |
| 24/10 14:00 | Contador de acessos (Worker + Durable Object) |
| 25/10 00:20–03:01 | Compartilhar, Fonte e auditoria, Projeção INEMA (calibrada em 224 cenários: dados de 2022 e simulações) |
| 25/10 03:06–03:44 | Reserva na VPS4, troca de domínios por script e manual de troca |
| 25/10 09:05 | Exterior país a país pelos boletins de urna |
| 25/10 17:00 | TSE abre a divulgação: coletores ligam sozinhos (timer) |
| 25/10 17:24–22:47 | 10 commits **durante** a apuração: correções (hora do exterior, fusos, cidades presas) e menus novos (Análise, Raio-X, Conferência, Por que perdeu) |
| 26/10 | A virada, chat "Tire suas dúvidas", operação inteira movida para a VPS4 |

Da primeira linha de código ao painel ao vivo foram **cerca de 37 horas de relógio** (com noite de sono no
meio), feitas em sessões com o Claude Code. O repositório tem mais de 45 commits; cada falha corrigida virou uma
linha em `FALHAS.md`.

## 2. A arquitetura em uma figura

```
TSE (resultados.tse.jus.br)
   │  1 coletor: a cada 15 s pede o índice com ETag (sem novidade = 304, quase nada trafega)
   ▼
Coletor + conferência  (Python, systemd)            ← único ponto que fala com o TSE
   │  guarda o bruto + sha256 · confere as contas · recusa número que "volta"
   ▼
Arquivos versionados   data/uf/sp/v100123.json  (imutáveis, nunca mudam)
                       data/latest.json         (manifesto, 4,9 KB, gravado por último)
   │  publicador: quando a assinatura dos dados muda → wrangler deploy
   ▼
Cloudflare (Workers Static Assets, na borda)        ← quem atende o visitante
   │  arquivo estático: servido direto da borda, sem rodar código
   │  /api/acessos e /api/chat: único trecho que roda código (Worker)
   ▼
Navegador: lê latest.json a cada 15 s e baixa só o arquivo da versão nova
```

Três partes que só conversam por arquivos JSON (o **contrato**, `contrato/README.md`):

| Parte | Pasta | Sabe do TSE? | Sabe de tela? |
|---|---|---|---|
| Dados | `coleta/`, `municipios/coletor_mun.py`, `analise/`, `projecao/` | sim | não |
| Contrato | `contrato/` | — | — |
| Apresentação | `site/`, `municipios/site/` | **não** | sim |

A coleta pode cair, trocar de máquina ou ser reescrita sem mexer no site, desde que mantenha o contrato. Foi
exatamente o que aconteceu na mudança para a VPS4.

## 3. Por que aguenta milhões sem derrubar servidor

1. **Nenhum servidor nosso atende visitante.** Quem responde é a borda do Cloudflare. A nossa máquina só
   *empurra* arquivos quando algo muda. Se ela cair, o site continua no ar com o último resultado. (FATO: na troca
   para a VPS4 o site não saiu do ar.)
2. **O TSE vê um único cliente.** Mil ou um milhão de visitantes, o coletor faz o mesmo pedido a cada 15 s, com
   ETag: se nada mudou, a resposta é um 304 vazio. (FATO: `coleta/coletor.py`.)
3. **Arquivo que nunca muda é cacheado para sempre.** Cada versão tem nome próprio (`v100340.json`) e cabeçalho
   `immutable` de 1 ano (`ferramentas/publicar_cf.py`). O navegador baixa uma vez e guarda.
4. **Só um arquivo pequeno é consultado sempre.** O `latest.json` tem 4,9 KB e diz qual versão é a atual. O
   navegador só busca o arquivo grande quando a versão muda.
5. **Arquivo estático não roda código.** No Cloudflare Workers Static Assets, pedido de arquivo estático é
   servido sem acionar o Worker; segundo a documentação do Cloudflare, esses pedidos não são cobrados nem
   limitados. Só `/api/acessos` e `/api/chat` rodam código.
6. **Manifesto por último.** O coletor grava os arquivos de versão antes do `latest.json`; o envio ao Cloudflare leva tudo junto,
   de uma vez. Ninguém vê manifesto apontando para arquivo que ainda não existe.

**A conta (ESTIMATIVA, a partir do polling de 15 s e do `latest.json` de 4,9 KB):**

| Pessoas com o painel aberto ao mesmo tempo | Pedidos/s na borda (latest.json) | Tráfego | Pedidos ao TSE | Carga na nossa máquina |
|---|---|---|---|---|
| 10 mil | ~670 | ~3 MB/s | 1 a cada 15 s | nenhuma |
| 100 mil | ~6.700 | ~33 MB/s | 1 a cada 15 s | nenhuma |
| 1 milhão | ~67.000 | ~330 MB/s | 1 a cada 15 s | nenhuma |

Somam-se os arquivos de versão nova (poucos KB, uma vez por mudança, e servidos do cache). Nada disso foi testado
com 1 milhão de pessoas reais; é a conta de quanto a borda precisa entregar. Público medido: 4.866 sessões no
contador do painel até 26/10 (FATO, `/api/acessos`).

## 4. Onde estão os limites de verdade

- **Contador de acessos.** É uma única instância de Durable Object (`ferramentas/cloudflare/contador.js`). Com
  milhões de sessões chegando juntas, vira gargalo. Se falhar, só o número some do menu; o painel não depende
  dele. Para escala real: dividir o contador em várias instâncias e somar.
- **Chamadas de Worker** (`/api/*`) são cobradas por volume acima da franquia do plano do Cloudflare. O painel
  faz 1 por sessão (contador) e o chat 1 por pergunta.
- **Chat.** Cada pergunta chama a API da Anthropic (Claude Opus 5.5). Medido nas primeiras conversas (FATO,
  `saida/chat/conversas.jsonl`): cerca de US$ 0,04 por pergunta, com 122 mil tokens de contexto lidos do cache.
  Teto contra abuso: 25 perguntas/hora e 80/dia por visitante, 1.500/dia no site.
- **TSE.** Se o TSE atrasa ou manda arquivo inconsistente, o coletor segura aquele estado e mantém o último
  válido. Não dá para ser mais rápido que a fonte.
- **Publicação.** Cada mudança vira um `wrangler deploy` de 18 a 26 s (FATO, log do publicador). Somado ao
  intervalo de 15 s da coleta, o site fica cerca de meio minuto atrás do TSE (ESTIMATIVA).

## 5. Custos

| Item | Custo | Tipo |
|---|---|---|
| Coletor, análises, publicador | máquina que já existia; hoje a VPS4 (Hetzner CX23, 2 vCPU, 4 GB, Helsinque) | FATO (máquina); preço: ESTIMATIVA de poucos euros por mês |
| Site e dados (arquivos estáticos na borda) | sem cobrança por pedido nos Workers Static Assets | FATO (documentação do Cloudflare) |
| Contador e chat (Worker + Durable Object) | dentro da franquia do plano em volume baixo; cobrado por volume acima dela | ESTIMATIVA (depende do plano da conta) |
| Chat (API da Anthropic) | ~US$ 0,04 por pergunta no Opus 5.5; ~US$ 1 cada vez que o contexto é regravado no cache | FATO medido nas primeiras conversas |
| Dados do TSE | gratuitos e públicos, sem chave | FATO |

O custo **não cresce com o número de visitantes** na parte do painel. Só cresce com o uso do chat (limitado
pelos tetos acima) e com chamadas de Worker acima da franquia.

## 6. Backup: a VPS de reserva e a troca em um comando

**Durante a apuração (25/10):**

- A VPS4 tinha **coletores próprios**, ligados às 17h, gravando versões a partir de **500001** — de propósito, para
  nunca colidir com os arquivos imutáveis já publicados pela máquina principal (série 100001).
- nginx na VPS servia cópias completas dos dois sites em `eleicoes2026.inema.club` e `municipios2026.inema.club`,
  com os mesmos cabeçalhos de cache. A reserva estava sempre no ar, testável a qualquer momento.
- **Troca por script:** `ferramentas/vps/trocar_dominios.sh vps --executar` soltava os domínios dos Workers e
  apontava `eleicoes.inema.club` e `municipios.inema.club` para a VPS (CNAME com proxy do Cloudflare);
  `volta --executar` desfazia; sem `--executar` só mostrava o que faria.
- **Troca manual:** `ferramentas/vps/TROCA-MANUAL.md` explica a mesma troca pelo painel do Cloudflare, para o
  caso de a máquina principal estar fora do ar.
- Instalação da reserva com um comando: `ferramentas/vps/instalar.sh vps`.

**Desde 26/10 a VPS4 é a principal:** os dados finais foram copiados daqui para lá (583 MB), as análises rodam lá
com resultado idêntico (conferido pelo sha256 do contexto do chat), os publicadores enviam ao Cloudflare de lá, e
a máquina principal foi desligada. Reinstalar a operação inteira:

```bash
ssh root@<IP-DA-VPS> 'cd /opt/eleicoes2026 && git pull && bash ferramentas/vps/operacao.sh --executar'
```

## 7. Técnicas que deram a eficiência

1. **Contrato primeiro.** O formato dos JSON foi escrito antes do código; coleta e site andaram em paralelo.
2. **Separar quem coleta de quem mostra.** O site nunca fala com o TSE; a coleta não sabe de tela.
3. **Arquivo imutável + manifesto pequeno.** Cache eterno no que não muda, consulta barata no que muda.
4. **ETag no TSE.** Pergunta "mudou?" em vez de baixar tudo; baixa só o estado que mudou.
5. **Conferir antes de publicar.** Soma que não fecha, seção ou voto que diminui, hora que volta: aquele estado
   não é publicado e o último válido fica no ar (`contrato/README.md`). Correção legítima do TSE passa com
   `touch saida/oficial/aceitar/<abr>`.
6. **Guardar o bruto com sha256.** Todo arquivo baixado do TSE fica guardado; a página Conferência refaz as
   somas e confere a integridade.
7. **Gravação atômica** (arquivo temporário + `rename`, permissão 644). Ninguém lê arquivo pela metade.
8. **Publicador por assinatura.** Ele calcula um hash dos dados e só publica quando muda; reinício não duplica.
9. **systemd com tetos.** `Restart=always`, `MemoryMax`, timers para ligar às 17h e desligar as simulações às 16h,
   valendo mesmo se a máquina reiniciar.
10. **Ensaiar a noite.** Simulação acelerada com nomes fictícios e um "TSE falso" com falhas de propósito (índice
    antes do arquivo, Brasil atrasado, estado corrompido, número diminuindo).
11. **Testar o modelo com dado real antigo.** A Projeção foi calibrada com dados de 2022 e simulações: em 224 cenários a faixa
    conteve o resultado final em 98,7% (medido na mesma amostra que ajudou a definir a faixa: não é garantia).
12. **Reserva quente e versionada à parte.** A VPS rodava de verdade a noite toda, com outra série de versões.
13. **Contexto do chat determinístico.** Sem carimbo de hora, o texto só muda quando os dados mudam e o cache de
    prompt da API vale (a hora da conferência mudava a cada 5 minutos e derrubava o cache — corrigido em 26/10).
14. **Registro de falhas em uma linha** (`FALHAS.md`): o que quebrou, a menor correção, se foi prompt ou infra.
    Exemplos da noite: o índice do TSE trazia o Brasil com a hora do exterior (~16 h no futuro) e o total não
    publicava; a hora de AC/AM/RR/RO/MT/MS vinha no fuso local; o nginx da reserva não lia arquivo gravado com
    permissão 600.

## 8. Onde ler mais

- `README.md` — o processo passo a passo e os comandos.
- `ANALISE.md` — a análise inicial do TSE e as decisões (o plano previa R2 + Pages; foi feito com Workers
  Static Assets, mais simples: um só envio leva site e dados).
- `contrato/README.md` — formato dos arquivos e regras de bloqueio.
- `ferramentas/vps/` — instalação da reserva, operação atual, troca de domínios.
- `FALHAS.md` — tudo o que quebrou e como foi corrigido.
