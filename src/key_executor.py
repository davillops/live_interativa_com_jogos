"""Pressionamento de teclas no jogo com verificacao de foco da janela.

Backend preferencial: ``pydirectinput`` (injeta scancodes que jogos
Source reconhecem). Fallback: ``pyautogui``. Ambos sao importados de
forma tolerante para que os testes rodem em ambientes sem display.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

_backend = None
_backend_name = "none"
_pyautogui_write = None  # funcao de digitar string (sempre via pyautogui)

try:  # pragma: no cover - depende do SO
    import pyautogui as _pyautogui

    _pyautogui_write = _pyautogui.write
except ImportError:  # pragma: no cover
    _pyautogui = None

try:  # pragma: no cover - depende do SO
    import pydirectinput as _backend  # type: ignore[no-redef]

    _backend.PAUSE = 0.05
    _backend_name = "pydirectinput"
except ImportError:  # pragma: no cover
    if _pyautogui is not None:
        _backend = _pyautogui
        _backend.PAUSE = 0.05
        _backend_name = "pyautogui"
    else:
        _backend = None

try:  # pragma: no cover - depende do SO
    import pygetwindow as _gw
except ImportError:  # pragma: no cover
    _gw = None


def sanitize_name(name: str, max_len: int = 24) -> str:
    """Limpa o nome de um viewer para uso seguro no console do GMod.

    Remove aspas e caracteres de controle que quebrariam o comando,
    colapsa espacos e corta o comprimento. Nomes vazios viram "Chat".

    Args:
        name: Nome de exibicao bruto vindo do TikTok.
        max_len: Tamanho maximo do nome resultante.

    Returns:
        Nome seguro para interpolar em um comando de console.
    """
    if not name:
        return "Chat"
    # remove aspas, ponto-e-virgula e caracteres de controle/nova linha
    cleaned = "".join(
        ch for ch in name if ch.isprintable() and ch not in '";`'
    )
    cleaned = " ".join(cleaned.split())  # colapsa espacos
    cleaned = cleaned[:max_len].strip()
    return cleaned or "Chat"


class GameWindowNotFocusedError(Exception):
    """A janela do jogo nao esta em foco; o comando deve aguardar."""


class KeyExecutorUnavailableError(Exception):
    """Nenhum backend de teclado disponivel neste ambiente."""


class KeyExecutor:
    """Pressiona teclas no jogo somente quando a janela esta em foco."""

    def __init__(self, window_title: str, console_key: str = "`") -> None:
        self._window_title = window_title.lower()
        self._console_key = console_key
        logger.info("Backend de teclado: %s", _backend_name)

    def is_game_focused(self) -> bool:
        """Verifica se a janela ativa do SO e a janela do jogo.

        Returns:
            True se o titulo da janela ativa contem o titulo configurado.
            Se ``pygetwindow`` nao estiver disponivel, assume True para
            nao bloquear ambientes de teste/simulacao.
        """
        if _gw is None:
            return True
        try:
            active = _gw.getActiveWindow()
        except _gw.PyGetWindowException:
            logger.warning("Falha ao consultar janela ativa", exc_info=True)
            return False
        if active is None or not getattr(active, "title", ""):
            return False
        return self._window_title in active.title.lower()

    def press(self, keys: tuple[str, ...]) -> None:
        """Pressiona uma tecla simples ou um combo com modificadores.

        Em combos ("ctrl", "1"), todas as teclas anteriores a ultima sao
        seguradas como modificadores enquanto a ultima e pressionada.

        Args:
            keys: Sequencia de teclas no vocabulario do backend
                (ex: ("f7",) ou ("ctrl", "1")).

        Raises:
            GameWindowNotFocusedError: Se o jogo nao esta em foco.
            KeyExecutorUnavailableError: Se nenhum backend foi importado.
        """
        if _backend is None:
            raise KeyExecutorUnavailableError(
                "Instale pydirectinput (Windows) ou pyautogui."
            )
        if not self.is_game_focused():
            raise GameWindowNotFocusedError(
                f"Janela contendo '{self._window_title}' nao esta em foco."
            )

        if len(keys) == 1:
            _backend.press(keys[0])
            logger.debug("Tecla pressionada: %s", keys[0])
            return

        modifiers, final_key = keys[:-1], keys[-1]
        for modifier in modifiers:
            _backend.keyDown(modifier)
        try:
            _backend.press(final_key)
        finally:
            for modifier in reversed(modifiers):
                _backend.keyUp(modifier)
        logger.debug("Combo pressionado: %s", "+".join(keys))

    def run_console(self, command: str) -> None:
        """Abre o console do GMod, digita um comando e o executa.

        Sequencia: abre console -> digita -> Enter (executa) ->
        Enter de novo fecha o console aberto. Tudo so acontece com a
        janela do jogo em foco.

        Args:
            command: Linha de comando ja com o nome interpolado
                (ex: 'spawn_zumbi_cod "joao"').

        Raises:
            GameWindowNotFocusedError: Se o jogo nao esta em foco.
            KeyExecutorUnavailableError: Se nenhum backend foi importado.
        """
        if _backend is None:
            raise KeyExecutorUnavailableError(
                "Instale pydirectinput (Windows) ou pyautogui."
            )
        if not self.is_game_focused():
            raise GameWindowNotFocusedError(
                f"Janela contendo '{self._window_title}' nao esta em foco."
            )

        _backend.press(self._console_key)  # abre o console
        time.sleep(0.12)
        if _backend_name == "pydirectinput":
            # pydirectinput nao digita strings; usa o write do pyautogui
            # se disponivel, senao digita caractere a caractere.
            if _pyautogui_write is not None:
                _pyautogui_write(command, interval=0.01)
            else:  # pragma: no cover - caminho raro
                for ch in command:
                    _backend.press(ch)
        else:
            _backend.write(command, interval=0.01)
        time.sleep(0.08)
        _backend.press("enter")  # executa
        time.sleep(0.05)
        _backend.press("enter")  # fecha o console
        logger.debug("Console executado: %s", command)
