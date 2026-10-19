"""Finding citations of Constitutional Court rulings in a text, and normalising them.

The same ruling is written many ways: "T-760/08", "T-760 de 2008", "sentencia T 760 del 2008", "SU-214/16",
"C-355/2006", "T-760A/00". normalizar() turns each into one key, "T-760/2008", so that a citation and the
register can be compared.
"""

import re
from dataclasses import dataclass

# Type (SU before the one-letter types), number with an optional letter, then the year after "/", "-" or "de".
PATRON = re.compile(
    r"\b(SU|T|C)\s*-?\s*(\d{1,4})\s*([A-Z])?\s*(?:/|-|\s+de(?:l)?\s+)\s*(\d{4}|\d{2})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Cita:
    texto: str  # as written
    clave: str  # normalised: "T-760/2008"
    inicio: int  # position in the text


def anio_completo(anio: str) -> int:
    """The Court started in 1992: a two-digit year from 92 to 99 is the 1990s, the rest the 2000s."""
    valor = int(anio)
    if len(anio) == 4:
        return valor
    return 1900 + valor if valor >= 92 else 2000 + valor


def normalizar(identificador: str) -> str:
    """One key per ruling, whatever the spelling. Raises ValueError when there is no ruling in the string."""
    encontrada = PATRON.search(identificador)
    if not encontrada:
        raise ValueError(f"no es un identificador de sentencia: {identificador!r}")
    tipo, numero, letra, anio = encontrada.groups()
    return f"{tipo.upper()}-{int(numero)}{(letra or '').upper()}/{anio_completo(anio)}"


def extraer(texto: str) -> list[Cita]:
    """Every citation in the text, in order. The same ruling cited twice appears twice."""
    citas = []
    for encontrada in PATRON.finditer(texto):
        anio = anio_completo(encontrada.group(4))
        if not 1992 <= anio <= 2100:  # "C-1 de 1810" is not a ruling of this Court
            continue
        citas.append(Cita(encontrada.group(0), normalizar(encontrada.group(0)), encontrada.start()))
    return citas
