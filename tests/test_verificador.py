import json

import pytest

from citas import anio_completo, extraer, normalizar
from registro import cargar
from verificar import verificar

FILAS = [
    {"sentencia": "T-760/08", "fecha_sentencia": "2008-07-31T00:00:00.000", "proceso": "Tutela", "magistrado_a": "Manuel José Cepeda Espinosa"},
    {"sentencia": "T-760/98", "fecha_sentencia": "1998-12-07T00:00:00.000", "proceso": "Tutela", "magistrado_a": "Antonio Barrera Carbonell"},
    {"sentencia": "T-760A/00", "fecha_sentencia": "2000-06-22T00:00:00.000", "proceso": "Tutela", "magistrado_a": "Alejandro Martínez Caballero"},
    {"sentencia": "C-355/06", "fecha_sentencia": "2006-05-10T00:00:00.000", "proceso": "Demanda de inconstitucionalidad", "magistrado_a": "Jaime Araújo Rentería; Clara Inés Vargas Hernández"},
    {"sentencia": "SU-214/16", "fecha_sentencia": "2016-04-28T00:00:00.000", "proceso": "Tutela", "magistrado_a": "Alberto Rojas Ríos"},
]


@pytest.fixture
def registro(tmp_path):
    archivo = tmp_path / "sentencias.json"
    archivo.write_text(json.dumps(FILAS, ensure_ascii=False), encoding="utf-8")
    return cargar(archivo)


@pytest.mark.parametrize("escrito", ["T-760/08", "T-760 de 2008", "sentencia T 760 del 2008", "T-760/2008", "t-760-08"])
def test_the_spellings_of_one_ruling_share_a_key(escrito):
    assert normalizar(escrito) == "T-760/2008"


def test_a_letter_and_the_two_letter_type_are_kept():
    assert normalizar("T-760A/00") == "T-760A/2000" and normalizar("SU-214 de 2016") == "SU-214/2016"


def test_two_digit_years_start_with_the_court():
    assert (anio_completo("92"), anio_completo("99"), anio_completo("08"), anio_completo("26")) == (1992, 1999, 2008, 2026)


def test_citations_are_found_in_running_text():
    texto = "Como dijo la Corte en la sentencia T-760 de 2008 y reiteró en la SU-214/16, y no en el artículo 86 de 1991."
    assert [cita.clave for cita in extraer(texto)] == ["T-760/2008", "SU-214/2016"]


def test_a_real_citation_exists_with_its_date_and_process(registro):
    [resultado] = verificar("La sentencia T-760 de 2008 ordenó reestructurar el sistema de salud.", registro)
    assert resultado.existe and resultado.sentencia.fecha == "2008-07-31" and resultado.sentencia.proceso == "Tutela"


def test_an_invented_year_is_caught_and_the_real_ones_are_offered(registro):
    [resultado] = verificar("Según la T-760 de 2011, ...", registro)
    assert not resultado.existe and resultado.otros_anios == ("T-760/08", "T-760/98")


def test_a_number_never_used_is_caught(registro):
    [resultado] = verificar("Como estableció la C-9999 de 2019, ...", registro)
    assert not resultado.existe and resultado.otros_anios == ()


def test_the_reporting_justice_is_checked_when_the_text_names_one(registro):
    bien, mal = verificar("T-760/08 (M.P. Manuel José Cepeda) y C-355/06, M.P. Jorge Iván Palacio.", registro)
    assert bien.ponente_coincide is True and mal.ponente_coincide is False


def test_one_of_several_justices_is_enough(registro):
    [resultado] = verificar("C-355 de 2006, magistrada ponente: Clara Inés Vargas", registro)
    assert resultado.ponente_coincide is True


def test_the_summary_counts_invented_citations_per_question():
    from benchmark import resumen

    filas = [
        {"citas": [{"existe": True, "ponente_coincide": None}, {"existe": False, "ponente_coincide": None}]},
        {"citas": [{"existe": True, "ponente_coincide": False}]},
        {"citas": []},
    ]
    assert resumen(filas) == {"preguntas": 3, "citas": 3, "inexistentes": 1, "tasa_inexistentes": 1 / 3,
                              "ponente_equivocado": 1, "preguntas_con_alguna_inventada": 1, "preguntas_sin_citas": 1}
