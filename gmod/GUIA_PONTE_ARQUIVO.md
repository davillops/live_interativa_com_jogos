# Ponte por arquivo — sem console, sem roubar foco

A meta de likes (zumbi) e qualquer evento com nome do doador agora usam
a **ponte por arquivo**: o Python escreve numa fila de texto e o addon
Lua lê e executa de dentro do jogo. Nada abre na tela, seu input nunca
trava, e aguenta muitos likes seguidos.

## Como ligar (uma vez)

1. **Addon no GMod**: copie `gmod_lua/live_caos_ponte.lua` para
   `garrysmod/lua/autorun/`. Ele cria a pasta `data/live_caos/` sozinho
   na primeira execução.

2. **Troque os placeholders** no `live_caos_ponte.lua`:
   - `COLE_O_ID_DO_FNAF` → classname do seu nextbot FNAF
   - `COLE_O_ID_DA_GALINHA` → classname da galinha explosiva
   (o zumbi já está com a sua lista de 4 monstros)

3. **Caminho da fila no `.env`** (`QUEUE_FILE`): aponte para o
   `fila.txt` dentro da SUA instalação do GMod. O padrão é:
   ```
   QUEUE_FILE=C:/Program Files (x86)/Steam/steamapps/common/GarrysMod/garrysmod/data/live_caos/fila.txt
   ```
   Se seu Steam está em outro drive (ex: `D:`), ajuste. Use barras `/`.

   👉 Como achar: no GMod, console → `path` mostra as pastas; ou procure
   a pasta `GarrysMod` dentro de `steamapps/common`. O arquivo
   `data/live_caos/fila.txt` aparece após rodar o addon a primeira vez.

4. **Tikfinity**: desative a ação de likes (F11) — agora é o Python que
   spawna o zumbi. Senão nasce duplicado.

## Como funciona (pra você entender)

- O Python escreve linhas `evento|nome` no `fila.txt` (ex: `zumbi|joao`).
- O addon lê a cada 0,3s, limpa o arquivo e executa cada linha.
- Para o nome flutuar, o Lua marca a entidade com `SetNWString` e
  desenha o texto no `HUDPaint` (só sobre quem tem nome, some a 2500u).

## Adicionar evento novo na ponte

**Lado Lua** (`live_caos_ponte.lua`): adicione uma função na tabela
`EVENTOS`. A chave é o nome do evento:

```lua
["meteoro"] = function(nome, dono)
    -- seu código de spawn aqui; use 'dono' como referência de posição
    -- e:SetNWString("doador", nome) se quiser o nome flutuando
end,
```

**Lado Python** (`commands.json`): use `"file"` com esse nome:

```json
{ "gift_name": "Foguete", "file": "meteoro", "label": "Meteoro", "emoji": "☄️" }
```

Funciona em `commands`, `gifts` e `likes_meta`. O nome do doador é
passado automaticamente (já limpo de caracteres perigosos).

## Os 3 modos de ação (resumo)

| Modo | Como | Abre na tela? | Passa nome? | Quando usar |
|------|------|---------------|-------------|-------------|
| `file` | escreve na fila do addon | Não ✅ | Sim ✅ | **Padrão** — tudo, especialmente com nome |
| `keys` | aperta tecla (bind) | Não | Não | Comandos simples que já funcionam por bind |
| `console` | digita no console | Sim 😕 | Sim | Evite; só se não der pra fazer no Lua |

Você pode migrar os comandos de chat (`!barril` etc.) das teclas para a
ponte quando quiser: descomente os exemplos no fim da tabela `EVENTOS`
do `live_caos_ponte.lua` e troque `"keys"` por `"file"` no
`commands.json`. Aí nem precisa mais dos binds no autoexec.
