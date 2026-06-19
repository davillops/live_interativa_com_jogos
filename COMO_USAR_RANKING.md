# Painel de Ranking — Como usar

## O que e
Um placar que gamifica a live. Mostra Top 5 e alterna sozinho entre:
- **Live**: pontos desde que o script ligou (zera ao reiniciar)
- **Geral**: histórico de todas as lives (salvo em SQLite)

Troca de modo a cada 30 segundos automaticamente.

## Pontos por acao (presentes valem mais)
- Comentário/comando no chat: 1 ponto
- Entrar na live: 5 pontos
- Seguir: 25 pontos
- Presente: pontos = valor em diamantes do presente

## Como por no Live Studio / OBS
1. Adicione uma fonte de **Navegador (Browser)**
2. URL: `http://localhost:8080/ranking.html`
3. Tamanho sugerido: ~360 de largura, altura conforme o Top 5
4. Posicione onde quiser (canto superior, lateral...)

## Configuracao (.env)
- `RANKING_ENABLED=true` liga/desliga o sistema
- `RANKING_DB=live_caos.db` nome do arquivo do banco

## Onde fica o histórico
No arquivo `live_caos.db` (na pasta do projeto). E um banco SQLite.
Para ZERAR o histórico, apague esse arquivo (cuidado: nao tem volta).

## Ajustar os pontos
No arquivo `src/ranking.py`, na classe PontosConfig:
- chat, follow, join: valores fixos
- gift_multiplier: multiplica os diamantes (1 = valor cheio)
