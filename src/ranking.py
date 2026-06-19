"""Sistema de ranking/gamificacao da Live Caos.

Mantem dois placares ao mesmo tempo:

* **Live atual** — pontos acumulados desde que o script iniciou. Fica em
  memoria e zera ao reiniciar.
* **Historico** — pontos somados de todas as lives, persistidos em SQLite
  (arquivo local, sem servidor).

Cada interacao (chat, seguir, entrar, presente) credita pontos. Presentes
valem por diamante, entao doar pesa muito mais que comentar.

O modulo nao sabe nada de TikTok nem de rede; recebe chamadas simples
(`add_chat`, `add_gift`, ...) e devolve o Top N. Isso mantem a
responsabilidade unica e facilita testar.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PontosConfig:
    """Quanto vale cada tipo de interacao.

    Presentes nao estao aqui: valem o numero de diamantes vezes
    `gift_multiplier` (calculado na hora, pois varia por presente).
    """

    chat: int = 1
    follow: int = 25
    join: int = 5
    gift_multiplier: int = 1  # pontos = diamantes * este fator


@dataclass
class _Pessoa:
    """Acumulador em memoria para o ranking da live atual."""

    nome: str
    pontos: int = 0
    chat: int = 0
    follows: int = 0
    joins: int = 0
    gifts: int = 0
    diamantes: int = 0


@dataclass
class EntradaRanking:
    """Uma linha do ranking, pronta para exibir."""

    nome: str
    pontos: int
    posicao: int = 0


class Ranking:
    """Gerencia pontos da live atual (memoria) e historico (SQLite)."""

    def __init__(
        self,
        db_path: str | Path = "live_caos.db",
        pontos: PontosConfig | None = None,
    ) -> None:
        """Abre/cria o banco e prepara o placar da sessao.

        Args:
            db_path: Caminho do arquivo SQLite. Criado se nao existir.
            pontos: Tabela de pontos por acao. Usa padroes se omitido.
        """
        self._pontos = pontos or PontosConfig()
        self._db_path = str(db_path)
        # check_same_thread=False: o worker async e o listener podem tocar
        # o banco; protegemos com um lock proprio.
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._live: dict[str, _Pessoa] = {}
        self._criar_tabela()

    # ------------------------------------------------------------------
    # Banco
    # ------------------------------------------------------------------
    def _criar_tabela(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pessoas (
                    nome       TEXT PRIMARY KEY,
                    pontos     INTEGER NOT NULL DEFAULT 0,
                    chat       INTEGER NOT NULL DEFAULT 0,
                    follows    INTEGER NOT NULL DEFAULT 0,
                    joins      INTEGER NOT NULL DEFAULT 0,
                    gifts      INTEGER NOT NULL DEFAULT 0,
                    diamantes  INTEGER NOT NULL DEFAULT 0,
                    atualizado TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            self._conn.commit()

    def _gravar(
        self,
        nome: str,
        pontos: int,
        *,
        chat: int = 0,
        follows: int = 0,
        joins: int = 0,
        gifts: int = 0,
        diamantes: int = 0,
    ) -> None:
        """Soma os valores no historico (UPSERT)."""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO pessoas (nome, pontos, chat, follows, joins,
                                     gifts, diamantes, atualizado)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(nome) DO UPDATE SET
                    pontos    = pontos    + excluded.pontos,
                    chat      = chat      + excluded.chat,
                    follows   = follows   + excluded.follows,
                    joins     = joins     + excluded.joins,
                    gifts     = gifts     + excluded.gifts,
                    diamantes = diamantes + excluded.diamantes,
                    atualizado = datetime('now')
                """,
                (nome, pontos, chat, follows, joins, gifts, diamantes),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Credito de pontos (chamado pelo listener)
    # ------------------------------------------------------------------
    def _live_pessoa(self, nome: str) -> _Pessoa:
        p = self._live.get(nome)
        if p is None:
            p = _Pessoa(nome=nome)
            self._live[nome] = p
        return p

    def add_chat(self, nome: str) -> None:
        """Credita 1 comando de chat."""
        pts = self._pontos.chat
        p = self._live_pessoa(nome)
        p.pontos += pts
        p.chat += 1
        self._gravar(nome, pts, chat=1)

    def add_follow(self, nome: str) -> None:
        """Credita um seguir."""
        pts = self._pontos.follow
        p = self._live_pessoa(nome)
        p.pontos += pts
        p.follows += 1
        self._gravar(nome, pts, follows=1)

    def add_join(self, nome: str) -> None:
        """Credita uma entrada na live."""
        pts = self._pontos.join
        p = self._live_pessoa(nome)
        p.pontos += pts
        p.joins += 1
        self._gravar(nome, pts, joins=1)

    def add_gift(self, nome: str, diamantes: int) -> None:
        """Credita um presente. Pontos = diamantes * multiplicador.

        Args:
            nome: Quem enviou.
            diamantes: Valor do presente em diamantes (>= 0).
        """
        diamantes = max(0, int(diamantes))
        pts = diamantes * self._pontos.gift_multiplier
        if pts <= 0:
            pts = 1  # presente de valor desconhecido ainda conta algo
        p = self._live_pessoa(nome)
        p.pontos += pts
        p.gifts += 1
        p.diamantes += diamantes
        self._gravar(nome, pts, gifts=1, diamantes=diamantes)

    # ------------------------------------------------------------------
    # Leitura dos rankings
    # ------------------------------------------------------------------
    def top_live(self, n: int = 5) -> list[EntradaRanking]:
        """Top N da live atual (memoria)."""
        ordenado = sorted(
            self._live.values(), key=lambda p: p.pontos, reverse=True
        )
        return [
            EntradaRanking(nome=p.nome, pontos=p.pontos, posicao=i + 1)
            for i, p in enumerate(ordenado[:n])
            if p.pontos > 0
        ]

    def top_historico(self, n: int = 5) -> list[EntradaRanking]:
        """Top N de todas as lives (SQLite)."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT nome, pontos FROM pessoas "
                "ORDER BY pontos DESC LIMIT ?",
                (n,),
            )
            linhas = cur.fetchall()
        return [
            EntradaRanking(nome=row[0], pontos=row[1], posicao=i + 1)
            for i, row in enumerate(linhas)
        ]

    def fechar(self) -> None:
        """Fecha a conexao com o banco."""
        with self._lock:
            self._conn.close()
