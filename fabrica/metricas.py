"""Métricas da comparação de decisores: funções puras, sem modelo nem rede."""

from math import comb, sqrt

from fabrica.roteamento import ORDEM_DE_RISCO


def wilson(acertos: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confiança de 95% para uma proporção, estável com amostra pequena."""
    if total == 0:
        return (0.0, 1.0)
    p = acertos / total
    denominador = 1 + z**2 / total
    centro = (p + z**2 / (2 * total)) / denominador
    margem = z * sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominador
    return (max(0.0, centro - margem), min(1.0, centro + margem))


def ece(pares: list[tuple[float, bool]], faixas: int = 10) -> float:
    """Erro de calibração: distância média entre a confiança declarada e o acerto observado."""
    if not pares:
        return 0.0
    grupos: dict[int, list[tuple[float, bool]]] = {}
    for confianca, acerto in pares:
        grupos.setdefault(min(int(confianca * faixas), faixas - 1), []).append((confianca, acerto))
    return sum(
        abs(sum(c for c, _ in g) / len(g) - sum(a for _, a in g) / len(g)) * len(g)
        for g in grupos.values()
    ) / len(pares)


def brier(pares: list[tuple[float, bool]]) -> float:
    """Erro quadrático da confiança em relação ao acerto. Menor é melhor."""
    if not pares:
        return 0.0
    return sum((c - float(a)) ** 2 for c, a in pares) / len(pares)


def mcnemar_exato(so_a_acertou: int, so_b_acertou: int) -> float:
    """Valor-p bilateral exato para dois classificadores nos mesmos casos."""
    n = so_a_acertou + so_b_acertou
    if n == 0:
        return 1.0
    cauda = sum(comb(n, k) for k in range(min(so_a_acertou, so_b_acertou) + 1)) / 2**n
    return min(1.0, 2 * cauda)


def resumir(respostas: list[dict], limiar: float) -> dict:
    """Resume respostas `{esperado, risco, confianca, ambiguo}` para um limiar.

    O erro que importa é a subestimação aceita sem humano: risco real maior que o previsto, com
    confiança acima do limiar. Caso ambíguo não entra no acerto: o gabarito ali é uma aposta.
    """
    claros = [r for r in respostas if not r.get("ambiguo")]
    aceitas = [r for r in claros if r["confianca"] >= limiar]
    corretas = [r for r in aceitas if r["risco"] == r["esperado"]]
    subestimadas = [
        r for r in aceitas if ORDEM_DE_RISCO[r["risco"]] < ORDEM_DE_RISCO[r["esperado"]]
    ]
    ambiguos = [r for r in respostas if r.get("ambiguo")]
    return {
        "limiar": limiar,
        "casos": len(claros),
        "aceitas": len(aceitas),
        "cobertura": len(aceitas) / len(claros) if claros else 0.0,
        "acerto_aceitas": len(corretas) / len(aceitas) if aceitas else 0.0,
        "subestimadas": sorted(r["id"] for r in subestimadas),
        "ambiguos_ao_humano": sum(r["confianca"] < limiar for r in ambiguos),
        "ambiguos": len(ambiguos),
    }
