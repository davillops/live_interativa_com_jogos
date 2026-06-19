"""Testes dos presentes executaveis e do load_interactions."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

from src.command_mapper import CommandMapper
from src.config import Settings, load_interactions
from src.cooldown import CooldownManager
from src.models import CommandConfig
from src.tiktok_listener import TikTokListener


def make_settings() -> Settings:
    return Settings(
        tiktok_username="",
        ws_host="localhost",
        ws_port=8765,
        min_interval=0.0,
        retry_delay=0.0,
        likes_goal=5,
        game_window_title="Garry's Mod",
        simulation=True,
        commands_file=Path("commands.json"),
        log_dir=Path("logs"),
    )


def make_listener(gift_actions: dict) -> tuple[TikTokListener, AsyncMock, AsyncMock]:
    queue = AsyncMock()
    panel = AsyncMock()
    barril = CommandConfig(
        trigger="!barril", keys=("=",), label="Fogo Mira", cooldown_global=8
    )
    listener = TikTokListener(
        settings=make_settings(),
        mapper=CommandMapper({"!barril": barril}),
        cooldowns=CooldownManager(),
        queue=queue,
        panel=panel,
        gift_actions=gift_actions,
    )
    return listener, queue, panel


BOMBA = CommandConfig(
    trigger="Controle de videogame",
    keys=("f3",),
    label="Bomba 1000lb",
    emoji="🎮",
    bypass_cooldown=True,
)


class TestPresentesExecutaveis:
    def test_presente_configurado_entra_na_fila(self) -> None:
        listener, queue, panel = make_listener(
            {"controle de videogame": BOMBA}
        )
        asyncio.run(listener.handle_gift("@ana", "Controle de videogame"))
        queue.put.assert_awaited_once()
        enqueued = queue.put.await_args.args[0]
        assert enqueued.config.keys == ("f3",)
        panel.broadcast.assert_not_awaited()  # sem toast social duplicado

    def test_nome_do_presente_ignora_maiusculas_e_espacos(self) -> None:
        listener, queue, _ = make_listener({"controle de videogame": BOMBA})
        asyncio.run(listener.handle_gift("@ana", "  CONTROLE DE VIDEOGAME "))
        queue.put.assert_awaited_once()

    def test_presente_nao_configurado_so_notifica_painel(self) -> None:
        listener, queue, panel = make_listener(
            {"controle de videogame": BOMBA}
        )
        asyncio.run(listener.handle_gift("@ana", "Rosa"))
        queue.put.assert_not_awaited()
        event = panel.broadcast.await_args.args[0]
        assert event["type"] == "social"
        assert event["gift"] == "Rosa"


class TestLoadInteractions:
    def test_carrega_comandos_e_presentes(self, tmp_path: Path) -> None:
        data = {
            "commands": [
                {"trigger": "!x", "keys": ["f1"], "label": "X"}
            ],
            "gifts": [
                {
                    "gift_name": "Controle de videogame",
                    "keys": ["f3"],
                    "label": "Bomba 1000lb",
                }
            ],
        }
        file = tmp_path / "commands.json"
        file.write_text(json.dumps(data), encoding="utf-8")

        interactions = load_interactions(file)

        assert "!x" in interactions.commands
        gift = interactions.gifts["controle de videogame"]
        assert gift.keys == ("f3",)
        assert gift.bypass_cooldown is True  # presente nunca tem cooldown

    def test_gifts_e_opcional(self, tmp_path: Path) -> None:
        data = {"commands": [{"trigger": "!x", "keys": ["f1"], "label": "X"}]}
        file = tmp_path / "commands.json"
        file.write_text(json.dumps(data), encoding="utf-8")
        assert load_interactions(file).gifts == {}

    def test_projeto_real_carrega(self) -> None:
        interactions = load_interactions(Path("commands.json"))
        assert "controle de videogame" in interactions.gifts
        assert len(interactions.commands) == 5
