"""Controle da comparação: o modelo responde bem no exemplo do autor e em formato mais favorável?

Escrito depois de ver o resultado das variantes declaradas, então é exploratório e não entra na
comparação principal. Serve para separar "modelo fraco nesta tarefa" de "defeito no meu uso".
"""

import json
import sys

from huggingface_hub import snapshot_download
from strands_decider.infer import load_engine
from strands_decider.schema import ChoiceQuestion, NoulQuestion
from worker import MODELO, REGUA_PT, REVISAO

PERGUNTA_ALTO = (
    "A tarefa envolve autenticação, autorização, dado pessoal, dinheiro, migração de dados, "
    "deploy ou mais de um domínio?"
)
CONTROLES = [
    ("Help! My payouts have been failing for 3 days! ", "Which team?", "billing,sales,retail"),
    ("Meu pagamento falhou três vezes e fui cobrado em dobro.", "Qual equipe?", "cobranca,vendas"),
    ("Quero comprar mais licenças para a minha empresa.", "Qual equipe?", "cobranca,vendas"),
]


def main() -> None:
    motor = load_engine(snapshot_download(MODELO, revision=REVISAO), device="cpu")
    for estado, pergunta, opcoes in CONTROLES:
        criterios = {opcao: "" for opcao in opcoes.split(",")}
        resposta = motor.ask(
            estado, {"q": ChoiceQuestion(instructions=pergunta, criteria=criterios)}
        ).answers["q"]
        linha = {"controle": estado, "choice": resposta.choice, "confianca": resposta.confidence}
        print(json.dumps(linha, ensure_ascii=False), flush=True)
    with open(sys.argv[1], encoding="utf-8") as arquivo:
        casos = json.load(arquivo)
    for caso in casos:
        dados = json.loads(caso["estado"])
        aceites = " ".join(r["aceite"] for r in dados["requisitos"])
        texto = f"{dados['titulo']}. {dados['resumo']} {aceites}"
        perguntas = {
            "noul": NoulQuestion(instructions=PERGUNTA_ALTO),
            "choice": ChoiceQuestion(instructions="Qual é o risco da tarefa?", criteria=REGUA_PT),
        }
        respostas = motor.ask(texto, perguntas).answers
        print(
            json.dumps(
                {
                    "id": caso["id"],
                    "p_alto": respostas["noul"].noul,
                    "choice": respostas["choice"].choice,
                    "confianca": respostas["choice"].confidence,
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
