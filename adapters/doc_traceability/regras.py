"""Lê do `workflow-rules.yaml` fixado os níveis de sizing, os documentos e as transições."""

from pathlib import Path

import yaml


class Regras:
    def __init__(self, raiz: Path):
        arquivo = raiz / "_framework" / "rules" / "workflow-rules.yaml"
        self._dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}

    def _niveis(self) -> list[dict]:
        return (self._dados.get("sizing") or {}).get("levels") or []

    def niveis(self) -> tuple[str, ...]:
        return tuple(nivel["id"] for nivel in self._niveis())

    def documentos(self, nivel: str) -> tuple[str, ...]:
        for item in self._niveis():
            if item["id"] == nivel:
                return tuple(d for d in item.get("documents", []) if not d.endswith("(opcional)"))
        return ()

    def transicao_permitida(self, de: str, para: str) -> bool:
        transicoes = (self._dados.get("status_lifecycle") or {}).get("allowed_transitions") or {}
        return para in (transicoes.get(de) or [])

    def _tipo(self, tipo: str) -> dict | None:
        return (self._dados.get("document_types") or {}).get(tipo)

    def repositorio(self, tipo: str) -> str | None:
        dados = self._tipo(tipo)
        return dados.get("repo") if dados else None

    def pasta(self, tipo: str, codigo: str) -> str:
        return self._tipo(tipo)["folder"].replace("{PROJECT_CODE}", codigo)

    def tipo_do_central(self, sizing: str) -> str | None:
        for tipo in self.documentos(sizing):
            if self.repositorio(tipo) == "central":
                return tipo
        return None
