import importlib.util
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent.parent / "scripts" / "gerar_token.py"
spec = importlib.util.spec_from_file_location("gerar_token", ARQUIVO)
gerar_token = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gerar_token)


def test_extrai_token_com_cores_e_quebra_de_linha():
    saida = "Seu token:\r\n\x1b[32msk-ant-oat01-abc\r\ndef_-1\x1b[0m\r\n\r\nGuarde com cuidado.\r\n"
    assert gerar_token.extrair_token(saida) == "sk-ant-oat01-abcdef_-1"


def test_ignora_codigo_do_navegador():
    assert gerar_token.extrair_token("Cole o código: abc123#def456\r\n") is None


def test_token_e_o_ultimo_impresso():
    saida = "sk-ant-oat01-antigo\n\nexemplo\n\nsk-ant-oat01-novo\n"
    assert gerar_token.extrair_token(saida) == "sk-ant-oat01-novo"
