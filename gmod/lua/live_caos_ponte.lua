-- =====================================================================
--  PONTE LIVE CAOS  (pasta: garrysmod/lua/autorun/)
--
--  Le a fila escrita pelo Python e executa os eventos SEM abrir console
--  e SEM roubar o foco do jogo. Cada linha do arquivo tem o formato:
--      evento|nome
--  Ex:  zumbi|joao_gamer
--
--  O arquivo fica em:  garrysmod/data/live_caos/fila.txt
--  (o Python escreve nesse mesmo caminho)
--
--  COMO ADICIONAR UM EVENTO NOVO:
--    1. Adicione uma funcao na tabela EVENTOS abaixo (a chave e o nome
--       do evento que o Python manda no commands.json em "file").
--    2. So isso. Nao precisa mexer em mais nada do lado do jogo.
-- =====================================================================

-- A FILA so e processada no servidor/host. Em vez de "return" (que
-- mataria a parte CLIENT do desenho de nomes mais abaixo), envolvemos
-- toda a logica de servidor neste if. Assim o arquivo continua ate o
-- bloco CLIENT no final.
if SERVER then

local CAMINHO = "live_caos/fila.txt"   -- relativo a garrysmod/data/
local INTERVALO = 0.3                  -- segundos entre leituras da fila

-- ---------- Helpers de spawn ----------

