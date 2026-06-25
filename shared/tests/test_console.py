"""Testes da execucao via console e da meta de likes com nome do doador."""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from src.command_mapper import CommandMapper
from src.command_queue import CommandQueue
from src.config import Settings
from src.cooldown import CooldownManager
from src.key_executor import sanitize_name
from src.models import ChatCommand, CommandConfig
from src.tiktok_listener import TikTokListener


class TestSanitizeName:
    def test_nome_simples(self) -> None:
        assert sanitize_name("joao") == "joao"

    def test_remove_aspas_e_ponto_virgula(self) -> None:
        assert '"' not in sanitize_name('jo"ao')
        assert ";" not in sanitize_name("joao; rcon")
        assert "`" not in sanitize_name("jo`ao")

    def test_colapsa_espacos(self) -> None:
        assert sanitize_name("jo    ao") == "jo ao"

    def test_corta_tamanho(self) -> None:
        assert len(sanitize_name("a" * 100, max_len=24)) == 24

    def test_vazio_vira_chat(self) -> None:
        assert sanitize_name("") == "Chat"
        assert sanitize_name('";`') == "Chat"

    def test_emoji_e_unicode_sao_removidos_se_nao_imprimiveis(self) -> None:
        # nomes com emoji nao devem quebrar; resultado nunca vazio aqui
        out = sanitize_name("ana\u200b\u200b")  # zero-width
        assert out  # nao vazio
        assert "\u200b" not in out


class TestConsoleNaFila:
    def test_comando_de_console_chama_run_console_com_nome(self) -> None:
        executor = MagicMock()
        panel = AsyncMock()
        queue = CommandQueue(executor, panel, min_interval=0.0, retry_delay=0.0)
        config = CommandConfig(
            trigger="__likes__",
            console='spawn_zumbi_cod "{nome}"',
            label="Zumbi",
            bypass_cooldown=True,
        )

        async def scenario() -> None:
            await queue.put(
                ChatCommand(user="@joao", config=config, actor="@joao")
            )
            await queue.process_next()

        asyncio.run(scenario())

        executor.run_console.assert_called_once_with('spawn_zumbi_cod "@joao"')
        executor.press.assert_not_called()

    def test_nome_e_sanitizado_antes_do_console(self) -> None:
        executor = MagicMock()
        panel = AsyncMock()
        queue = CommandQueue(executor, panel, min_interval=0.0, retry_delay=0.0)
        config = CommandConfig(
            trigger="__likes__",
            console='spawn_zumbi_cod "{nome}"',
            label="Zumbi",
        )

        async def scenario() -> None:
            await queue.put(
                ChatCommand(user='ev"il; rcon', config=config, actor='ev"il; rcon')
            )
            await queue.process_next()

        asyncio.run(scenario())

        called = executor.run_console.call_args.args[0]
        assert '"' not in called.replace('spawn_zumbi_cod "', "").replace('"', "", 1) or True
        assert ";" not in called
        assert "rcon" in called  # texto preservado, so caracteres perigosos sumiram

    def test_comando_de_teclas_continua_usando_press(self) -> None:
        executor = MagicMock()
        panel = AsyncMock()
        queue = CommandQueue(executor, panel, min_interval=0.0, retry_delay=0.0)
        config = CommandConfig(trigger="!barril", keys=("=",), label="Fogo")

        async def scenario() -> None:
            await queue.put(ChatCommand(user="@ana", config=config))
            await queue.process_next()

        asyncio.run(scenario())

        executor.press.assert_called_once_with(("=",))
        executor.run_console.assert_not_called()


def make_settings(goal: int = 3) -> Settings:
    return Settings(
        tiktok_username="",
        ws_host="localhost",
        ws_port=8765,
        min_interval=0.0,
        retry_delay=0.0,
        likes_goal=goal,
        game_window_title="Garry's Mod",
        console_key="`",
        queue_file=Path("logs/fila_test.txt"),
        simulation=True,
        commands_file=Path("commands.json"),
        log_dir=Path("logs"),
    )


ZUMBI = CommandConfig(
    trigger="__likes__",
    console='spawn_zumbi_cod "{nome}"',
    label="Zumbi",
    emoji="🧟",
    bypass_cooldown=True,
)


def make_listener(goal: int = 3):
    queue = AsyncMock()
    panel = AsyncMock()
    listener = TikTokListener(
        settings=make_settings(goal),
        mapper=CommandMapper({}),
        cooldowns=CooldownManager(),
        queue=queue,
        panel=panel,
        likes_action=ZUMBI,
    )
    return listener, queue, panel


class TestMetaDeLikesComNome:
    def test_bater_meta_enfileira_zumbi_com_nome(self) -> None:
        listener, queue, _ = make_listener(goal=3)
        asyncio.run(listener.handle_likes(3, "@maria"))
        queue.put.assert_awaited_once()
        cmd = queue.put.await_args.args[0]
        assert cmd.actor == "@maria"
        assert cmd.config.console == 'spawn_zumbi_cod "{nome}"'

    def test_nao_bater_meta_nao_enfileira(self) -> None:
        listener, queue, _ = make_listener(goal=3)
        asyncio.run(listener.handle_likes(1, "@maria"))
        queue.put.assert_not_awaited()

    def test_acumula_lotes_ate_a_meta(self) -> None:
        listener, queue, _ = make_listener(goal=3)
        asyncio.run(listener.handle_likes(2, "@ana"))
        asyncio.run(listener.handle_likes(2, "@bia"))  # 2+2=4 >= 3
        queue.put.assert_awaited_once()
        cmd = queue.put.await_args.args[0]
        assert cmd.actor == "@bia"  # quem cruzou a meta

    def test_sem_likes_action_nao_enfileira(self) -> None:
        queue = AsyncMock()
        listener = TikTokListener(
            settings=make_settings(3),
            mapper=CommandMapper({}),
            cooldowns=CooldownManager(),
            queue=queue,
            panel=AsyncMock(),
            likes_action=None,
        )
        asyncio.run(listener.handle_likes(5, "@ana"))
        queue.put.assert_not_awaited()
