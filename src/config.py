"""Configuracoes da aplicacao (variaveis de ambiente + commands.json)."""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from src.models import CommandConfig

load_dotenv()


class CommandsFileError(Exception):
    """O arquivo commands.json esta ausente ou malformado."""


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    """Configuracoes de execucao carregadas do ambiente (.env)."""

    tiktok_username: str
    tiktok_api_key: str
    ws_host: str
    ws_port: int
    min_interval: float
    retry_delay: float
    likes_goal: int
    queue_max_size: int
    queue_max_age: float
    game_window_title: str
    console_key: str
    queue_file: Path
    simulation: bool
    join_enabled: bool
    ranking_enabled: bool
    ranking_db: str
    nuclear_goal: int
    commands_file: Path
    log_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        """Constroi as configuracoes a partir das variaveis de ambiente."""
        return cls(
            tiktok_username=_env("TIKTOK_USERNAME", ""),
            tiktok_api_key=_env("TIKTOK_API_KEY", ""),
            ws_host=_env("WS_HOST", "localhost"),
            ws_port=int(_env("WS_PORT", "8765")),
            min_interval=float(_env("MIN_INTERVAL_SECONDS", "1.5")),
            retry_delay=float(_env("RETRY_DELAY_SECONDS", "2.0")),
            likes_goal=int(_env("LIKES_GOAL", "10")),
            queue_max_size=int(_env("QUEUE_MAX_SIZE", "20")),
            queue_max_age=float(_env("QUEUE_MAX_AGE_SECONDS", "30")),
            game_window_title=_env("GAME_WINDOW_TITLE", "Garry's Mod"),
            console_key=_env("CONSOLE_KEY", "`"),
            queue_file=Path(
                _env(
                    "QUEUE_FILE",
                    "C:/Program Files (x86)/Steam/steamapps/common/"
                    "GarrysMod/garrysmod/data/live_caos/fila.txt",
                )
            ),
            simulation=_env("SIMULATION", "false").lower() == "true",
            join_enabled=_env("JOIN_ENABLED", "false").lower() == "true",
            ranking_enabled=_env("RANKING_ENABLED", "true").lower() == "true",
            ranking_db=_env("RANKING_DB", "live_caos.db"),
            nuclear_goal=int(_env("NUCLEAR_GOAL", "1000")),
            commands_file=Path(_env("COMMANDS_FILE", "commands.json")),
            log_dir=Path(_env("LOG_DIR", "logs")),
        )


def load_interactions(path: Path) -> "Interactions":
    """Carrega comandos de chat e presentes executaveis do arquivo JSON.

    Args:
        path: Caminho do commands.json.

    Returns:
        Interactions com comandos (gatilho -> config) e presentes
        (nome do presente em minusculas -> config).

    Raises:
        CommandsFileError: Se o arquivo nao existir ou for invalido.
    """
    if not path.exists():
        raise CommandsFileError(f"Arquivo de comandos nao encontrado: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CommandsFileError(f"JSON invalido em {path}: {exc}") from exc

    commands: dict[str, CommandConfig] = {}
    for entry in raw.get("commands", []):
        config = CommandConfig(
            trigger=entry["trigger"],
            keys=tuple(entry.get("keys", [])),
            console=entry.get("console", ""),
            file=entry.get("file", ""),
            label=entry["label"],
            emoji=entry.get("emoji", ""),
            cooldown_global=float(entry.get("cooldown_global", 0)),
            cooldown_user=float(entry.get("cooldown_user", 0)),
            bypass_cooldown=bool(entry.get("bypass_cooldown", False)),
        )
        commands[config.trigger] = config
    if not commands:
        print(f"[LiveCaos] Nenhum comando de chat em {path} (OK para Hytale).")

    gifts: dict[str, CommandConfig] = {}
    for entry in raw.get("gifts", []):
        config = CommandConfig(
            trigger=entry["gift_name"],
            keys=tuple(entry.get("keys", [])),
            console=entry.get("console", ""),
            file=entry.get("file", ""),
            label=entry["label"],
            emoji=entry.get("emoji", ""),
            bypass_cooldown=True,  # quem pagou, ganha: presente nunca tem cooldown
        )
        gifts[config.trigger.strip().lower()] = config

    likes_action: CommandConfig | None = None
    likes_raw = raw.get("likes_meta")
    if likes_raw:
        likes_action = CommandConfig(
            trigger="__likes__",
            keys=tuple(likes_raw.get("keys", [])),
            console=likes_raw.get("console", ""),
            file=likes_raw.get("file", ""),
            label=likes_raw.get("label", "Zumbi"),
            emoji=likes_raw.get("emoji", ""),
            bypass_cooldown=True,
        )

    follow_action: CommandConfig | None = None
    follow_raw = raw.get("follow_meta")
    if follow_raw:
        follow_action = CommandConfig(
            trigger="__follow__",
            keys=tuple(follow_raw.get("keys", [])),
            console=follow_raw.get("console", ""),
            file=follow_raw.get("file", ""),
            label=follow_raw.get("label", "Fogo"),
            emoji=follow_raw.get("emoji", ""),
            bypass_cooldown=True,
        )

    join_action: CommandConfig | None = None
    join_raw = raw.get("join_meta")
    if join_raw:
        join_action = CommandConfig(
            trigger="__join__",
            keys=tuple(join_raw.get("keys", [])),
            console=join_raw.get("console", ""),
            file=join_raw.get("file", ""),
            label=join_raw.get("label", "Espectador"),
            emoji=join_raw.get("emoji", ""),
            bypass_cooldown=True,
        )

    nuclear_action: CommandConfig | None = None
    nuclear_raw = raw.get("nuclear_meta")
    if nuclear_raw:
        nuclear_action = CommandConfig(
            trigger="__nuclear__",
            keys=tuple(nuclear_raw.get("keys", [])),
            console=nuclear_raw.get("console", ""),
            file=nuclear_raw.get("file", ""),
            label=nuclear_raw.get("label", "Bomba Nuclear"),
            emoji=nuclear_raw.get("emoji", ""),
            bypass_cooldown=True,
        )

    return Interactions(
        commands=commands,
        gifts=gifts,
        likes_action=likes_action,
        follow_action=follow_action,
        join_action=join_action,
        nuclear_action=nuclear_action,
    )


@dataclass(frozen=True)
class Interactions:
    """Interacoes carregadas do commands.json."""

    commands: dict[str, CommandConfig]
    gifts: dict[str, CommandConfig]
    likes_action: CommandConfig | None = None
    follow_action: CommandConfig | None = None
    join_action: CommandConfig | None = None
    nuclear_action: CommandConfig | None = None


def setup_logging(log_dir: Path) -> None:
    """Configura logging em console + arquivo diario, sem print().

    Args:
        log_dir: Diretorio onde os arquivos de log serao gravados.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = log_dir / f"live_{date.today().isoformat()}.log"
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(logfile, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # A lib 'websockets' registra como ERROR (com traceback gigante) as
    # conexoes que abrem e fecham sem completar o handshake — ex: OBS ou
    # navegador reconectando, health-checks, abas fechando. Isso e
    # inofensivo e polui o log. Um filtro descarta SO esse caso especifico
    # (handshake malsucedido), mantendo "server listening" e erros reais.
    class _IgnoraHandshakeVazio(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            msg = record.getMessage()
            return "opening handshake failed" not in msg

    logging.getLogger("websockets.server").addFilter(_IgnoraHandshakeVazio())
