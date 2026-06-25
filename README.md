# TikTok Live interativa (GMod + Hytale)

O chat e os presentes do TikTok controlam a live: comandos, likes e
presentes spawnaoMonstros, disparam efeitos e reagem em tempo real via
WebSocket no painel do OBS. Funciona tanto no **Garry's Mod** quanto
no **Hytale** — com configs separadas por jogo.

---

## Estrutura do projeto

```
integracao_ttk/
├── shared/               # Python compartilhado pelos dois jogos
│   ├── src/              # código (config, fila, cooldown, listener...)
│   ├── tests/            # testes unitários (pytest)
│   ├── .env              # config ativa (QUEUE_FILE, COMMANDS_FILE)
│   └── requirements.txt
│
├── gmod/                 # tudo exclusivo do Garry's Mod
│   ├── commands.json     # comandos de chat, presentes e metas
│   ├── binds_gmod.cfg    # binds para autoexec.cfg
│   ├── lua/
│   │   └── live_caos_ponte.lua   # addon Lua (copiar para garrysmod/lua/autorun/)
│   └── overlay/
│       ├── painel.html / painel_config.json
│       ├── nuclear.html / ranking.html / toasts.html
│       ├── sons_config.json
│       └── assets/ sons/ gifs/
│
└── hytale/               # tudo exclusivo do Hytale
    ├── plugin/
    │   └── livecaos-hytale/    # projeto Java (compilar com gradlew jar)
    └── overlay/
        ├── painel_hytale.html
        └── commands_hytale.json
```

---

## Pré-requisitos

- Windows com **Python 3.11+**
- OBS / TikTok Live Studio
- **GMod**: Garry's Mod com `lua_run` liberado
- **Hytale**: Hytale instalado (Early Access)

---

## Instalação

```bat
cd shared
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edite o `.env` e preencha `TIKTOK_USERNAME=seu_usuario` (sem @).

---

## Trocar entre GMod e Hytale

No `.env`, mude duas variáveis:

**Para GMod:**
```
COMMANDS_FILE=../gmod/commands.json
QUEUE_FILE=C:/...caminho.../garrysmod/data/live_caos/fila.txt
GAME_WINDOW_TITLE=Garry's Mod
```

**Para Hytale:**
```
COMMANDS_FILE=../hytale/overlay/commands_hytale.json
QUEUE_FILE=C:/Users/.../Hytale/UserData/Saves/<mundo>/livecaos/fila.txt
```
> O `QUEUE_FILE` do Hytale aparece no log do jogo quando você entra no mundo:
> `[LiveCaos] Mundo: <nome> | Fila: C:\...`

---

## GMod — configuração

**Addon Lua:**
Copie `gmod/lua/live_caos_ponte.lua` para `garrysmod/lua/autorun/`.

**Binds de tecla:**
Cole o conteúdo de `gmod/binds_gmod.cfg` no `garrysmod/cfg/autoexec.cfg`.

**Comandos e presentes:**
Edite `gmod/commands.json` — gatilho, teclas, cooldowns e rótulo do painel.

**Overlay:**
```bat
cd gmod/overlay
python -m http.server 8080
```
Adicione no OBS/Live Studio: `http://localhost:8080/painel.html`

---

## Hytale — configuração

**Plugin Java:**
```bat
cd hytale/plugin/livecaos-hytale
.\gradlew.bat jar
copy build\libs\livecaos-hytale-1.0.0.jar %APPDATA%\Hytale\UserData\Mods\
```
Reinicie o Hytale e entre no mundo. O plugin cria automaticamente a pasta
`livecaos/` dentro do save ativo com o `mobs.json` e `fila.txt`.

**Mobs por evento:**
Edite `Saves/<mundo>/livecaos/mobs.json` — evento, role do Hytale, quantidade.
Não precisa recompilar para mudar mobs ou quantidades.

**Presentes e comandos:**
Edite `hytale/overlay/commands_hytale.json` — gift_name, file, label, cooldowns.
O campo `file` deve ser idêntico ao `evento` no `mobs.json`.

**Overlay:**
```bat
cd hytale/overlay
python -m http.server 8081
```
Adicione no OBS: `http://localhost:8081/painel_hytale.html`

---

## Rodar o Python

```bat
cd shared
.venv\Scripts\activate
python -m src.main
```

**Modo simulação** (testar sem live):
No `.env`, mude `SIMULATION=true`.

---

## Logs

Cada sessão grava em `shared/logs/live_AAAA-MM-DD.log`.

---

## Testes

```bat
cd shared
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```
