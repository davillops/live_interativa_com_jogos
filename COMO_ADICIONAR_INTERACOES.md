# Guia: adicionar e remover interações (sem mexer no código)

Toda interação vive em **3 lugares**. Decorou isso, nunca mais precisa
de programador:

| # | Arquivo | O que controla |
|---|---------|----------------|
| 1 | `garrysmod/cfg/autoexec.cfg` | O que acontece **no jogo** (bind + lua_run) |
| 2 | `commands.json` | O que o **Python** escuta e qual tecla aperta |
| 3 | `overlay/painel_config.json` | O que aparece **no painel** da live |

Depois de editar: reinicie o script Python (Ctrl+C e rodar de novo) e
recarregue a fonte do painel no Live Studio (ou F5 no navegador).
No GMod, rode `exec autoexec` no console para recarregar os binds.

---

## Receita 1 — Novo COMANDO DE CHAT (ex: !meteoro na tecla F4)

**Passo 1 — GMod** (`autoexec.cfg`): crie o bind

```
bind "f4" "lua_run <seu codigo lua aqui>"
```

⚠️ Nunca use `;` dentro do lua_run (o console corta ali). Em Lua,
espaço entre comandos basta.

**Passo 2 — Python** (`commands.json`): copie um bloco dentro de
`"commands": [...]`, cole antes do `]` e ajuste:

```json
    {
      "trigger": "!meteoro",
      "keys": ["f4"],
      "label": "Chuva de Meteoro",
      "emoji": "☄️",
      "cooldown_global": 15,
      "cooldown_user": 45
    }
```

⚠️ Não esqueça a **vírgula** entre um bloco `}` e o próximo `{`.

**Passo 3 — Painel** (`overlay/painel_config.json`): copie uma linha
dentro de `"itens"` da seção "Interações grátis":

```json
        { "id": "!meteoro", "emoji": "☄️", "gatilho": "!meteoro", "efeito": "Chuva de Meteoro", "cooldown": true }
```

O `"id"` DEVE ser igual ao `"trigger"` — é o que faz o flash e a
barra de cooldown acenderem na linha certa.

---

## Receita 2 — Novo PRESENTE executado pelo PYTHON
*(exemplo real: Controle de videogame → bomba 1000lb na F3)*

**Passo 1 — GMod**: o bind já existe (`bind "f3" "lua_run ..."`).

**Passo 2 — Python** (`commands.json`), dentro de `"gifts": [...]`:

```json
    {
      "gift_name": "Controle de videogame",
      "keys": ["f3"],
      "label": "Bomba 1000lb",
      "emoji": "🎮"
    }
```

- `gift_name` deve ser o nome do presente **como aparece no TikTok**
  (maiúsculas/minúsculas não importam, espaços nas pontas também não).
- Presentes **nunca têm cooldown** (quem pagou, ganha) — só respeitam
  o ritmo da fila.
- ⚠️ Não cadastre aqui presentes que o **Tikfinity** já executa
  (Rosa, Urso Misha) — senão a ação dispara DUAS vezes.

**Passo 3 — Painel** (`painel_config.json`), seção "Presentes":

```json
        { "id": "controle de videogame", "emoji": "🎮", "gatilho": "Controle", "efeito": "Bomba 1000lb" }
```

Para presente, o `"id"` é o `gift_name` em **minúsculas**.

---

## Receita 3 — Interação que SÓ o Tikfinity executa
*(likes, follow, presentes configurados lá)*

O Python não participa — você só mostra no painel:

1. Configure a ação no **Tikfinity** (tecla, etc.)
2. Crie o bind correspondente no `autoexec.cfg`
3. Adicione a linha no `painel_config.json` (sem `"cooldown"`)

Nada de `commands.json` nesse caso.

---

## Receita 4 — REMOVER uma interação

Faça o caminho inverso, nos 3 arquivos:

1. `painel_config.json`: apague a linha `{ ... }` do item
   (cuidado com a vírgula sobrando no item anterior)
2. `commands.json`: apague o bloco do comando/presente
3. `autoexec.cfg`: apague o bind, ou rode `unbind f4` no console

Se quiser só **pausar** uma interação (ex: comando muito spammado),
basta remover do `commands.json` — o painel pode continuar mostrando
ou não, você decide.

---

## Receita 5 — Ajustes rápidos

| Quero... | Onde mexer |
|---|---|
| Mudar cooldown de um comando | `commands.json` → `cooldown_global` / `cooldown_user` |
| Trocar emoji por imagem no painel | `painel_config.json` → troque `"emoji": "🛢️"` por `"img": "assets/barril.png"` (coloque o PNG em `overlay/assets/`) |
| Mudar o texto que aparece no toast | `commands.json` → `label` e `emoji` |
| Mudar nome/efeito exibido no painel | `painel_config.json` → `gatilho` / `efeito` |
| Mudar ritmo da fila | `.env` → `MIN_INTERVAL_SECONDS` |
| Mudar meta de likes | `.env` → `LIKES_GOAL` (e no Tikfinity!) |
| Criar nova seção no painel | `painel_config.json` → copie um bloco de `"secoes"` |

---

## Checklist de teste (2 minutos, sem abrir live)

1. No `.env`: `SIMULATION=true`
2. Rode `python -m src.main` — se o JSON tiver erro de digitação,
   o log avisa na hora (procure por `CommandsFileError`)
3. Abra o painel e os toasts no navegador — confira a linha nova
4. Para testar o comando de verdade: deixe o GMod aberto e em foco;
   ou digite o comando você mesmo no chat da sua live
5. Volte `SIMULATION=false` antes da live de verdade
