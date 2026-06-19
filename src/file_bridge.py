"""Ponte por arquivo: o Python anexa eventos numa fila lida pelo addon Lua.

Formato de cada linha: ``evento|nome`` (ex: ``zumbi|joao_gamer``).
O addon Lua le o arquivo num timer, executa as linhas novas e trunca o
arquivo. Esta abordagem NAO abre console nem rouba foco do jogo.

Robustez:
- Escrita em modo append protegida por threading.Lock (varios eventos
  podem chegar concorrentemente das threads do asyncio executor).
- flush + os.fsync para o Lua nunca ler uma linha pela metade.
- O nome e sanitizado e o separador "|" e removido do nome.
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class FileBridge:
    """Anexa eventos numa fila de texto consumida pelo addon Lua do GMod."""

    def __init__(self, queue_file: Path) -> None:
        self._queue_file = queue_file
        self._lock = threading.Lock()
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Ponte por arquivo: %s", self._queue_file)

    def write_event(self, event: str, name: str = "") -> None:
        """Anexa uma linha ``evento|nome`` na fila, de forma atomica.

        Args:
            event: Identificador do evento (ex: "zumbi", "barril").
            name: Nome do doador, ja sanitizado. "|" e quebras de linha
                sao removidos por seguranca.

        Raises:
            OSError: Se nao for possivel escrever no arquivo.
        """
        safe_name = name.replace("|", " ").replace("\n", " ").replace("\r", " ")
        line = f"{event}|{safe_name}\n"
        with self._lock:
            with open(self._queue_file, "a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
        logger.debug("Evento na fila de arquivo: %s", line.strip())
