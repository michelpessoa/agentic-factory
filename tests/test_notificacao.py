import json

import pytest

from fabrica import notificacao
from fabrica.notificacao import ConfiguracaoInvalida, Email, Notificador, Teams, carregar_canais

CONFIG = """
[email]
servidor = "smtp.exemplo.com"
usuario = "fabrica@exemplo.com"
senha = "segredo"
para = ["owner@exemplo.com"]

[teams]
url = "https://exemplo.webhook.office.com/abc"
"""


def config(tmp_path, texto=CONFIG, modo=0o600):
    caminho = tmp_path / "notificacao.toml"
    caminho.write_text(texto)
    caminho.chmod(modo)
    return caminho


def test_sem_arquivo_nao_ha_canal(tmp_path):
    assert carregar_canais(tmp_path / "nao-existe.toml") == []


def test_carrega_email_e_teams(tmp_path):
    email, teams = carregar_canais(config(tmp_path))
    assert isinstance(email, Email) and email.porta == 587 and email.para == ["owner@exemplo.com"]
    assert isinstance(teams, Teams) and teams.url.startswith("https://")


@pytest.mark.parametrize("modo", [0o640, 0o604, 0o660])
def test_recusa_arquivo_legivel_por_outros(tmp_path, modo):
    with pytest.raises(ConfiguracaoInvalida, match="chmod 600"):
        carregar_canais(config(tmp_path, modo=modo))


def test_recusa_teams_sem_https(tmp_path):
    with pytest.raises(ConfiguracaoInvalida, match="https"):
        carregar_canais(config(tmp_path, '[teams]\nurl = "http://exemplo.com/x"\n'))


def test_recusa_campo_faltando(tmp_path):
    with pytest.raises(ConfiguracaoInvalida, match="senha"):
        carregar_canais(
            config(tmp_path, '[email]\nservidor = "s"\nusuario = "u"\npara = ["a@b"]\n')
        )


def test_recusa_email_sem_destinatario(tmp_path):
    texto = '[email]\nservidor = "s"\nusuario = "u"\nsenha = "x"\npara = []\n'
    with pytest.raises(ConfiguracaoInvalida, match="para"):
        carregar_canais(config(tmp_path, texto))


def test_recusa_toml_invalido(tmp_path):
    with pytest.raises(ConfiguracaoInvalida):
        carregar_canais(config(tmp_path, "[email\n"))


ENVIADOS = []


class SmtpFalso:
    def __init__(self, servidor, porta, timeout):
        self.conexao = (servidor, porta)
        self.passos = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        self.passos.append("starttls")

    def login(self, usuario, senha):
        assert self.passos == ["starttls"], "login antes de cifrar a conexão"
        self.passos.append(("login", usuario, senha))

    def send_message(self, email):
        ENVIADOS.append((self.conexao, self.passos, email))


def test_email_cifra_antes_do_login_e_envia(monkeypatch):
    ENVIADOS.clear()
    monkeypatch.setattr(notificacao.smtplib, "SMTP", SmtpFalso)
    Email("smtp.exemplo.com", 587, "f@e.com", "segredo", ["o@e.com", "p@e.com"]).enviar(
        "SDD-0001: PARADA_LIMITE. gates reprovados"
    )
    ((conexao, passos, email),) = ENVIADOS
    assert conexao == ("smtp.exemplo.com", 587)
    assert passos == ["starttls", ("login", "f@e.com", "segredo")]
    assert email["To"] == "o@e.com, p@e.com"
    assert "PARADA_LIMITE" in email["Subject"]
    assert "gates reprovados" in email.get_content()


def test_teams_envia_adaptive_card(monkeypatch):
    pedidos = []

    class Resposta:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def urlopen(pedido, timeout):
        pedidos.append(pedido)
        return Resposta()

    monkeypatch.setattr(notificacao.urllib.request, "urlopen", urlopen)
    Teams("https://exemplo.webhook.office.com/abc").enviar("SDD-0001: PAUSADA_DECISAO")
    (pedido,) = pedidos
    assert pedido.get_method() == "POST"
    anexo = json.loads(pedido.data)["attachments"][0]
    assert anexo["contentType"] == "application/vnd.microsoft.card.adaptive"
    textos = [bloco["text"] for bloco in anexo["content"]["body"]]
    assert "SDD-0001: PAUSADA_DECISAO" in textos


class CanalFalso:
    def __init__(self, falha=None):
        self.falha = falha
        self.mensagens = []

    def enviar(self, mensagem):
        if self.falha:
            raise self.falha
        self.mensagens.append(mensagem)


def test_falha_de_canal_fica_no_log_sem_segredo_e_nao_para(tmp_path):
    log = tmp_path / "status.log"
    quebrado = CanalFalso(OSError("https://exemplo.webhook.office.com/segredo recusou"))
    bom = CanalFalso()
    Notificador(log, toast=False, canais=[quebrado, bom]).avisar("SDD-0001: PARADA_LIMITE")
    assert bom.mensagens == ["SDD-0001: PARADA_LIMITE"]
    texto = log.read_text()
    assert "SDD-0001: PARADA_LIMITE" in texto
    assert "falha ao avisar por CanalFalso: OSError" in texto
    assert "segredo" not in texto
