# Troca manual para a VPS4 (sem a máquina principal)

Use quando a máquina principal estiver fora do ar. A VPS4 (62.238.25.84) funciona sozinha: coleta o TSE a partir
das 17h de Brasília, calcula a projeção e serve os sites. Ela não depende da máquina principal.

Reserva sempre no ar: https://eleicoes2026.inema.club e https://municipios2026.inema.club

## Ir para a VPS4 (painel do Cloudflare, zona inema.club)

1. **Workers & Pages → `eleicoes2026` → Settings → Domains & Routes** → remover `eleicoes.inema.club`.
2. **DNS → Add record**: tipo `CNAME`, nome `eleicoes`, destino `eleicoes2026.inema.club`, proxy LIGADO (nuvem laranja).
3. **Workers & Pages → `eleicoes2026-municipios` → Settings → Domains & Routes** → remover `municipios.inema.club`.
4. **DNS → Add record**: tipo `CNAME`, nome `municipios`, destino `municipios2026.inema.club`, proxy LIGADO.
5. Testar em aba anônima. Na VPS4 o número de acessos do menu some.

Se a máquina principal ainda estiver ligada, antes do passo 1:
`systemctl --user stop eleicoes-publicar eleicoes-municipios-publicar`
(senão ela prende o domínio de volta no Worker no próximo envio).

## Voltar ao Cloudflare

1. **DNS**: apagar os CNAME `eleicoes` e `municipios`.
2. Na máquina principal: `systemctl --user start eleicoes-publicar eleicoes-municipios-publicar`
   (no próximo envio eles prendem os domínios nos Workers de novo).

## Com a máquina principal no ar, um comando faz tudo

`ferramentas/vps/trocar_dominios.sh` (sem argumento mostra os comandos):
`status`, `vps --executar`, `volta --executar`. Usa o login do wrangler e o token de DNS que só existem
na máquina principal; em outra máquina, exporte `CF_TOKEN` com Workers Scripts:Edit e DNS:Edit.

## Conferir a VPS4

`ssh root@62.238.25.84 'systemctl is-active nginx eleicoes-coletor eleicoes-municipios eleicoes-projecao'`
(activating antes das 17h = esperando a abertura).
