package br.livecaos;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import org.joml.Vector3d;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.HashMap;
import java.util.Map;
import java.util.logging.Level;

/**
 * Executa eventos da fila — sempre chamado dentro da WorldThread.
 *
 * O mapeamento evento→role e carregado do mobs.json na pasta do plugin.
 * Para editar: abra o mobs.json e altere os roles. Reinicie o mundo para recarregar.
 */
public class EventoHandler {

    private static final HytaleLogger LOG = HytaleLogger.forEnclosingClass();
    private static final double DIST_FRENTE = 4.0;

    // mapa evento → role (ex: "rose" → "Werewolf")
    private final Map<String, String> eventosParaRole = new HashMap<>();
    // mapa evento → modelo (pode ser null = usa padrao do role)
    private final Map<String, String> eventosParaModelo = new HashMap<>();

    /**
     * Carrega o mobs.json da pasta do plugin.
     * Se nao encontrar, usa o mobs.json embutido no JAR como fallback.
     */
    public void carregarConfig(Path pastaPlugin) {
        Path configPath = pastaPlugin.resolve("mobs.json");

        // se nao existe na pasta do plugin, copia o padrao do JAR
        if (!Files.exists(configPath)) {
            try (InputStream is = getClass().getResourceAsStream("/mobs.json")) {
                if (is != null) {
                    Files.copy(is, configPath);
                    LOG.at(Level.INFO).log("[LiveCaos] mobs.json criado com valores padrao em: %s", configPath);
                }
            } catch (Exception e) {
                LOG.at(Level.WARNING).log("[LiveCaos] Nao foi possivel criar mobs.json: %s", e.getMessage());
            }
        }

        // le e parseia o JSON manualmente (sem dependencia externa)
        try {
            String json = Files.readString(configPath, StandardCharsets.UTF_8);
            parsearMobs(json);
            LOG.at(Level.INFO).log("[LiveCaos] mobs.json carregado: %d mobs configurados.", eventosParaRole.size());
        } catch (Exception e) {
            LOG.at(Level.WARNING).log("[LiveCaos] Erro ao ler mobs.json: %s", e.getMessage());
        }
    }

    // mapa evento → quantidade (default 1)
    private final Map<String, Integer> eventosParaQtd = new HashMap<>();

    /**
     * Parser JSON minimalista — sem biblioteca externa.
     * Le blocos { "evento": "...", "role": "...", "modelo": ..., "quantidade": N } do array "mobs".
     */
    private void parsearMobs(String json) {
        eventosParaRole.clear();
        eventosParaModelo.clear();
        eventosParaQtd.clear();

        // encontra o array "mobs": [...]
        int inicio = json.indexOf("\"mobs\"");
        if (inicio < 0) return;
        int abreColchete = json.indexOf('[', inicio);
        int fechaColchete = json.lastIndexOf(']');
        if (abreColchete < 0 || fechaColchete < 0) return;

        String arrayStr = json.substring(abreColchete + 1, fechaColchete);

        // divide em blocos de objeto {...}
        int pos = 0;
        while (pos < arrayStr.length()) {
            int abre = arrayStr.indexOf('{', pos);
            if (abre < 0) break;
            int fecha = arrayStr.indexOf('}', abre);
            if (fecha < 0) break;

            String bloco = arrayStr.substring(abre + 1, fecha);
            String evento    = extrairValor(bloco, "evento");
            String role      = extrairValor(bloco, "role");
            String modelo    = extrairValorOuNull(bloco, "modelo");
            int    quantidade = extrairInt(bloco, "quantidade", 1);

            if (evento != null && role != null) {
                eventosParaRole.put(evento.toLowerCase(), role);
                eventosParaModelo.put(evento.toLowerCase(), modelo);
                eventosParaQtd.put(evento.toLowerCase(), quantidade);
            }
            pos = fecha + 1;
        }
    }

    private String extrairValor(String bloco, String chave) {
        String busca = "\"" + chave + "\"";
        int idx = bloco.indexOf(busca);
        if (idx < 0) return null;
        int doisPontos = bloco.indexOf(':', idx + busca.length());
        if (doisPontos < 0) return null;
        int abreAspas = bloco.indexOf('"', doisPontos + 1);
        if (abreAspas < 0) return null;
        int fechaAspas = bloco.indexOf('"', abreAspas + 1);
        if (fechaAspas < 0) return null;
        return bloco.substring(abreAspas + 1, fechaAspas);
    }

