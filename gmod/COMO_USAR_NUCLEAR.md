# Barra Nuclear — Como usar

## O que e
Uma SEGUNDA barra de likes (separada do zumbi). Enche conforme o chat
da likes; ao bater a meta (padrao 1000), uma BOMBA NUCLEAR explode na
frente do personagem no GMod. Tem giroflex piscando e sirene quando
passa de 80% (clima de tensao antes do estouro).

## Configurar
1. .env: `NUCLEAR_GOAL=1000` (quantos likes para encher)
2. live_caos_ponte.lua: troque `COLE_O_ID_DA_NUCLEAR` pelo classname da
   sua bomba nuclear
3. Desative no Tikfinity qualquer meta de like que dispare isso (senao duplica)

## No Live Studio / OBS
- Nova fonte de Navegador: `http://localhost:8080/nuclear.html`
- Tamanho sugerido: ~380 de largura, ~130 de altura
- Para a SIRENE: marque "Controlar audio via OBS" na fonte
- Coloque o arquivo de som em `overlay/sons/sirene.mp3`

## Ajustes
- Limiar do alerta (giroflex/sirene): variavel LIMIAR_ALERTA no nuclear.html
  (0.8 = liga a 80%)
