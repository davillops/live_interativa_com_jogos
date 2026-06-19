"""Testes do CooldownManager (relogio fake para determinismo)."""
from src.cooldown import CooldownManager
from src.models import CommandConfig


def make_config(**overrides) -> CommandConfig:
    base = {
        "trigger": "!barril",
        "keys": ("=",),
        "label": "Fogo Mira",
        "cooldown_global": 10.0,
        "cooldown_user": 30.0,
    }
    base.update(overrides)
    return CommandConfig(**base)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class TestCooldownManager:
    def setup_method(self) -> None:
        self.clock = FakeClock()
        self.manager = CooldownManager(clock=self.clock)

    def test_primeira_execucao_passa(self) -> None:
        assert self.manager.try_acquire(make_config(), "ana") is True

    def test_cooldown_global_bloqueia_outro_usuario(self) -> None:
        config = make_config()
        assert self.manager.try_acquire(config, "ana") is True
        self.clock.now += 5  # ainda dentro dos 10s globais
        assert self.manager.try_acquire(config, "joao") is False

    def test_cooldown_global_expira(self) -> None:
        config = make_config()
        self.manager.try_acquire(config, "ana")
        self.clock.now += 11
        assert self.manager.try_acquire(config, "joao") is True

    def test_cooldown_de_usuario_bloqueia_mesmo_usuario(self) -> None:
        config = make_config()
        self.manager.try_acquire(config, "ana")
        self.clock.now += 15  # global (10s) expirou, user (30s) nao
        assert self.manager.try_acquire(config, "ana") is False

    def test_cooldown_de_usuario_expira(self) -> None:
        config = make_config()
        self.manager.try_acquire(config, "ana")
        self.clock.now += 31
        assert self.manager.try_acquire(config, "ana") is True

    def test_bypass_ignora_cooldowns(self) -> None:
        normal = make_config()
        presente = make_config(trigger="!barril", bypass_cooldown=True)
        self.manager.try_acquire(normal, "ana")
        assert self.manager.try_acquire(presente, "ana") is True

    def test_ready_at_reflete_fim_do_cooldown(self) -> None:
        config = make_config()
        self.manager.try_acquire(config, "ana")
        assert self.manager.ready_at("!barril") == 1010.0

    def test_ready_at_zero_para_comando_desconhecido(self) -> None:
        assert self.manager.ready_at("!nada") == 0.0

    def test_comandos_diferentes_nao_interferem(self) -> None:
        barril = make_config()
        cura = make_config(trigger="!cura")
        self.manager.try_acquire(barril, "ana")
        assert self.manager.try_acquire(cura, "ana") is True
