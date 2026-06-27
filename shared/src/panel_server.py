"""Servidor WebSocket local que alimenta o overlay (Browser Source)."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class PanelServer:
    """Mantem conexoes do overlay e transmite eventos em JSON.

    O overlay e somente leitura: mensagens recebidas dos clientes sao
    ignoradas. Multiplos overlays (ex: OBS + navegador de teste) podem
    conectar simultaneamente.
    """

    def __init__(self, host: str, port: int, config: dict[str, Any] | None = None) -> None:
        self._host = host
        self._port = port
        self._clients: set[Any] = set()
        self._server: Any = None
        self._config = config or {}

    async def start(self) -> None:
        """Sobe o servidor WebSocket e passa a aceitar conexoes."""
        import websockets

        self._server = await websockets.serve(
            self._handle_client, self._host, self._port
        )
        logger.info(
            "Painel WebSocket ouvindo em ws://%s:%d", self._host, self._port
        )

    async def _handle_client(self, websocket: Any) -> None:
        self._clients.add(websocket)
        logger.info("Overlay conectado (%d ativos)", len(self._clients))
        # manda config inicial para o overlay recem conectado
        if self._config:
            try:
                import json
                await websocket.send(json.dumps({"type": "config", **self._config}))
            except Exception:
                pass
        try:
            async for _ in websocket:
                pass  # overlay nao envia comandos
        finally:
            self._clients.discard(websocket)
            logger.info("Overlay desconectado (%d ativos)", len(self._clients))

    async def broadcast(self, event: dict[str, Any]) -> None:
        """Envia um evento JSON para todos os overlays conectados.

        Args:
            event: Dicionario serializavel (ex: {"type": "executed", ...}).
        """
        if not self._clients:
            return
        message = json.dumps(event, ensure_ascii=False)
        results = await asyncio.gather(
            *(client.send(message) for client in set(self._clients)),
            return_exceptions=True,
        )
        failures = sum(1 for item in results if isinstance(item, Exception))
        if failures:
            logger.warning("Falha ao enviar evento para %d overlay(s)", failures)