-- Spawna uma entidade perto do jogador host e devolve a entidade
local function spawnPerto(classe, dono)
    local origem = IsValid(dono) and dono:GetPos() or Vector(0, 0, 0)
    local areas = navmesh.Find(origem, 600, 120, 120)
    if #areas == 0 then return nil end
    local e = ents.Create(classe)
    if not IsValid(e) then return nil end
    e:SetPos(areas[math.random(#areas)]:GetCenter())
    e:Spawn()
    e:Activate()
    return e
end

-- Spawna uma entidade BEM NA FRENTE do jogador, no campo de visao dele.
-- Usado para o espectador que entra na live ver que apareceu no jogo.
local function spawnNaFrente(classe, dono, distancia)
    if not IsValid(dono) then return nil end
    distancia = distancia or 150

    -- direcao para onde o jogador olha, so no plano horizontal
    -- (zera a inclinacao para nao nascer no teto/chao)
    local olhar = dono:EyeAngles()
    olhar.pitch = 0
    olhar.roll = 0
    local frente = olhar:Forward()

    local origem = dono:GetPos() + Vector(0, 0, 40)
    local alvo = origem + frente * distancia

    -- trace para nao atravessar parede
    local tr = util.TraceLine({
        start = origem, endpos = alvo, filter = dono, mask = MASK_SOLID,
    })
    local destino = tr.Hit and (tr.HitPos - frente * 30) or alvo

    -- baixa ate o chao para nascer em pe no piso
    local chao = util.TraceLine({
        start = destino + Vector(0, 0, 20),
        endpos = destino - Vector(0, 0, 300),
        filter = dono, mask = MASK_SOLID,
    })
    if chao.Hit then destino = chao.HitPos end

    local e = ents.Create(classe)
    if not IsValid(e) then return nil end
    e:SetPos(destino)
    -- vira o personagem de frente para o jogador
    local paraJogador = (dono:GetPos() - destino)
    paraJogador.z = 0
    e:SetAngles(paraJogador:Angle())
    e:Spawn()
    e:Activate()
    return e
end

-- ---------- TABELA DE EVENTOS ----------
-- Cada funcao recebe (nome, dono) onde:
--   nome = nome do doador (string, pode ser "")
--   dono = o jogador host (Player) para usar como referencia de posicao
local EVENTOS = {

    -- Zumbi com o nome do doador flutuando em cima
    ["zumbi"] = function(nome, dono)
        local lista = {
            "drg_codz_iw_spaceland",
            "drg_codz_nova_crawler",
            "drg_codz_bo6_liberty",
            "drg_codz_bo3_origins_templar",
        }
        local e = spawnPerto(lista[math.random(#lista)], dono)
        if IsValid(e) and nome ~= "" then
            e:SetNWString("doador", nome)
        end
    end,

    -- Galinha explosiva com o nome do doador (presente Rosa)
    -- Ja explode sozinha; so spawnamos perto do jogador.
    ["galinha"] = function(nome, dono)
        local e = spawnPerto("npc_vj_mili_chicleet", dono)
        if IsValid(e) and nome ~= "" then
            e:SetNWString("doador", nome)
        end
    end,

    -- FNAF nextbot com nome (presente Urso Misha)
    ["fnaf"] = function(nome, dono)
        local e = spawnPerto("npc_drgbase_thebonwalten", dono)
        if IsValid(e) and nome ~= "" then
            e:SetNWString("doador", nome)
        end
    end,

    -- Espectador: quem ENTRA na live vira um BODYGUARD que te segue, com o
    -- nome em cima. Nasce na sua frente para a pessoa ver que apareceu.
    -- npc_xdehg = classname do Bodyguard Mod (descoberto via console).
    ["espectador"] = function(nome, dono)
        local e = spawnNaFrente("npc_xdehg", dono, 150)
        if not IsValid(e) then return end

        if nome ~= "" then
            e:SetNWString("doador", nome)
        end

        -- Tenta marcar o jogador como "dono" do bodyguard, para ele seguir.
        -- Mods de bodyguard usam nomes diferentes para isso; tentamos os
        -- mais comuns de forma segura (pcall) — se nenhum existir, o
        -- bodyguard ainda nasce e age pelo comportamento padrao do mod.
        pcall(function()
            -- formas comuns de definir o dono/lider
            if e.SetOwner then e:SetOwner(dono) end
            e:SetNWEntity("owner", dono)
            e:SetNWEntity("leader", dono)
            e:SetNWEntity("master", dono)
            -- formas comuns de ligar o "seguir"
            if e.SetFollow then e:SetFollow(true) end
            if e.Follow then e:Follow(dono) end
            e:SetNWBool("following", true)
            e:SetNWBool("follow", true)
            -- alguns mods leem um campo de "estado" textual
            if e.SetState then e:SetState("follow") end
        end)
    end,

    -- Tyrant (RE) com nome (presente Capybara)
    ["tyrant"] = function(nome, dono)
        local e = spawnPerto("npc_re_tyrant", dono)
        if IsValid(e) and nome ~= "" then
            e:SetNWString("doador", nome)
        end
    end,

    -- T-Rex com nome do doador flutuando
    ["trex"] = function(nome, dono)
        local e = spawnPerto("drg_milli_echo_jw_tyrannosaurus_rex", dono)
        if IsValid(e) and nome ~= "" then
            e:SetNWString("doador", nome)
        end
    end,

    -- Monstro backrooms com nome do doador flutuando
    ["backrooms"] = function(nome, dono)
        local e = spawnPerto("drg_costumeman", dono)
        if IsValid(e) and nome ~= "" then
            e:SetNWString("doador", nome)
        end
    end,

    -- Fogo no jogador quando alguem segue (sem nome flutuando)
    ["fogo"] = function(nome, dono)
        if IsValid(dono) then dono:Ignite(10) end
    end,

    -- Bomba 1000lb (presente Controle de videogame), sem nome flutuando.
    -- Mesmo efeito da antiga tecla F3: cai do ceu perto do jogador.
    ["bomba"] = function(nome, dono)
        if not IsValid(dono) then return end
        local pos = dono:GetPos() + Vector(
            math.random(-1500, 1500), math.random(-1500, 1500), 1500
        )
        local b = ents.Create("gb5_heavy_b_1000lb")
        if not IsValid(b) then return end
        b:SetPos(pos)
        b:Spawn()
        b:Activate()
        b:Use(dono, dono, 3, 1)
    end,

    -- BOMBA NUCLEAR: evento epico da barra de 1000 likes.
    -- Cai bem na frente do jogador e varre o mapa.
    -- >>> TROQUE "COLE_O_ID_DA_NUCLEAR" pelo classname da sua bomba nuclear <<<
    ["nuclear"] = function(nome, dono)
        if not IsValid(dono) then return end
        -- na frente do jogador, um pouco acima, para ele ver cair
        local frente = dono:GetForward()
        frente.z = 0
        local pos = dono:GetPos() + frente * 250 + Vector(0, 0, 200)
        local b = ents.Create("COLE_O_ID_DA_NUCLEAR")
        if not IsValid(b) then return end
        b:SetPos(pos)
        b:Spawn()
        b:Activate()
        -- muitas bombas detonam ao serem "usadas"; se a sua nao precisar,
        -- isso e inofensivo
        b:Use(dono, dono, 3, 1)
    end,

    -- ===== EXEMPLOS de migrar comandos de chat para a ponte =====
    -- Descomente e ajuste se quiser tirar esses comandos das teclas.

    -- ["barril"] = function(nome, dono)
    --     if not IsValid(dono) then return end
    --     local e = ents.Create("prop_physics")
    --     e:SetModel("models/props_c17/oildrum001_explosive.mdl")
    --     e:SetPos(dono:GetEyeTrace().HitPos)
    --     e:Spawn()
    --     e:Ignite(20)
    -- end,

    -- ["cura"] = function(nome, dono)
    --     if IsValid(dono) then dono:SetHealth(100) end
    -- end,

    -- ["formiga"] = function(nome, dono)
    --     if not IsValid(dono) then return end
    --     dono:SetModelScale(0.3, 1)
    --     timer.Simple(10, function()
    --         if IsValid(dono) then dono:SetModelScale(1, 1) end
    --     end)
    -- end,

    -- ["barco"] = function(nome, dono)
    --     if not IsValid(dono) then return end
    --     local e = ents.Create("prop_physics")
    --     e:SetModel("models/airboat.mdl")
    --     e:SetPos(dono:GetPos() + Vector(0, 0, 500))
    --     e:Spawn()
    -- end,

    -- ["drop"] = function(nome, dono)
    --     if IsValid(dono) then dono:DropWeapon(dono:GetActiveWeapon()) end
    -- end,
}

-- ---------- Processa uma linha "evento|nome" ----------
local function processarLinha(linha)
    linha = string.Trim(linha)
    if linha == "" then return end

    local sep = string.find(linha, "|", 1, true)
    local evento, nome
    if sep then
        evento = string.sub(linha, 1, sep - 1)
        nome = string.sub(linha, sep + 1)
    else
        evento = linha
        nome = ""
    end
    evento = string.Trim(evento)
    nome = string.Trim(nome)

    local fn = EVENTOS[evento]
    if not fn then
        print("[Live Caos] Evento desconhecido: " .. tostring(evento))
        return
    end

    -- Jogador host como referencia (primeiro player valido)
    local dono = Entity(1)
    if not IsValid(dono) then
        local players = player.GetAll()
        dono = players[1]
    end

    -- Protege o servidor: erro num evento nao derruba o timer
    local ok, err = pcall(fn, nome, dono)
    if not ok then
        print("[Live Caos] Erro no evento '" .. evento .. "': " .. tostring(err))
    end
end

-- ---------- Timer: le e consome a fila ----------
timer.Create("LiveCaosPonte", INTERVALO, 0, function()
    if not file.Exists(CAMINHO, "DATA") then return end

    local conteudo = file.Read(CAMINHO, "DATA")
    if not conteudo or conteudo == "" then return end

    -- Consome tudo de uma vez: limpa o arquivo ANTES de executar, para
    -- nao reprocessar caso um evento demore.
    file.Write(CAMINHO, "")

    for _, linha in ipairs(string.Explode("\n", conteudo)) do
        processarLinha(linha)
    end
end)

print("[Live Caos] Ponte por arquivo ativa. Lendo: data/" .. CAMINHO)

end  -- fim do "if SERVER then"

-- =====================================================================
--  CLIENTE: desenha o nome do doador flutuando sobre os zumbis
--  OTIMIZADO: nao varre ents.GetAll() todo frame. Mantem uma lista
--  curta de entidades com nome, atualizada quando elas nascem/morrem.
-- =====================================================================
if CLIENT then
    surface.CreateFont("FonteDoadorCaos", {
        font = "Roboto", size = 34, weight = 800,
        antialias = true, outline = true,
    })

    -- ----- Ajustes de performance -----
    local ALCANCE = 1200                      -- distancia maxima (unidades)
    local ALCANCE_SQR = ALCANCE * ALCANCE     -- comparacao sem raiz quadrada
    local MAX_NOMES = 10                       -- teto de nomes na tela
    local LIMPEZA_INTERVALO = 1.0              -- segundos entre limpezas da lista

    -- Lista enxuta: so as entidades que tem nome de doador.
    -- (em vez de ents.GetAll() — que percorre o mapa inteiro todo frame)
    local marcados = {}

    -- Registra automaticamente toda entidade nova que tenha o NWString.
    -- O NWString chega do servidor um instante depois do spawn, entao
    -- checamos rapido com um timer curto ao criar.
    hook.Add("OnEntityCreated", "LiveCaosRegistraNome", function(ent)
        if not IsValid(ent) then return end
        timer.Simple(0.2, function()
            if IsValid(ent) and ent:GetNWString("doador", "") ~= "" then
                marcados[ent] = true
            end
        end)
    end)

    -- Limpeza periodica: remove zumbis mortos/invalidos da lista.
    -- Roda 1x/s, nao 60x/s — barato.
    timer.Create("LiveCaosLimpaMarcados", LIMPEZA_INTERVALO, 0, function()
        for ent in pairs(marcados) do
            if not IsValid(ent) or ent:GetNWString("doador", "") == "" then
                marcados[ent] = nil
            end
        end
    end)

    -- Buffer reaproveitado entre frames (evita criar tabela toda hora)
    local visiveis = {}

    hook.Add("HUDPaint", "LiveCaosNomeDoador", function()
        local lp = LocalPlayer()
        if not IsValid(lp) then return end

        local origem = lp:GetPos()
        local aim = lp:GetAimVector()
        local n = 0

        -- Monta a lista de candidatos perto e a frente do jogador
        for ent in pairs(marcados) do
            if not IsValid(ent) then continue end

            local pos = ent:GetPos()
            local delta = pos - origem

            -- 1) Distancia ao quadrado (sem sqrt): corta os longe
            local distSqr = delta:LengthSqr()
            if distSqr > ALCANCE_SQR then continue end

            -- 2) Dot product: corta quem esta ATRAS do jogador
            --    (delta normalizado . direcao do olhar > 0 = a frente)
            if delta:Dot(aim) < 0 then continue end

            n = n + 1
            visiveis[n] = { ent = ent, dist = distSqr }
        end

        if n == 0 then return end

        -- Ordena por proximidade e desenha no maximo MAX_NOMES
        table.sort(visiveis, function(a, b) return a.dist < b.dist end)
        local limite = math.min(n, MAX_NOMES)

        for i = 1, limite do
            local ent = visiveis[i].ent
            if not IsValid(ent) then continue end

            local topo = ent:GetPos() + Vector(0, 0, ent:OBBMaxs().z + 15)
            local tela = topo:ToScreen()
            if tela.x < 0 or tela.x > ScrW() then continue end
            if tela.y < 0 or tela.y > ScrH() then continue end

            draw.SimpleTextOutlined(
                ent:GetNWString("doador", ""),
                "FonteDoadorCaos", tela.x, tela.y,
                Color(0, 255, 100), TEXT_ALIGN_CENTER, TEXT_ALIGN_CENTER,
                2, Color(0, 0, 0, 255)
            )
        end

        -- limpa o buffer para o proximo frame
        for i = 1, n do visiveis[i] = nil end
    end)

    print("[Live Caos] Desenho de nomes OTIMIZADO ativo (alcance "
        .. ALCANCE .. ", max " .. MAX_NOMES .. " nomes).")
end
