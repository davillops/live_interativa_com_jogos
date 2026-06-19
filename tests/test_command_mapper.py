"""Testes do CommandMapper."""
from src.command_mapper import CommandMapper
from src.models import CommandConfig


def make_commands() -> dict[str, CommandConfig]:
    barril = CommandConfig(trigger="!barril", keys=("=",), label="Fogo Mira")
    cura = CommandConfig(trigger="!cura", keys=("-",), label="Vida Máx")
    return {"!barril": barril, "!cura": cura}


class TestCommandMapper:
    def setup_method(self) -> None:
        self.mapper = CommandMapper(make_commands())

    def test_comando_valido(self) -> None:
        config = self.mapper.map("!barril")
        assert config is not None
        assert config.trigger == "!barril"

    def test_case_insensitive(self) -> None:
        assert self.mapper.map("!BARRIL") is not None
        assert self.mapper.map("!BaRrIl") is not None

    def test_comando_com_texto_extra(self) -> None:
        config = self.mapper.map("!cura por favor!!!")
        assert config is not None
        assert config.trigger == "!cura"

    def test_espacos_nas_pontas(self) -> None:
        assert self.mapper.map("   !barril   ") is not None

    def test_mensagem_comum_retorna_none(self) -> None:
        assert self.mapper.map("boa live kkkk") is None

    def test_comando_desconhecido_retorna_none(self) -> None:
        assert self.mapper.map("!nuclear") is None

    def test_vazio_e_so_espacos_retornam_none(self) -> None:
        assert self.mapper.map("") is None
        assert self.mapper.map("   ") is None

    def test_comando_no_meio_da_frase_nao_dispara(self) -> None:
        assert self.mapper.map("manda um !barril ai") is None
