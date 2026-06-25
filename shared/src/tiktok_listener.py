"""Conexao com a live do TikTok e roteamento de eventos.

O Python EXECUTA apenas comandos de chat. Likes, follows e presentes
sao executados pelo Tikfinity; aqui eles apenas alimentam o painel
(toasts e barra de progresso), nunca pressionam teclas.
"""
from __future__ import annotations

import asyncio
import itertools
import logging
import random

from src.command_mapper import CommandMapper
from src.command_queue import CommandQueue
from src.config import Settings
from src.cooldown import CooldownManager
from src.models import ChatCommand, CommandConfig
from src.panel_server import PanelServer

logger = logging.getLogger(__name__)

_BACKOFF_INITIAL = 15.0
_BACKOFF_MAX = 120.0


class TikTokListener:
    """Escuta a live e distribui eventos para fila e painel."""

    def __init__(
        self,
        settings: Settings,
        mapper: CommandMapper,
        cooldowns: CooldownManager,
        queue: CommandQueue,
        panel: PanelServer,
        gift_actions: dict[str, "CommandConfig"] | None = None,
        likes_action: "CommandConfig | None" = None,
        follow_action: "CommandConfig | None" = None,
        join_action: "CommandConfig | None" = None,
        ranking: "object | None" = None,
        nuclear_action: "CommandConfig | None" = None,
    ) -> None:
        self._settings = settings
        self._mapper = mapper
        self._cooldowns = cooldowns
        self._queue = queue
        self._panel = panel
        self._gift_actions = gift_actions or {}
        self._likes_action = likes_action
        self._follow_action = follow_action
        self._join_action = join_action
        self._ranking = ranking
        self._nuclear_action = nuclear_action
        self._likes_current = 0
        self._nuclear_current = 0  # contador separado da barra nuclear
        self._last_liker = "Chat"
        self._joined_users: set[str] = set()  # quem ja entrou nesta sessao

    # ------------------------------------------------------------------
    # Handlers de dominio (independentes da lib TikTokLive — testaveis)
    # ------------------------------------------------------------------

    async def handle_comment(self, user: str, text: str) -> None:
        """Processa uma mensagem de chat: mapeia, valida cooldown, enfileira.

        Args:
            user: Nome de exibicao do viewer.
            text: Conteudo da mensagem.
        """
        config = self._mapper.map(text)
        if config is None:
            return
        if not self._cooldowns.try_acquire(config, user):
            return
        if self._ranking is not None:
            self._ranking.add_chat(user)
            await self._broadcast_ranking()
        await self._queue.put(
            ChatCommand(user=user, config=config, actor=user)
        )
        if config.cooldown_global > 0:
            await self._panel.broadcast(
                {
                    "type": "cooldown",
                    "command": config.trigger,
                    "ready_at": self._cooldowns.ready_at(config.trigger),
                    "duration": config.cooldown_global,
                }
            )

    async def handle_likes(self, count: int, user: str = "") -> None:
        """Acumula likes; ao bater a meta, enfileira o zumbi com o nome.

        O TikTok envia likes em lotes. Quando a meta e cruzada, o
        Python executa a acao de likes (zumbi) passando o nome de quem
        deu o ultimo lote de likes, para o nome flutuar sobre o zumbi.

        Args:
            count: Quantidade de likes recebidos no lote.
            user: Nome de quem enviou este lote de likes.
        """
        if user:
            self._last_liker = user
        self._likes_current += count
        goal = self._settings.likes_goal
        crossed = self._likes_current >= goal
        self._likes_current %= goal

        if crossed and self._likes_action is not None:
            actor = user or self._last_liker
            if self._settings.likes_enabled:
                logger.info("Meta de likes batida por %s -> zumbi", actor)
                await self._queue.put(
                    ChatCommand(
                        user=actor, config=self._likes_action, actor=actor
                    )
                )
            else:
                logger.info("Meta de likes batida por %s (LIKES_ENABLED=false, ignorado)", actor)

        await self._panel.broadcast(
            {
                "type": "likes",
                "current": self._likes_current,
                "goal": goal,
                "triggered": crossed,
                "user": user or self._last_liker,
            }
        )

        # ---- Segunda barra: meta NUCLEAR (independente do zumbi) ----
        if self._nuclear_action is not None:
            nuclear_goal = self._settings.nuclear_goal
            self._nuclear_current += count
            nuclear_crossed = self._nuclear_current >= nuclear_goal
            if nuclear_crossed:
                actor = user or self._last_liker
                logger.info(
                    "META NUCLEAR batida (%d likes) por %s -> bomba nuclear",
                    nuclear_goal, actor,
                )
                await self._queue.put(
                    ChatCommand(
                        user=actor, config=self._nuclear_action, actor=actor
                    )
                )
                self._nuclear_current = 0  # reseta a barra apos explodir

            await self._panel.broadcast(
                {
                    "type": "nuclear",
                    "current": self._nuclear_current,
                    "goal": nuclear_goal,
                    "triggered": nuclear_crossed,
                }
            )

    async def _broadcast_ranking(self) -> None:
        """Envia o Top 5 (live + historico) para os overlays.

        O painel de ranking decide qual mostrar e alterna sozinho.
        Silencioso se o ranking nao estiver ativo.
        """
        if self._ranking is None:
            return
        live = [
            {"nome": e.nome, "pontos": e.pontos, "posicao": e.posicao}
            for e in self._ranking.top_live(5)
        ]
        historico = [
            {"nome": e.nome, "pontos": e.pontos, "posicao": e.posicao}
            for e in self._ranking.top_historico(5)
        ]
        await self._panel.broadcast(
            {"type": "ranking", "live": live, "historico": historico}
        )

    async def handle_join(self, user: str) -> None:
        """Trata alguem entrando na live: spawna personagem com o nome.

        So age se JOIN_ENABLED estiver ligado no .env. Cada pessoa
        spawna apenas uma vez por sessao do script (cooldown "1x por
        live"). Em lives movimentadas entram muitas pessoas, por isso
        esses dois freios sao importantes.

        Args:
            user: Nome de exibicao de quem entrou.
        """
        # Pontos de entrada: 1x por pessoa por sessao, mesmo que o spawn
        # esteja desligado (entrar na live ja vale ponto no ranking).
        primeira_vez = user not in self._joined_users
        if primeira_vez and self._ranking is not None:
            self._ranking.add_join(user)
            await self._broadcast_ranking()

        if not self._settings.join_enabled:
            self._joined_users.add(user)  # marca p/ nao recreditar pontos
            return  # spawn desligado; ignora a parte do personagem
        if self._join_action is None:
            self._joined_users.add(user)
            return
        if user in self._joined_users:
            return  # essa pessoa ja virou personagem nesta sessao
        self._joined_users.add(user)
        logger.info("Entrada na live: %s -> personagem", user)
        await self._queue.put(
            ChatCommand(user=user, config=self._join_action, actor=user)
        )

    async def handle_follow(self, user: str) -> None:
        """Trata um novo seguidor: dispara o fogo (se configurado) e avisa painel.

        Diferente de antes, agora o PYTHON executa o fogo via ponte
        (saiu do Tikfinity). O follow_action vem do commands.json.

        Args:
            user: Nome de exibicao de quem seguiu.
        """
        if self._ranking is not None:
            self._ranking.add_follow(user)
            await self._broadcast_ranking()
        if self._follow_action is not None:
            logger.info("Novo seguidor %s -> fogo", user)
            await self._queue.put(
                ChatCommand(user=user, config=self._follow_action, actor=user)
            )
        await self._panel.broadcast(
            {"type": "social", "kind": "follow", "user": user}
        )

    async def handle_gift(
        self, user: str, gift_name: str, diamantes: int = 0
    ) -> None:
        """Trata um presente recebido.

        Se o presente estiver configurado em "gifts" no commands.json,
        o PYTHON executa a acao (entra na fila, sem cooldown). Caso
        contrario, apenas notifica o painel (Tikfinity executa, se for
        um presente dele).

        Args:
            user: Nome de exibicao do viewer.
            gift_name: Nome do presente como o TikTok envia.
            diamantes: Valor do presente em diamantes (para o ranking).
        """
        # Ranking: presente pontua pelo valor em diamantes (doar pesa mais)
        if self._ranking is not None:
            self._ranking.add_gift(user, diamantes)
            await self._broadcast_ranking()

        config = self._gift_actions.get(gift_name.strip().lower())
        if config is not None:
            logger.info("Presente executavel: %s de %s", gift_name, user)
            await self._queue.put(
                ChatCommand(user=user, config=config, actor=user)
            )
            return
        # Nao casou com nenhum presente configurado: avisa no log com os
        # nomes disponiveis, para facilitar corrigir o gift_name no JSON.
        logger.info(
            "Presente '%s' (de %s) nao esta em 'gifts'. Configurados: %s",
            gift_name, user,
            ", ".join(sorted(self._gift_actions.keys())) or "nenhum",
        )
        await self._panel.broadcast(
            {"type": "social", "kind": "gift", "user": user, "gift": gift_name}
        )

    # ------------------------------------------------------------------
    # Conexao real com o TikTok
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Conecta a live e reconecta com backoff exponencial em quedas."""
        if self._settings.simulation:
            await self._run_simulation()
            return

        from TikTokLive import TikTokLiveClient
        from TikTokLive.client.web.web_settings import WebDefaults
        from TikTokLive.events import (
            CommentEvent,
            ConnectEvent,
            FollowEvent,
            GiftEvent,
            JoinEvent,
            LikeEvent,
        )

        # Chave da API EulerStream: aumenta o limite de conexoes e evita
        # o erro 429 (rate limit). Definida globalmente antes do cliente.
        if self._settings.tiktok_api_key:
            WebDefaults.tiktok_sign_api_key = self._settings.tiktok_api_key
            logger.info("Chave da API EulerStream configurada.")
        else:
            logger.warning(
                "Sem TIKTOK_API_KEY no .env — usando limite gratuito "
                "(sujeito a erro 429 se reconectar muitas vezes)."
            )

        backoff = _BACKOFF_INITIAL
        while True:
            client = TikTokLiveClient(unique_id=self._settings.tiktok_username)

            @client.on(ConnectEvent)
            async def _on_connect(event: ConnectEvent) -> None:
                logger.info("Conectado a live de @%s", event.unique_id)

            @client.on(CommentEvent)
            async def _on_comment(event: CommentEvent) -> None:
                await self.handle_comment(event.user.nickname, event.comment)

            @client.on(LikeEvent)
            async def _on_like(event: LikeEvent) -> None:
                await self.handle_likes(
                    getattr(event, "count", 1) or 1, event.user.nickname
                )

            @client.on(FollowEvent)
            async def _on_follow(event: FollowEvent) -> None:
                await self.handle_follow(event.user.nickname)

            @client.on(JoinEvent)
            async def _on_join(event: JoinEvent) -> None:
                await self.handle_join(event.user.nickname)

            @client.on(GiftEvent)
            async def _on_gift(event: GiftEvent) -> None:
                gift = event.gift
                gift_name = getattr(gift, "name", "") or ""
                user = event.user.nickname
                # valor em diamantes (nomes variam entre versoes da lib)
                diamantes = (
                    getattr(gift, "diamond_count", None)
                    or getattr(gift, "diamondCount", None)
                    or 0
                )

                # Atributos de streak mudam entre versoes da lib. Lemos de
                # forma tolerante; na duvida, NAO descartamos o presente.
                streakable = bool(getattr(gift, "streakable", False))
                streaking = bool(getattr(event, "streaking", False))

                # Log de diagnostico: mostra TODO presente que chega, com o
                # nome exato que o TikTok manda (copie isso para o gift_name).
                logger.info(
                    "GiftEvent recebido: nome='%s' de %s (diamantes=%s, streakable=%s, streaking=%s)",
                    gift_name, user, diamantes, streakable, streaking,
                )

                # Regra: presente com streak so conta quando o streak acaba
                # (evita disparar varias vezes). Presente sem streak conta
                # na hora. Se os atributos vierem estranhos, processa mesmo.
                if streakable and streaking:
                    return  # streak ainda em andamento; espera terminar
                await self.handle_gift(user, gift_name, diamantes)

            try:
                logger.info(
                    "Conectando a @%s...", self._settings.tiktok_username
                )
                # connect() retorna uma asyncio.Task; aguardar a Task
                # bloqueia ate a live encerrar/desconectar. Sem o await
                # na Task, o loop reconectaria imediatamente em loop.
                client_task = await client.connect()
                await client_task
                logger.info("Conexao encerrada (live offline?).")
                backoff = _BACKOFF_INITIAL
                await asyncio.sleep(_BACKOFF_INITIAL)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - reconexao deve sobreviver a tudo
                logger.error(
                    "Conexao com o TikTok caiu; nova tentativa em %.0fs. "
                    "(erro 500 do EulerStream e instabilidade do servico, "
                    "costuma resolver sozinho)",
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _BACKOFF_MAX)

    # ------------------------------------------------------------------
    # Modo simulacao (desenvolvimento sem live no ar)
    # ------------------------------------------------------------------

    async def _run_simulation(self) -> None:
        """Gera eventos falsos para testar fila e painel sem live ativa.

        Os presentes sorteados vem do proprio commands.json (gifts), entao
        a simulacao sempre testa exatamente o que voce configurou — sem
        precisar editar este arquivo ao adicionar um presente novo.
        """
        logger.info("MODO SIMULACAO ativo — gerando eventos falsos")
        fake_users = ["@joao_zoeira", "@ana.gamer", "@pedrocaos", "@lua_fps"]
        fake_comments = [
            "!barril", "!cura", "!drop", "!formiga", "!barco",
            "kkkkk", "boa live!", "!BARRIL", "!barril agora",
        ]
        # nomes reais dos presentes configurados (usa o trigger original,
        # nao a chave em minusculas, pra simular o que o TikTok mandaria)
        gift_names = [cfg.trigger for cfg in self._gift_actions.values()]
        if not gift_names:
            gift_names = ["Rosa"]  # fallback se nao houver presentes no JSON
        logger.info("Simulacao vai sortear presentes: %s", ", ".join(gift_names))

        for tick in itertools.count():
            await asyncio.sleep(random.uniform(1.5, 4.0))
            roll = random.random()
            user = random.choice(fake_users)
            if roll < 0.45:
                await self.handle_comment(user, random.choice(fake_comments))
            elif roll < 0.62:
                await self.handle_likes(random.randint(1, 4), user)
            elif roll < 0.74:
                await self.handle_follow(user)
            elif roll < 0.84:
                await self.handle_join(user)
            else:
                await self.handle_gift(
                    user, random.choice(gift_names),
                    diamantes=random.choice([1, 5, 10, 50, 100, 500]),
                )
            if tick % 20 == 0:
                logger.info("Simulacao rodando (tick %d)", tick)
