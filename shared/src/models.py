"""Modelos de dominio do sistema de live interativa."""
from __future__ import annotations

from dataclasses import dataclass, field
from time import time


@dataclass(frozen=True)
class CommandConfig:
    """Configuracao de uma interacao mapeada para acao no jogo.

    A acao pode ser de tres tipos (verificados nesta ordem de prioridade):
    - Arquivo (``file``): escreve "evento|nome" na fila lida pelo addon
      Lua. NAO abre console nem rouba foco. Use ``{nome}`` opcional.
      E o modo recomendado, sobretudo para eventos com nome do doador.
    - Console (``console``): digita um comando no console do GMod. Abre o
      console na tela; use apenas se nao houver alternativa.
    - Teclas (``keys``): pressiona uma tecla/combo (depende de bind).

    Attributes:
        trigger: Texto que dispara (ex: "!barril") ou nome do presente.
        keys: Sequencia de teclas, ou tupla vazia se usar outro modo.
        console: Comando de console com {nome} opcional, ou "".
        file: Identificador do evento escrito na fila do addon Lua
            (ex: "zumbi"). Pode conter {nome}, mas em geral o nome vai
            no campo separado da linha "evento|nome".
        label: Rotulo exibido no painel (ex: "Fogo Mira").
        emoji: Emoji exibido junto ao rotulo no toast do painel.
        cooldown_global: Segundos ate o comando poder ser usado de novo
            por qualquer pessoa. 0 desativa.
        cooldown_user: Segundos ate o MESMO usuario poder repetir o
            comando. 0 desativa.
        bypass_cooldown: Se True, ignora cooldowns (usado por presentes).
    """

    trigger: str
    keys: tuple[str, ...] = ()
    console: str = ""
    file: str = ""
    label: str = ""
    emoji: str = ""
    cooldown_global: float = 0.0
    cooldown_user: float = 0.0
    bypass_cooldown: bool = False

    @property
    def uses_file(self) -> bool:
        """True se a acao e via ponte por arquivo (modo recomendado)."""
        return bool(self.file)

    @property
    def uses_console(self) -> bool:
        """True se a acao e via console (digitar texto) em vez de teclas."""
        return bool(self.console)


@dataclass(frozen=True)
class ChatCommand:
    """Comando ja validado, aguardando execucao na fila.

    Attributes:
        user: Nome de exibicao do viewer que enviou o comando.
        config: Configuracao do comando a executar.
        actor: Nome a inserir no placeholder {nome} de comandos de
            console. Em geral igual a ``user``; para meta de likes e o
            nome de quem cruzou a meta.
        created_at: Epoch (segundos) de quando o comando entrou na fila.
    """

    user: str
    config: CommandConfig
    actor: str = ""
    created_at: float = field(default_factory=time)
