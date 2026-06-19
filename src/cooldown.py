"""Controle de cooldown global e por usuario para comandos de chat."""
from __future__ import annotations

import logging
import time
from typing import Callable

from src.models import CommandConfig

logger = logging.getLogger(__name__)


class CooldownManager:
    """Gerencia cooldowns em dois niveis: por comando e por (comando, usuario).

    O relogio e injetavel para permitir testes deterministicos.
    Usa epoch (time.time) para que o painel consiga animar a contagem
    regressiva no navegador a partir de ``ready_at``.
    """

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._global_ready: dict[str, float] = {}
        self._user_ready: dict[tuple[str, str], float] = {}

    def try_acquire(self, config: CommandConfig, user: str) -> bool:
        """Tenta reservar a execucao de um comando para um usuario.

        Args:
            config: Configuracao do comando solicitado.
            user: Identificador do viewer que solicitou.

        Returns:
            True se o comando pode executar agora (cooldowns aplicados),
            False se esta em cooldown e deve ser descartado.
        """
        if config.bypass_cooldown:
            return True

        now = self._clock()
        trigger = config.trigger

        if self._global_ready.get(trigger, 0.0) > now:
            logger.info(
                "Descartado por cooldown global: %s (user=%s)", trigger, user
            )
            return False

        if self._user_ready.get((trigger, user), 0.0) > now:
            logger.info(
                "Descartado por cooldown de usuario: %s (user=%s)", trigger, user
            )
            return False

        if config.cooldown_global > 0:
            self._global_ready[trigger] = now + config.cooldown_global
        if config.cooldown_user > 0:
            self._user_ready[(trigger, user)] = now + config.cooldown_user
        return True

    def ready_at(self, trigger: str) -> float:
        """Retorna o epoch em que o comando estara disponivel globalmente.

        Args:
            trigger: Gatilho do comando (ex: "!barril").

        Returns:
            Epoch em segundos; 0.0 se o comando nunca entrou em cooldown.
        """
        return self._global_ready.get(trigger, 0.0)
