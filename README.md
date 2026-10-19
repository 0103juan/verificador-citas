# verificador-citas

Checks every citation of a Colombian Constitutional Court ruling in a text against the Court's official register,
and measures how often a language model invents them.

A model asked about Colombian constitutional law answers with citations such as "T-760 de 2008". Some of those
rulings exist and some do not, and the invented ones look exactly like the real ones. A lawyer, a student or a
legal assistant built on a model cannot tell which is which without looking each one up. This tool looks them up.

```
$ python verificar.py ejemplo.txt
existe     T-760 de 2008 -> T-760/08, 2008-07-31, Tutela
existe     C-355 de 2006 -> C-355/06, 2006-05-10, Demanda de inconstitucionalidad
           PONENTE NO COINCIDE: el texto dice 'Jorge Iván Palacio'; fue Clara Inés Vargas Hernández; Jaime Araujo Rentería
NO EXISTE  SU-1184 de 2021; con ese número existen: SU-1184/01
```

That output is a real run against the register, on [ejemplo.txt](ejemplo.txt), a paragraph written for the
example. The SU-1184 de 2021 was made up, and the Court did issue an SU-1184, in 2001. The C-355 de 2006 is
real, and the justice named next to it is not one of its reporting justices.

## Why this is worth doing

A 2026 survey of legal NLP benchmarks ([arXiv 2610.03639](https://arxiv.org/html/2610.03639)) found 41 published
since 2018, of which six cover Latin America. All six are about Brazil and in Portuguese, and the authors' own
Colombian benchmark is multiple choice. I found nothing that measures, in Spanish and against the official
source, whether the rulings a model cites exist.

Checking existence does not need the rulings' text, only the register. The Court publishes that register on
datos.gov.co.

## What it checks

- **Existence.** Every citation is normalised (`T-760/08`, `T-760 de 2008`, `sentencia T 760 del 2008` and
  `T-760/2008` are the same ruling) and looked up among the 29,474 rulings from 1992 to August 2026.
- **The usual shape of an invented citation.** When a ruling does not exist, the report lists the same type and
  number in other years. A real number with the wrong year is the most common fabrication, and the list shows
  which ruling was probably meant.
- **The reporting justice,** when the text names one next to the citation ("M.P. Manuel José Cepeda"). Any of
  the ruling's justices counts, and a partial name matches.
- **Exit code 1** when anything does not check out, so it can gate a pipeline that drafts legal text.

Checked against the full register on 18 October 2026: 29,474 rows, 29,474 distinct keys after normalisation,
none unparseable.

## The benchmark

`benchmark.py` asks a model the questions in `preguntas.jsonl` (30, on well-known areas of constitutional
case law), asks it to cite the rulings behind its answer and checks every citation. It reports:

- how many citations there were;
- the share that do not exist;
- the citations that name the wrong justice;
- how many answers contain at least one invented ruling;
- how many answers cite nothing.

**It has not been run yet.** The estimate is about 0.06 USD for a run on the small model and 0.13 USD on the
large one. That comes from list prices and answers of about 400 tokens; it was not measured. Calls go through
[model-gateway](https://github.com/0103juan/model-gateway), so a repeated run is free and a run stops at 1 USD.

The questions are a first draft and need a review by someone who knows the case law before the numbers mean
anything.

## Run it

```
uv run python registro.py             # downloads the register (one request, about 29,000 rows)
uv run python verificar.py texto.txt  # or pipe the text in
uv run pytest                         # 14 tests, no network and no model
ANTHROPIC_API_KEY=... uv run python benchmark.py --tier small
```

## Limits

- **Existence, not content.** A ruling that exists but does not say what the text claims passes. Checking the
  content needs the rulings' text. The Court's site serves it through an application whose API is not
  published, so this project does not download it. The next step is to ask the Court's Relatoría for bulk
  access, or to work from a corpus that has the texts under a licence that allows it.
- **Only the Constitutional Court's sentencias.** Autos, the Council of State and the Supreme Court are not in
  this register.
- The register is as fresh as its last update (7 September 2026, covering rulings up to August 2026).
- Citations written in a way the pattern does not cover ("la sentencia de tutela 760 de ese año") are missed.
  They are not reported as invented, just not seen.

## Data and licence

The register is "Sentencias proferidas por la Corte Constitucional" (dataset `v2k4-2t8s` on datos.gov.co),
published by the Corte Constitucional de Colombia under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). It is downloaded by `registro.py` and not
included in this repository.

The code is MIT.