    private String extrairValorOuNull(String bloco, String chave) {
        String busca = "\"" + chave + "\"";
        int idx = bloco.indexOf(busca);
        if (idx < 0) return null;
        int doisPontos = bloco.indexOf(':', idx + busca.length());
        if (doisPontos < 0) return null;
        String resto = bloco.substring(doisPontos + 1).strip();
        if (resto.startsWith("null")) return null;
        if (resto.startsWith("\"")) {
            int abre = bloco.indexOf('"', doisPontos + 1);
            int fecha = bloco.indexOf('"', abre + 1);
            return bloco.substring(abre + 1, fecha);
        }
        return null;
    }

    private int extrairInt(String bloco, String chave, int padrao) {
        String busca = "\"" + chave + "\"";
        int idx = bloco.indexOf(busca);
        if (idx < 0) return padrao;
        int doisPontos = bloco.indexOf(':', idx + busca.length());
        if (doisPontos < 0) return padrao;
        String resto = bloco.substring(doisPontos + 1).strip();
        try {
            // pega so os digitos ate o proximo separador
            StringBuilder sb = new StringBuilder();
            for (char c : resto.toCharArray()) {
                if (Character.isDigit(c)) sb.append(c);
                else if (sb.length() > 0) break;
            }
            return sb.length() > 0 ? Integer.parseInt(sb.toString()) : padrao;
        } catch (NumberFormatException e) {
            return padrao;
        }
    }

    // ------------------------------------------------------------------

    /** Chamado sempre dentro da WorldThread */
    public void executar(String evento, String nome, Ref<EntityStore> ref, World world) {
        String eventoLower = evento.toLowerCase();
        String role = eventosParaRole.get(eventoLower);

        if (role == null) {
            LOG.at(Level.INFO).log("[LiveCaos] Evento nao configurado no mobs.json: %s", evento);
            return;
        }

        String modelo    = eventosParaModelo.get(eventoLower);
        int    quantidade = eventosParaQtd.getOrDefault(eventoLower, 1);
        spawnMob(role, modelo, nome, quantidade, ref, world);
    }

    private void spawnMob(String role, String modelo, String nome, int quantidade,
                          Ref<EntityStore> ref, World world) {
        Store<EntityStore> store = world.getEntityStore().getStore();

        TransformComponent tc = store.getComponent(ref, TransformComponent.getComponentType());
        if (tc == null) {
            LOG.at(Level.WARNING).log("[LiveCaos] TransformComponent nulo.");
            return;
        }

        PlayerRef player = store.getComponent(ref, PlayerRef.getComponentType());
        if (player == null) return;

        double yawRad = Math.toRadians(tc.getRotation().y());
        double baseX  = tc.getPosition().x() + (-Math.sin(yawRad) * DIST_FRENTE);
        double baseY  = tc.getPosition().y() + 0.1;
        double baseZ  = tc.getPosition().z() + ( Math.cos(yawRad) * DIST_FRENTE);
        Rotation3f spawnRot = new Rotation3f(0, tc.getRotation().y(), 0);

        // spawna 'quantidade' vezes com pequeno offset lateral para nao sobrepor
        for (int i = 0; i < quantidade; i++) {
            double offset = (i - (quantidade - 1) / 2.0) * 1.5; // espaca 1.5 blocos lateralmente
            double spawnX = baseX + Math.cos(yawRad) * offset;
            double spawnZ = baseZ + Math.sin(yawRad) * offset;
            Vector3d spawnPos = new Vector3d(spawnX, baseY, spawnZ);
            NPCPlugin.get().spawnNPC(store, role, modelo, spawnPos, spawnRot);
        }

        if (nome != null && !nome.isEmpty()) {
            player.sendMessage(Message.raw("[LiveCaos] " + quantidade + "x " + role + " de: " + nome));
        }
        LOG.at(Level.INFO).log("[LiveCaos] %dx %s spawnado por %s",
            quantidade, role, nome.isEmpty() ? "?" : nome);
    }
}
