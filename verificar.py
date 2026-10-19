"""Checks every citation of a Constitutional Court ruling in a text against the official register.

    python verificar.py respuesta.txt        # or the text on standard input
    exit code 1 when a citation does not exist, so it can gate a pipeline

For each citation it says whether the ruling exists. When it does not, it says whether the same type and number
exist in another year, which is the usual shape of an invented citation: a real-looking number with the wrong
year, or a number that was never used. When the text names a reporting justice next to the citation
("M.P. Manuel José Cepeda"), it also checks that the justice is one of the ruling's.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from citas import Cita, extraer
from registro import Sentencia, cargar, plano

# "M.P." or "magistrado ponente" followed by a name, close after the citation.
PONENTE = re.compile(r"(?:M\.\s?P\.|magistrad[oa] ponente:?)\s*([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.]*(?:\s+[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ.]*){0,4})")
VENTANA = 120  # characters after a citation in which a reporting justice is looked for


@dataclass(frozen=True)
class Resultado:
    cita: Cita
    existe: bool
    sentencia: Sentencia | None
    otros_anios: tuple[str, ...]  # the same type and number in other years, when the citation does not exist
    ponente_citado: str | None
    ponente_coincide: bool | None  # None when the text names no justice


def verificar(texto: str, registro: dict[str, Sentencia]) -> list[Resultado]:
    por_numero: dict[str, list[str]] = {}
    for clave in registro:
        por_numero.setdefault(clave.split("/")[0], []).append(registro[clave].clave)

    resultados = []
    for cita in extraer(texto):
        sentencia = registro.get(cita.clave)
        cercano = PONENTE.search(texto[cita.inicio + len(cita.texto): cita.inicio + len(cita.texto) + VENTANA])
        ponente = cercano.group(1).strip() if cercano else None
        coincide = None
        if ponente and sentencia:
            # A name matches when every word written is in one of the ruling's justices: "Cepeda" and
            # "Manuel José Cepeda" both match "Manuel José Cepeda Espinosa".
            palabras = plano(ponente).split()
            coincide = any(all(palabra in plano(magistrado).split() for palabra in palabras) for magistrado in sentencia.magistrados)
        otros = () if sentencia else tuple(sorted(por_numero.get(cita.clave.split("/")[0], [])))
        resultados.append(Resultado(cita, sentencia is not None, sentencia, otros, ponente, coincide))
    return resultados


def informe(resultados: list[Resultado]) -> str:
    lineas = []
    for r in resultados:
        if not r.existe:
            pista = f"; con ese número existen: {', '.join(r.otros_anios)}" if r.otros_anios else "; ese número no existe en ningún año"
            lineas.append(f"NO EXISTE  {r.cita.texto}{pista}")
            continue
        linea = f"existe     {r.cita.texto} -> {r.sentencia.clave}, {r.sentencia.fecha}, {r.sentencia.proceso}"
        if r.ponente_coincide is False:
            linea += f"\n           PONENTE NO COINCIDE: el texto dice {r.ponente_citado!r}; fue {'; '.join(r.sentencia.magistrados)}"
        lineas.append(linea)
    return "\n".join(lineas) or "(no hay citas de sentencias en el texto)"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")  # Windows reads a pipe as cp1252 otherwise, and accents break
    texto = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else sys.stdin.read()
    resultados = verificar(texto, cargar())
    print(informe(resultados))
    sys.exit(1 if any(not r.existe or r.ponente_coincide is False for r in resultados) else 0)
