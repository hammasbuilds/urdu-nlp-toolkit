# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-09-24

First release.

### Added

- `normalize()` — Arabic↔Urdu codepoint unification, diacritics, tatweel, zero-width
  characters, digits and punctuation. Unicode NFC does **not** merge `U+064A` ARABIC YEH
  with `U+06CC` FARSI YEH, because they are genuinely different letters used by different
  languages, which is why the problem survives the normalisation people assume handles it.
- `words()` / `sentences()` — tokenisation whose letter ranges skip each Urdu punctuation
  codepoint individually. Urdu punctuation sits *inside* the Arabic block, so the obvious
  range swallows `،` `؟` `۔` into word tokens.
- `transliterate_to_urdu()` / `transliterate_to_roman()` / `transliterate_with_confidence()`
  — with per-token provenance, so a caller can tell a lexicon lookup from a rule guess.
- `STOPWORDS` (115 entries) with `NEGATION` held **separately**. A stopword list that
  deletes `نہیں` inverts every sentiment label.
- `docs/CORPUS.md` — every claim measured against 84,581 BBC Urdu articles (44.7M tokens):
  **one article in eleven** carries a substituted Arabic codepoint; the stopword list
  covers **41.4%** of tokens; transliteration round-trips **44.7%** with the default and
  **61.2%** with `insert_short_vowels=False`.
- `scripts/measure_corpus.py` — reproduces all of it on any corpus.
- `py.typed`, so type checkers see the annotations instead of returning `Any`.

### Fixed

- Urdu fed to the Roman→Urdu direction was returned untouched but labelled `rules`, as
  though the rule engine had resolved it, with `lexicon_coverage` reading `0.0`. Tokens
  already in Urdu script now report `already-urdu` and are excluded from the coverage
  denominator.
- `pytest` failed from a fresh clone with `ModuleNotFoundError`. CI installed the package
  first, so CI was green while every clone was broken.
- The README documented `pip install urdu-nlp-toolkit`, which returned 404.

[0.1.0]: https://github.com/hammasbuilds/urdunlp/releases/tag/v0.1.0
