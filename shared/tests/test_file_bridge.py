"""Testes da ponte por arquivo (FileBridge) e do modo file na fila."""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from src.command_queue import CommandQueue, FileBridgeUnavailableError
from src.file_bridge import FileBridge
from src.models import ChatCommand, CommandConfig


class TestFileBridge:
    def test_escreve_evento_e_nome(self, tmp_path: Path) -> None:
        f = tmp_path / "fila.txt"
        bridge = FileBridge(f)
        bridge.write_event("zumbi", "joao")
        assert f.read_text(encoding="utf-8") == "zumbi|joao\n"

    def test_append_nao_sobrescreve(self, tmp_path: Path) -> None:
        f = tmp_path / "fila.txt"
        bridge = FileBridge(f)
        bridge.write_event("zumbi", "ana")
        bridge.write_event("barril", "bia")
        linhas = f.read_text(encoding="utf-8").splitlines()
        assert linhas == ["zumbi|ana", "barril|bia"]

    def test_remove_pipe_e_quebras_do_nome(self, tmp_path: Path) -> None:
        f = tmp_path / "fila.txt"
        bridge = FileBridge(f)
        bridge.write_event("zumbi", "jo|ao\nrcon")
        conteudo = f.read_text(encoding="utf-8")
        # apenas o separador do formato deve existir, nao no nome
        assert conteudo.count("|") == 1
        assert "\n" == conteudo[-1]  # so a quebra final

    def test_cria_diretorio_se_nao_existe(self, tmp_path: Path) -> None:
        f = tmp_path / "sub" / "dir" / "fila.txt"
        FileBridge(f).write_event("zumbi", "x")
        assert f.exists()

    def test_evento_sem_nome(self, tmp_path: Path) -> None:
        f = tmp_path / "fila.txt"
        FileBridge(f).write_event("barril")
        assert f.read_text(encoding="utf-8") == "barril|\n"


class TestModoFileNaFila:
    def test_comando_file_escreve_na_ponte_com_nome(self, tmp_path: Path) -> None:
        f = tmp_path / "fila.txt"
        bridge = FileBridge(f)
        executor = MagicMock()
        panel = AsyncMock()
        queue = CommandQueue(
            executor, panel, file_bridge=bridge,
            min_interval=0.0, retry_delay=0.0,
        )
        config = CommandConfig(
            trigger="__likes__", file="zumbi", label="Zumbi",
            bypass_cooldown=True,
        )

        async def scenario() -> None:
            await queue.put(
                ChatCommand(user="@maria", config=config, actor="@maria")
            )
            await queue.process_next()

        asyncio.run(scenario())

        assert f.read_text(encoding="utf-8") == "zumbi|@maria\n"
        executor.press.assert_not_called()
        executor.run_console.assert_not_called()

    def test_file_sem_ponte_descarta_sem_quebrar(self) -> None:
        executor = MagicMock()
        panel = AsyncMock()
        queue = CommandQueue(
            executor, panel, file_bridge=None,
            min_interval=0.0, retry_delay=0.0,
        )
        config = CommandConfig(trigger="x", file="zumbi", label="Z")

        async def scenario() -> None:
            await queue.put(ChatCommand(user="@a", config=config))
            await queue.process_next()  # nao deve levantar

        asyncio.run(scenario())
        # nenhum evento "executed" foi para o painel
        types = [c.args[0].get("type") for c in panel.broadcast.call_args_list]
        assert "executed" not in types

    def test_prioridade_file_sobre_console_e_keys(self, tmp_path: Path) -> None:
        f = tmp_path / "fila.txt"
        bridge = FileBridge(f)
        executor = MagicMock()
        queue = CommandQueue(
            executor, AsyncMock(), file_bridge=bridge,
            min_interval=0.0, retry_delay=0.0,
        )
        # config com os tres modos preenchidos: file deve vencer
        config = CommandConfig(
            trigger="x", file="zumbi", console="cmd", keys=("f1",), label="Z",
        )

        async def scenario() -> None:
            await queue.put(ChatCommand(user="@a", config=config, actor="@a"))
            await queue.process_next()

        asyncio.run(scenario())
        assert f.read_text(encoding="utf-8") == "zumbi|@a\n"
        executor.press.assert_not_called()
        executor.run_console.assert_not_called()
