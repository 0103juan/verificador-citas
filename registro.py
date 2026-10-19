"""The official register of Constitutional Court rulings: every sentencia since 1992, from datos.gov.co.

    python registro.py        # downloads data/sentencias.json (about 29,000 rows, one request)

Source: "Sentencias proferidas por la Corte Constitucional" (v2k4-2t8s), published by the Court under
CC BY-SA 4.0. It lists each ruling's identifier, date, type of process and reporting justices; it does not
hold the text.
"""

import json
import sys
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DATASET = "https://www.datos.gov.co/resource/v2k4-2t8s.json"
DATA = Path(__file__).parent / "data" / "sentencias.json"


@dataclass(frozen=True)
class Sentencia:
    clave: str  # "T-760/08", as the register writes it
    fecha: str  # ISO date
    proceso: str
    magistrados: tuple[str, ...]  # reporting justices; a ruling can have more than one


def plano(texto: str) -> str:
    """Lowercase without accents, to compare names that the register and a text write differently."""
    return unicodedata.normalize("NFD", texto.lower()).encode("ascii", "ignore").decode()


def descargar(destino: Path = DATA) -> int:
    query = urllib.parse.urlencode({"$select": "sentencia,fecha_sentencia,proceso,magistrado_a", "$limit": 100000})
    with urllib.request.urlopen(f"{DATASET}?{query}", timeout=120) as respuesta:
        filas = json.load(respuesta)
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")
    return len(filas)


def cargar(origen: Path = DATA) -> dict[str, Sentencia]:
    """The register keyed by the ruling's identifier, normalised the way citas.py normalises a citation."""
    from citas import normalizar  # the one place that decides what two spellings of an identifier have in common

    registro = {}
    for fila in json.loads(origen.read_text(encoding="utf-8")):
        if not fila.get("sentencia"):
            continue
        magistrados = tuple(nombre.strip() for nombre in fila.get("magistrado_a", "").split(";") if nombre.strip())
        sentencia = Sentencia(fila["sentencia"], fila.get("fecha_sentencia", "")[:10], fila.get("proceso", ""), magistrados)
        registro[normalizar(fila["sentencia"])] = sentencia
    return registro


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{descargar()} sentencias en {DATA}")
