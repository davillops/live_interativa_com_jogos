# Live Caos — TikTok Live interativa no Garry's Mod

O chat controla a live: comandos como `!barril` e `!cura` viram teclas no
GMod, com fila, cooldowns e um painel (overlay) que reage em tempo real
via WebSocket. Likes, follows e presentes são executados pelo **Tikfinity**;
o Python apenas exibe esses eventos no painel.

## Divisão de responsabilidades

| Evento | Quem executa | Tecla |
|---|---|---|
| `!drop`, `!barril`, `!cura`, `!formiga`, `!barco` | **Python** | ver `commands.json` |
| 5 likes → zumbi | python | F9 |
| Seguir → fogo | python | F10 |
| Urso Misha → FNAF Nextbot | Tikfinity | F11 |
| Rosa → galinha explosiva | Tikfinity | Ctrl+3 |

## Pré-requisitos

- Windows com **Python 3.11+** (https://python.org — marque "Add to PATH")
- Garry's Mod com `lua_run` liberado (jogo local)
- OBS / TikTok Live Studio

## Instalação (PC novo)

```bat
cd live_caos
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edite o `.env` e preencha `TIKTOK_USERNAME=seu_usuario` (sem @).

## Configurar o GMod

**Ponte por arquivo (zumbi com nome, sem abrir console):**
copie `gmod_lua/live_caos_ponte.lua` para `garrysmod/lua/autorun/`,
troque os placeholders de classname e ajuste `QUEUE_FILE` no `.env`.
Veja o passo a passo em `GUIA_PONTE_ARQUIVO.md`.

**Binds de tecla (comandos de chat):**
cole o conteúdo de `binds_gmod.cfg` no `garrysmod/cfg/autoexec.cfg`.

⚠️ **Combos com Ctrl**: o Source não suporta `bind "ctrl+1"` nativamente.
Se `!formiga`/`!barco` não dispararem no jogo, troque por teclas simples
(F4, F5...) no `autoexec.cfg` **e** no `commands.json` (`"keys": ["f4"]`).

⚠️ **Tecla `+` do barril**: o bind `"="` corresponde à tecla `=`/`+` da
fileira superior. Se não funcionar, teste `"keys": ["add"]` no
`commands.json` (tecla + do numpad) e `bind "kp_plus"` no GMod.

## Configurar o overlay

**TikTok Live Studio** (usa fonte "Link", que exige URL):

1. Dê dois cliques em `abrir_overlay.bat` (deixe a janela aberta)
2. No Live Studio: **Fontes → + Adicionar fonte → Link**
3. Cole `http://localhost:8080/painel.html`
4. Posicione na lateral do layout vertical

**OBS** (aceita arquivo local direto):

1. **Fonte → Navegador (Browser Source)**
2. Marque "Arquivo local" e aponte para `overlay/painel.html`
3. Largura 520 / Altura 900 (ajuste à vontade)

O painel funciona mesmo com o script desligado (fica estático) e
reconecta sozinho a cada 5s quando o script subir.

## Rodar

```bat
.venv\Scripts\activate
python -m src.main
```

### Testar sem live no ar (modo simulação)

No `.env`, mude `SIMULATION=true` e rode normalmente. O sistema gera
chat/likes/follows/presentes falsos — perfeito para validar painel,
fila e teclas antes de abrir a live. **Importante**: as teclas são
pressionadas de verdade; deixe o GMod em foco (ou um bloco de notas
para ver as teclas chegando).

## Ajustar comandos e cooldowns

Tudo em `commands.json` — gatilho, teclas, cooldowns e rótulo do
painel. Não precisa mexer em código. Campos:

- `cooldown_global`: segundos até QUALQUER pessoa usar de novo
- `cooldown_user`: segundos até o MESMO viewer repetir
- `keys`: `["f7"]` tecla simples, `["ctrl", "1"]` combo

## Estrutura

```
live_caos/
├── src/                  # código (config, fila, cooldown, executor, listener...)
├── tests/                # testes unitários (pytest)
├── overlay/painel.html   # overlay para Browser Source
├── overlay/assets/       # fundo.png + ícones
├── commands.json         # mapeamento comando → tecla → cooldown
├── binds_gmod.cfg        # binds prontos p/ autoexec.cfg
├── .env.example          # modelo de configuração
└── requirements.txt
```

## Logs

Cada sessão grava em `logs/live_AAAA-MM-DD.log`: comandos recebidos,
executados e descartados por cooldown — útil para auditar a live.

## Testes

```bat
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```
