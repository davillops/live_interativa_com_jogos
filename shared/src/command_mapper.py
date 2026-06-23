"""Traducao de mensagens do chat para comandos configurados."""
from __future__ import annotations

import logging

from src.models import CommandConfig

logger = logging.getLogger(__name__)


class CommandMapper:
    """Mapeia o texto de uma mensagem de chat para um ``CommandConfig``.

    A comparacao e case-insensitive e considera apenas a primeira
    palavra da mensagem, entao "!BARRIL agora!!!" dispara "!barril".
    """

    def __init__(self, commands: dict[str, CommandConfig]) -> None:
        self._commands = {key.lower(): cfg for key, cfg in commands.items()}

    def map(self, text: str) -> CommandConfig | None:
        """Resolve o comando correspondente a uma mensagem de chat.

        Args:
            text: Conteudo bruto da mensagem do viewer.

        Returns:
            O ``CommandConfig`` correspondente, ou None se a mensagem
            nao for um comando conhecido.
        """
        if not text:
            return None
        stripped = text.strip()
        if not stripped:
            return None
        token = stripped.split()[0].lower()
        return self._commands.get(token)
