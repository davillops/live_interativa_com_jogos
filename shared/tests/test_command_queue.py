"""Testes da CommandQueue com executor e painel mockados."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.command_queue import CommandQueue
from src.key_executor import GameWindowNotFocusedError
from src.models import ChatCommand, CommandConfig


def make_command(trigger: str = "!barril") -> ChatCommand:
    config = CommandConfig(trigger=trigger, keys=("=",), label="Fogo Mira")
    return ChatCommand(user="@ana", config=config)


def make_queue(executor: MagicMock) -> tuple[CommandQueue, AsyncMock]:
    panel = AsyncMock()
    queue = CommandQueue(
        executor=executor, panel=panel, min_interval=0.0, retry_delay=0.0
    )
    return queue, panel


class TestCommandQueue:
    def test_executa_comando_e_notifica_painel(self) -> None:
        executor = MagicMock()
        queue, panel = make_queue(executor)

        async def scenario() -> None:
            await queue.put(make_command())
            await queue.process_next()

        asyncio.run(scenario())

        executor.press.assert_called_once_with(("=",))
        types_sent = [
            call.args[0]["type"] for call in panel.broadcast.call_args_list
        ]
        assert "executed" in types_sent

    def test_jogo_fora_de_foco_reagenda_sem_descartar(self) -> None:
        executor = MagicMock()
        executor.press.side_effect = [
            GameWindowNotFocusedError("fora de foco"),
            None,
        ]
        queue, panel = make_queue(executor)

        async def scenario() -> int:
            await queue.put(make_command())
            await queue.process_next()  # falha -> reagenda
            size_after_retry = queue.size
            await queue.process_next()  # segunda tentativa executa
            return size_after_retry

        size_after_retry = asyncio.run(scenario())

        assert size_after_retry == 1  # comando voltou para a fila
        assert executor.press.call_count == 2
        types_sent = [
            call.args[0]["type"] for call in panel.broadcast.call_args_list
        ]
        assert types_sent.count("executed") == 1

    def test_ordem_de_chegada_e_respeitada(self) -> None:
        executor = MagicMock()
        queue, _ = make_queue(executor)

        async def scenario() -> None:
            await queue.put(make_command("!barril"))
            await queue.put(make_command("!cura"))
            await queue.process_next()
            await queue.process_next()

        asyncio.run(scenario())

        pressed = [call.args[0] for call in executor.press.call_args_list]
        assert pressed == [("=",), ("=",)]
        assert executor.press.call_count == 2

    def test_tamanho_da_fila(self) -> None:
        executor = MagicMock()
        queue, _ = make_queue(executor)

        async def scenario() -> tuple[int, int]:
            await queue.put(make_command())
            before = queue.size
            await queue.process_next()
            return before, queue.size

        before, after = asyncio.run(scenario())
        assert before == 1
        assert after == 0
