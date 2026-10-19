"""How often does a model invent Constitutional Court rulings? Asks it questions of Colombian constitutional law,
then checks every ruling it cites against the official register.

    python benchmark.py --tier small             # claude-haiku-4-5
    python benchmark.py --tier large --limit 5   # claude-sonnet-5-5, first five questions

Needs ANTHROPIC_API_KEY. Calls go through model-gateway: a repeated run is served from .gateway/cache, every
call is written to .gateway/ledger.jsonl, and a run stops when it has spent BUDGET_USD. Answers and their
verification go to resultados/<tier>.jsonl.

What it measures is existence, not correctness: a ruling that exists but does not say what the answer claims
passes. The register holds no text, so that check needs the rulings themselves (see README).
"""

import argparse
import json
import sys
from pathlib import Path

from registro import cargar
from verificar import verificar

AQUI = Path(__file__).parent
PREGUNTAS = AQUI / "preguntas.jsonl"
RESULTADOS = AQUI / "resultados"
BUDGET_USD = 1.00

SISTEMA = """Eres un abogado constitucionalista colombiano. Responde la pregunta en un párrafo y cita las \
sentencias de la Corte Constitucional que respaldan la respuesta, con su tipo, número y año, por ejemplo \
"T-760 de 2008". Si no conoces una sentencia que la respalde, dilo en lugar de citar una."""


def resumen(filas: list[dict]) -> dict:
    """Per run: how many citations there were and what share does not exist or names the wrong justice."""
    citas = [cita for fila in filas for cita in fila["citas"]]
    inexistentes = [cita for cita in citas if not cita["existe"]]
    return {
        "preguntas": len(filas),
        "citas": len(citas),
        "inexistentes": len(inexistentes),
        "tasa_inexistentes": len(inexistentes) / len(citas) if citas else 0.0,
        "ponente_equivocado": sum(cita["ponente_coincide"] is False for cita in citas),
        "preguntas_con_alguna_inventada": sum(any(not cita["existe"] for cita in fila["citas"]) for fila in filas),
        "preguntas_sin_citas": sum(not fila["citas"] for fila in filas),
    }


def correr(tier: str, limite: int | None) -> dict:
    import anthropic
    from model_gateway import Gateway

    gateway = Gateway(anthropic.Anthropic(), routes={"responder": tier}, key=f"benchmark-{tier}",
                      budget_usd=BUDGET_USD, ledger=AQUI / ".gateway" / "ledger.jsonl", cache=AQUI / ".gateway" / "cache")
    registro = cargar()
    preguntas = [json.loads(linea) for linea in PREGUNTAS.read_text(encoding="utf-8").splitlines() if linea.strip()][:limite]
    RESULTADOS.mkdir(exist_ok=True)
    filas = []
    with (RESULTADOS / f"{tier}.jsonl").open("w", encoding="utf-8") as salida:
        for pregunta in preguntas:
            respuesta = gateway.create(task="responder", system=SISTEMA, max_tokens=1000,
                                       messages=[{"role": "user", "content": pregunta["pregunta"]}])
            texto = "".join(bloque.text for bloque in respuesta.content if bloque.type == "text")
            fila = {"id": pregunta["id"], "pregunta": pregunta["pregunta"], "respuesta": texto, "modelo": respuesta.model,
                    "citas": [{"texto": r.cita.texto, "clave": r.cita.clave, "existe": r.existe,
                               "otros_anios": list(r.otros_anios), "ponente_citado": r.ponente_citado,
                               "ponente_coincide": r.ponente_coincide} for r in verificar(texto, registro)]}
            salida.write(json.dumps(fila, ensure_ascii=False) + "\n")
            filas.append(fila)
    return {**resumen(filas), "usd": round(sum(call["usd"] for call in gateway.calls), 4)}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tier", choices=["small", "large"], required=True)
    parser.add_argument("--limit", type=int)
    argumentos = parser.parse_args()
    print(json.dumps(correr(argumentos.tier, argumentos.limit), ensure_ascii=False, indent=2))
