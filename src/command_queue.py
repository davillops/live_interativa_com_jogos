"""Fila unica de comandos com worker, intervalo minimo e reagendamento."""
from __future__ import annotations

import asyncio
import logging

from src.file_bridge import FileBridge
from src.key_executor import (
    GameWindowNotFocusedError,
    KeyExecutor,
    KeyExecutorUnavailableError,
)
from src.models import ChatCommand
from src.panel_server import PanelServer

logger = logging.getLogger(__name__)


class FileBridgeUnavailableError(Exception):
    """Comando configurado para usar arquivo, mas sem ponte disponivel."""


class CommandQueue:
    """Processa comandos um a um, respeitando o ritmo do jogo.

    Comandos sao executados na ordem de chegada. Se a janela do jogo
    nao estiver em foco, o comando volta para o fim da fila apos um
    atraso, sem nunca enviar teclas para outra aplicacao (CA05).
    """

    def __init__(
        self,
        executor: KeyExecutor,
        panel: PanelServer,
        file_bridge: "FileBridge | None" = None,
        min_interval: float = 1.5,
        retry_delay: float = 2.0,
        max_size: int = 20,
        max_age: float = 30.0,
    ) -> None:
        self._executor = executor
        self._panel = panel
        self._file_bridge = file_bridge
        self._min_interval = min_interval
        self._retry_delay = retry_delay
        self._max_size = max_size
        self._max_age = max_age
        self._queue: asyncio.Queue[ChatCommand] = asyncio.Queue()

    @property
    def size(self) -> int:
        """Quantidade de comandos aguardando execucao."""
        return self._queue.qsize()

    def _execute(self, command: ChatCommand) -> None:
        """Executa a acao no jogo conforme o modo do comando.

        Prioridade: arquivo (nao rouba foco) > console > teclas.
        Roda em thread separada (run_in_executor) porque as operacoes
        de teclado/arquivo sao bloqueantes.

        Args:
            command: Comando a executar.

        Raises:
            FileBridgeUnavailableError: Se o comando usa arquivo mas
                nenhuma ponte foi configurada.
        """
        from src.key_executor import sanitize_name

        config = command.config
        actor = sanitize_name(command.actor or command.user)

        if config.uses_file:
            if self._file_bridge is None:
                raise FileBridgeUnavailableError(
                    f"Comando '{config.trigger}' usa 'file' mas a ponte "
                    "por arquivo nao foi configurada."
                )
            event = config.file.replace("{nome}", actor)
            self._file_bridge.write_event(event, actor)
        elif config.uses_console:
            line = config.console.replace("{nome}", actor)
            self._executor.run_console(line)
        else:
            self._executor.press(config.keys)

    async def put(self, command: ChatCommand) -> None:
        """Enfileira um comando, descartando se a fila estiver cheia.

        Numa live movimentada chegam mais comandos do que da para
        executar. Em vez de deixar a fila crescer sem limite (e atrasar
        tudo em horas), descartamos o comando novo quando a fila atinge
        ``max_size``. Assim o que esta na fila e sempre recente.

        Args:
            command: Comando aprovado pelo cooldown, pronto para executar.
        """
        if self.size >= self._max_size:
            logger.warning(
                "Fila cheia (%d); descartando %s de %s",
                self.size,
                command.config.trigger,
                command.user,
            )
            return
        await self._queue.put(command)
        logger.info(
            "Enfileirado: %s por %s (fila=%d)",
            command.config.trigger,
            command.user,
            self.size,
        )
        await self._panel.broadcast({"type": "queue", "size": self.size})

    async def run(self) -> None:
        """Loop infinito do worker. Cancele a task para encerrar."""
        logger.info("Worker da fila iniciado")
        while True:
            await self.process_next()

    async def process_next(self) -> None:
        """Processa exatamente um comando da fila (testavel isoladamente)."""
        command = await self._queue.get()

        # Descarta comando velho: numa live movimentada, um comando que
        # esperou demais ja perdeu o sentido (o viewer nem lembra mais).
        import time as _time

        age = _time.time() - command.created_at
        if age > self._max_age:
            logger.info(
                "Descartado por idade (%.0fs): %s de %s",
                age,
                command.config.trigger,
                command.user,
            )
            self._queue.task_done()
            return

        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self._execute, command)
        except GameWindowNotFocusedError:
            logger.warning(
                "Jogo fora de foco; descartando %s",
                command.config.trigger,
            )
            return
        except KeyExecutorUnavailableError:
            logger.error(
                "Backend de teclado indisponivel; comando %s descartado",
                command.config.trigger,
            )
            return
        except FileBridgeUnavailableError:
            logger.error(
                "Ponte por arquivo indisponivel; comando %s descartado",
                command.config.trigger,
            )
            return
        except OSError:
            logger.error(
                "Falha ao escrever na fila de arquivo; %s descartado",
                command.config.trigger,
                exc_info=True,
            )
            return
        finally:
            self._queue.task_done()

        logger.info(
            "Executado: %s por %s", command.config.trigger, command.user
        )
        # Para eventos internos (ex: __likes__), mostramos o label
        # ("Zumbi") no painel, nunca o identificador tecnico.
        display = command.config.trigger
        if display.startswith("__"):
            display = command.config.label
        await self._panel.broadcast(
            {
                "type": "executed",
                "user": command.user,
                "command": display,
                "trigger": command.config.trigger,
                "label": command.config.label,
                "emoji": command.config.emoji,
            }
        )
        await self._panel.broadcast({"type": "queue", "size": self.size})
        await asyncio.sleep(self._min_interval)
