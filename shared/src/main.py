"""Ponto de entrada: monta as dependencias e sobe os servicos.

Uso:
    python -m src.main
"""
from __future__ import annotations

import asyncio
import logging

from src.command_mapper import CommandMapper
from src.command_queue import CommandQueue
from src.config import Settings, load_interactions, setup_logging
from src.cooldown import CooldownManager
from src.file_bridge import FileBridge
from src.key_executor import KeyExecutor
from src.panel_server import PanelServer
from src.ranking import Ranking
from src.tiktok_listener import TikTokListener

logger = logging.getLogger(__name__)


async def run() -> None:
    """Sobe painel, worker da fila e listener do TikTok em paralelo."""
    settings = Settings.from_env()
    setup_logging(settings.log_dir)

    if not settings.simulation and not settings.tiktok_username:
        logger.critical(
            "Defina TIKTOK_USERNAME no .env (ou SIMULATION=true para testar)."
        )
        return

    interactions = load_interactions(settings.commands_file)
    logger.info(
        "Comandos: %s", ", ".join(sorted(interactions.commands.keys()))
    )
    logger.info(
        "Presentes executaveis: %s",
        ", ".join(sorted(interactions.gifts.keys())) or "nenhum",
    )
    logger.info(
        "Acao de meta de likes: %s",
        "configurada (Python)" if interactions.likes_action else "nenhuma (Tikfinity)",
    )
    logger.info(
        "Acao de seguir: %s",
        "configurada (Python)" if interactions.follow_action else "nenhuma (Tikfinity)",
    )
    logger.info(
        "Acao de entrar na live: %s",
        ("LIGADA" if settings.join_enabled else "desligada (JOIN_ENABLED)")
        if interactions.join_action else "nenhuma",
    )
    logger.info(
        "Meta NUCLEAR: %s",
        ("%d likes" % settings.nuclear_goal)
        if interactions.nuclear_action else "nenhuma",
    )

    ranking = None
    if settings.ranking_enabled:
        # Em modo simulacao usamos um banco SEPARADO, para os bots de teste
        # (@joao_zoeira etc.) nao sujarem o ranking historico real. O banco
        # de teste pode ser apagado a vontade sem afetar a live de verdade.
        if settings.simulation:
            db_real = settings.ranking_db
            base = db_real[:-3] if db_real.endswith(".db") else db_real
            db_usado = base + "_teste.db"
            logger.info(
                "Ranking ATIVO em MODO TESTE (banco separado: %s). "
                "O banco real (%s) nao sera tocado.",
                db_usado, db_real,
            )
        else:
            db_usado = settings.ranking_db
            logger.info("Ranking ATIVO (banco: %s)", db_usado)
        ranking = Ranking(db_path=db_usado)
    else:
        logger.info("Ranking desligado (RANKING_ENABLED)")

    panel = PanelServer(
        settings.ws_host,
        settings.ws_port,
        config={"likes_enabled": settings.likes_enabled},
    )
    executor = KeyExecutor(settings.game_window_title, settings.console_key)
    file_bridge = FileBridge(settings.queue_file)
    queue = CommandQueue(
        executor=executor,
        panel=panel,
        file_bridge=file_bridge,
        min_interval=settings.min_interval,
        retry_delay=settings.retry_delay,
        max_size=settings.queue_max_size,
        max_age=settings.queue_max_age,
    )
    mapper = CommandMapper(interactions.commands)
    cooldowns = CooldownManager()
    listener = TikTokListener(
        settings=settings,
        mapper=mapper,
        cooldowns=cooldowns,
        queue=queue,
        panel=panel,
        gift_actions=interactions.gifts,
        likes_action=interactions.likes_action,
        follow_action=interactions.follow_action,
        join_action=interactions.join_action,
        ranking=ranking,
        nuclear_action=interactions.nuclear_action,
    )

    await panel.start()
    await asyncio.gather(queue.run(), listener.run())


def main() -> None:
    """Entrada sincrona com encerramento limpo via Ctrl+C."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Encerrado pelo usuario (Ctrl+C)")


if __name__ == "__main__":
    main()
