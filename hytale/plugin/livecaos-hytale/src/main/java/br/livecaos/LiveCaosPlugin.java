package br.livecaos;

import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.server.core.entity.UUIDComponent;
import com.hypixel.hytale.server.core.event.events.player.AddPlayerToWorldEvent;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.universe.world.World;

import javax.annotation.Nonnull;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.*;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.logging.Level;

/**
 * Plugin Live Caos para Hytale.
 *
 * Dinamico: quando o jogador entra em qualquer mundo, o plugin detecta
 * automaticamente o caminho do save e usa a fila.txt e mobs.json de la.
 * Trocar de mundo = trocar de config automaticamente, sem editar .env.
 *
 * Estrutura por mundo:
 *   Saves/<nome do mundo>/livecaos/fila.txt   <- Python escreve aqui
 *   Saves/<nome do mundo>/livecaos/mobs.json  <- config de mobs
 */
public class LiveCaosPlugin extends JavaPlugin {

    private static final HytaleLogger LOG = HytaleLogger.forEnclosingClass();
    private static final long INTERVALO_MS = 300L;

    private EventoHandler handler;
    private ScheduledExecutorService scheduler;

    // atualizados automaticamente quando o jogador entra num mundo
    volatile World mundo;
    volatile UUID  jogadorUUID;
    volatile Path  caminhoFila;

    public LiveCaosPlugin(@Nonnull JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        handler = new EventoHandler();

        LOG.at(Level.INFO).log("[LiveCaos] Plugin iniciado. Aguardando jogador entrar num mundo...");

        // quando o jogador entra num mundo (qualquer um), atualiza tudo automaticamente
        this.getEventRegistry().registerGlobal(AddPlayerToWorldEvent.class, event -> {
            World novoMundo = event.getWorld();

            var uuidComp = event.getHolder().getComponent(UUIDComponent.getComponentType());
            if (uuidComp == null) return;

            mundo       = novoMundo;
            jogadorUUID = uuidComp.getUuid();

            // pasta livecaos dentro do save do mundo atual
            Path pastaMundo = novoMundo.getSavePath().resolve("livecaos");
            try {
                Files.createDirectories(pastaMundo);
            } catch (IOException e) {
                LOG.at(Level.WARNING).log("[LiveCaos] Erro ao criar pasta: %s", e.getMessage());
            }

            // atualiza o caminho da fila para este mundo
            caminhoFila = pastaMundo.resolve("fila.txt");

            // carrega (ou cria) o mobs.json deste mundo
            copiarMobsJsonSeNecessario(pastaMundo);
            handler.carregarConfig(pastaMundo);

            LOG.at(Level.INFO).log("[LiveCaos] Mundo: %s | Fila: %s",
                novoMundo.getName(), caminhoFila.toAbsolutePath());
        });

        // scheduler le a fila a cada 300ms
        scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "LiveCaos-Fila");
            t.setDaemon(true);
            return t;
        });
        scheduler.scheduleWithFixedDelay(
            this::lerEDespachar, INTERVALO_MS, INTERVALO_MS, TimeUnit.MILLISECONDS);
    }

    @Override
    protected void shutdown() {
        if (scheduler != null) scheduler.shutdownNow();
        LOG.at(Level.INFO).log("[LiveCaos] Plugin desativado.");
    }

    /**
     * Copia o mobs.json padrao do JAR para a pasta do mundo,
     * mas so se ainda nao existir (preserva configuracoes do usuario).
     */
    private void copiarMobsJsonSeNecessario(Path pastaMundo) {
        Path destino = pastaMundo.resolve("mobs.json");
        if (Files.exists(destino)) return; // ja existe, nao sobrescreve

        try (InputStream is = getClass().getResourceAsStream("/mobs.json")) {
            if (is != null) {
                Files.copy(is, destino);
                LOG.at(Level.INFO).log("[LiveCaos] mobs.json criado em: %s", destino);
            }
        } catch (IOException e) {
            LOG.at(Level.WARNING).log("[LiveCaos] Erro ao criar mobs.json: %s", e.getMessage());
        }
    }

    private void lerEDespachar() {
        if (mundo == null || jogadorUUID == null || caminhoFila == null) return;
        if (!mundo.isAlive()) return;
        if (!Files.exists(caminhoFila)) return;

        List<String> linhas;
        try {
            linhas = Files.readAllLines(caminhoFila);
            Files.writeString(caminhoFila, "", StandardOpenOption.TRUNCATE_EXISTING);
        } catch (IOException e) {
            LOG.at(Level.WARNING).log("[LiveCaos] Erro fila: %s", e.getMessage());
            return;
        }

        for (String linha : linhas) {
            linha = linha.strip().replace("\uFEFF", "");
            if (linha.isEmpty()) continue;

            String[] partes = linha.split("\\|", 2);
            final String evento = partes[0].strip();
            final String nome   = partes.length > 1 ? partes[1].strip() : "";
            final World  w    = mundo;
            final UUID   uuid = jogadorUUID;

            LOG.at(Level.INFO).log("[LiveCaos] Despachando: %s|%s", evento, nome);

            w.execute(() -> {
                try {
                    var ref = w.getEntityRef(uuid);
                    if (ref == null || !ref.isValid()) {
                        LOG.at(Level.WARNING).log("[LiveCaos] Ref do jogador invalida.");
                        return;
                    }
                    handler.executar(evento, nome, ref, w);
                } catch (Exception e) {
                    LOG.at(Level.WARNING).log("[LiveCaos] Erro '%s': %s", evento, e.getMessage());
                }
            });
        }
    }
}
