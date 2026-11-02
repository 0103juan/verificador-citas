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

### Results

One run on 2 November 2026, on Gemini through Vertex AI (the Anthropic key is not on the machine that ran it), one
answer per question, at the models' default temperature:

| Model | Citations | Not in the register | Answers with at least one | Wrong justice | Cost |
|---|---|---|---|---|---|
| `gemini-3.5-flash-lite` (small) | 99 | 15 (15.2 %) | 14 of 30 | 0 | 0.02 USD |
| `gemini-3.5-flash` (large) | 97 | 4 (4.1 %) | 3 of 30 | 0 | 0.38 USD |

Every answer cited something, so no model refused. The small model invents about four times as often as the
large one, and about half of its answers carry at least one ruling that does not exist. The cost includes three
questions asked twice by mistake. The answers are written to `resultados/`, which is not committed.

**I checked the 19 distinct citations flagged as not in the register against the Court's own site**
(`corteconstitucional.gov.co/relatoria/<year>/<ruling>.htm`). All 19 return the site's empty page, while the
rulings in the register return the ruling (three controls: `T-001/22`, `SU-006/23` and `C-355/06`). That matters
because the register has gaps: for 2022, 304 of the 471 tutela numbers are in it. The Court's site does not publish
the missing numbers either, so for these 19 "not in the register" and "does not exist" agree. A ruling that the Court
published somewhere else would still be reported as missing.

What is not measured: an invented citation that happens to match a real number and year, and a real ruling cited for
something it does not say. Both pass. One run per model is also a sample, not a rate: the questions are a first draft
and the gap between the models is the finding, not the exact percentages.

The questions are a first draft and need a review by someone who knows the case law before the numbers mean
anything.

## Run it

```
uv run python registro.py             # downloads the register (one request, about 29,000 rows)
uv run python verificar.py texto.txt  # or pipe the text in
uv run pytest                         # 14 tests, no network and no model
ANTHROPIC_API_KEY=... uv run python benchmark.py --tier small
PROVIDER=vertex GOOGLE_CLOUD_PROJECT=... uv run python benchmark.py --tier large   # the same on Gemini
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
