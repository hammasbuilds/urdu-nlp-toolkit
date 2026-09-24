<h1 align="center">urdunlp (Python · Unicode normalisation · transliteration)</h1>
<p align="center"><i>Urdu and Roman Urdu text processing. Pure Python, zero dependencies, no model downloads</i></p>

<p align="center">
  <a href="#why-this-exists">Why this exists</a> &middot;
  <a href="#what-it-does">What it does</a> &middot;
  <a href="#install">Install</a> &middot;
  <a href="https://github.com/hammasbuilds/urdunlp/blob/main/docs/CORPUS.md">Measured on 84,581 articles</a> &middot;
  <a href="#known-limits">Known limits</a> &middot;
  <a href="#problems-hit-while-building-this">Problems hit</a>
</p>

<p align="center">
  <a href="https://github.com/hammasbuilds/urdunlp/actions/workflows/ci.yml"><img src="https://github.com/hammasbuilds/urdunlp/actions/workflows/ci.yml/badge.svg" alt="ci"></a>
  <a href="https://pypi.org/project/urdunlp/"><img src="https://img.shields.io/pypi/v/urdunlp" alt="pypi"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="python">
  <img src="https://img.shields.io/badge/dependencies-zero-success" alt="deps">
  <img src="https://img.shields.io/badge/model%20downloads-none-success" alt="downloads">
  <a href="https://github.com/hammasbuilds/urdunlp/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="license"></a>
</p>

---

## Why this exists

```mermaid
flowchart LR
    I["raw Urdu or<br/>Roman Urdu text"] --> N["normalise<br/>Unicode, diacritics, digits"]
    N --> T["transliterate<br/>Roman to Urdu script"]
    N --> W["word segmentation"]
    T --> O["clean, consistent text"]
    W --> O

    style O fill:#16a34a,color:#fff
```

**Zero dependencies and no model downloads.** Urdu tooling usually assumes a GPU and a
multi-gigabyte model; most preprocessing does not need either, and requiring them puts the
language behind a hardware barrier that English does not have.


Urdu is the national language of a country of 240 million people, and the tooling for
it is close to nonexistent. Every Urdu project starts by rewriting the same four
things badly. This is those four things, written once, with tests.

### The problem nobody handles: the same word has several encodings

Urdu uses a Perso-Arabic script, and text scraped from the web freely mixes Arabic
codepoints with Urdu ones, because most keyboards and many fonts do not distinguish
them:

| Looks like | Arabic codepoint | Urdu codepoint |
|---|---|---|
| ی | `U+064A` ARABIC YEH | `U+06CC` FARSI YEH |
| ک | `U+0643` ARABIC KAF | `U+06A9` KEHEH |
| ہ | `U+0647` ARABIC HEH | `U+06C1` HEH GOAL |

They render identically and compare unequal. Without normalisation, exact match fails,
vocabularies fragment, and every downstream model quietly learns three versions of the
same word.

```python
normalize("كتاب") == normalize("کتاب")   # True. Without it: False.
```

**Measured on 84,581 BBC Urdu news articles** (44.7M tokens): **7,410 articles — one in
eleven — contain an Arabic codepoint standing in for an Urdu one.** 20,555 occurrences of
`U+064A` ARABIC YEH alone, in professionally edited copy. Unicode NFC does not touch any of
them, because they are genuinely different letters used by different languages.

&#128202; **[Every claim on this page, measured against the corpus &rarr;](https://github.com/hammasbuilds/urdunlp/blob/main/docs/CORPUS.md)**

### Roman Urdu, which is what people actually type

Most Pakistanis type Urdu in Latin script — in messages, comments, reviews, support
tickets. It has **no standard orthography**:

```
نہیں  ->  nahi, nahin, nhi, nahee, naheen
ہے    ->  hai, hay, he, h
```

This library does not pretend that is solved. It works in two stages and **tells you
which one answered**:

```python
r = transliterate_with_confidence("mera naam Ali hai")
r.text               # 'میرا نام الی ہے'
r.lexicon_coverage   # 0.5  — half looked up, half guessed by rule
r.sources            # [('mera','lexicon'), ('naam','rules'),
                     #  ('Ali','rules'), ('hai','lexicon')]
```

`Ali` comes back as `الی`, not the conventional `علی`, because ع cannot be written in Roman
and no lexicon covers proper nouns. The function says so — `rules`, not `lexicon` — rather
than presenting a guess as a lookup.

A curated lexicon covers the closed-class vocabulary — pronouns, postpositions,
auxiliaries — which is where most tokens in real text actually are, and which rules
cannot disambiguate (`khana` is کھانا *food* or خانہ *compartment*). Longest-match
grapheme rules handle the rest, because no lexicon covers proper nouns. Hiding that
distinction behind a single string would be the dishonest design.

**"Where most tokens actually are" is measurable, so it was measured**: the 115-word
stopword list covers **41.4% of 44.7M tokens**, and 114 of the 115 entries appear in the
corpus at all.

### Transliteration is lossy, and the default is the worse round-trip

Round-tripping 457,428 sampled tokens, Urdu → Roman → Urdu:

| `insert_short_vowels` | Exact round-trip |
|---|---:|
| `True` **(default)** | 44.7% |
| `False` | **61.2%** |

Urdu does not write short vowels, so `صرف` maps to `srf` — unreadable to an English
speaker. Inserting them gives `saraf`, which is what Roman Urdu users actually type, but
every inserted vowel returns as an alef: `ساراف`.

**Use the default when a person reads the output; use `insert_short_vowels=False` when
something has to convert it back.** The README previously documented neither.

## What it does

| Module | |
|---|---|
| `normalize` | Arabic↔Urdu unification, diacritics, tatweel, zero-width, digits, punctuation. `is_urdu()` script detection. |
| `tokenize` | Sentence splitting on `۔` and `؟`, word tokenisation, merged-compound repair, character n-grams. |
| `translit` | Roman Urdu ↔ Urdu script, with per-token confidence. |
| `stopwords` | 115 function words — **with negation held separately**. |

### Three details that are usually wrong elsewhere

**Urdu punctuation lives inside the Arabic block**, interleaved with the letters. A
range like `؀-ۿ` silently swallows `،` `؟` `۔` into your word tokens. The letter
ranges here skip each punctuation codepoint individually.

**`ھ` (do-chashmi he) marks aspiration**, not a separate consonant — `کھ` is one
sound. Transliterating it as its own letter turns کھانا into `kahana`. It is also a
different codepoint from standalone `ہ`, and confusing the two is the most common
mistake in machine-produced Urdu.

**Negation is not a stopword.** `نہیں` carries the entire meaning of a sentence, and
a stopword list that deletes it inverts every sentiment label. It is kept in a
separate `NEGATION` set and preserved by default:

```python
remove_stopwords(words("یہ اچھا نہیں ہے"))   # ['اچھا', 'نہیں']  — negation survives
```

## Install

```bash
pip install urdunlp
```

The distribution is `urdunlp`, which is also the import name. Until the first
release lands, install from the repository:

```bash
pip install git+https://github.com/hammasbuilds/urdunlp
```

No dependencies, deliberately. This is the layer other Urdu projects sit on, and a
dependency here becomes a dependency of all of them.

The package is **typed** — `py.typed` ships in the wheel, so mypy and pyright see every
annotation rather than falling back to `Any`.

From a clone, there is nothing to install at all:

```bash
git clone https://github.com/hammasbuilds/urdunlp
cd urdunlp
python demo.py
pytest -q          # 57 tests, no install step needed
```

---

## Input

One deliberately messy sentence: Arabic `ک` and `ی` rather than the Urdu forms, doubled
spaces, a URL and an English mention.

```
میں  کل  لاہور  سے  آیا  ہوں۔ http://x.co @ali
```

## Output

`python demo.py`

```
remove_urls_and_mentions   میں کل لاہور سے آیا ہوں۔
normalize                  میں کل لاہور سے آیا ہوں۔
words                      میں کل لاہور سے آیا ہوں
remove_stopwords           کل لاہور آیا
transliterate_to_roman     min kal lahor se aaia hon.

6 tokens in, 3 content words out (3 stopwords removed)

Roman -> Urdu, with identifiers left alone:
   dekho http://x.co par    ->  دےکھو http://x.co پر
   @ali ne kaha             ->  @ali نے کہا
   lahore                   ->  لاہور
```

*A transliterated URL is a broken URL, so URLs, emails, `@mentions` and `#hashtags` pass
through untouched. Ordinary English words do **not**: `lahore` gives لاہور, because Roman
Urdu is written in English letters and the two cannot be told apart by spelling.*

*Shown as text, not a screenshot: Urdu is a joining right-to-left script, and an image
renderer without HarfBuzz shaping produces disconnected letters in the wrong order.*

---

## Tests

```bash
pytest
```

**49 tests.** Each encodes a real property of the language rather than a convenient
example, so a failure means the library is wrong about Urdu, not about a fixture.

## Known limits

Stated plainly, because a toolkit that overclaims wastes its users' time:

- **Roman → Urdu is ambiguous by nature.** `sher` is شیر (lion) or شعر (couplet).
  Outside the lexicon it is a best-effort guess, and `lexicon_coverage` tells you how
  much of a given string was guessed.
- **English words inside Roman Urdu are transliterated too.** `lahore` → لاہور is
  correct; `hello` → ہےللو is not, and nothing in the spelling distinguishes them.
  Only *identifiers* — URLs, emails, `@mentions`, `#hashtags` — are recognised by
  syntax and passed through untouched. Strip English spans yourself if you have a
  reliable way to find them.
- **Urdu → Roman is lossy and one-way.** س ص ث all give `s`; the merge cannot be
  undone. Measured over 457,428 corpus tokens, **44.7% survive a round-trip** with the
  default settings and **61.2% with `insert_short_vowels=False`**. The remaining 38.8%
  is letter collapse that no setting recovers — ح/ہ/ھ all `h`, خ and کھ both `kh`, and
  ں nasalisation written as a plain `n`.
- **Short vowels are inserted heuristically.** Urdu does not write them, so a literal
  mapping gives `jmlh` for جملہ. An `a` between consonants gives `jamalah` — right
  more often than not, wrong sometimes, and disabled with
  `insert_short_vowels=False`. **The default is the worse round-trip**: every inserted
  vowel returns as an alef, so `صرف` → `saraf` → `ساراف`. Readable output and
  reversible output are different goals; pick the setting for the one you need.
- **Feeding Urdu to the Roman → Urdu direction is a no-op, and now says so.** Tokens
  already in Urdu script are reported as `already-urdu` rather than `rules`, and
  `already_urdu_share` tells you. Previously they were returned untouched and labelled
  as though the rule engine had resolved them.
- **Compound-splitting is a fixed list**, not a model. Deliberately: an aggressive
  splitter does more damage than an incomplete one.
- **No stemmer or lemmatiser.** Urdu morphology needs a lexicon that does not exist
  openly. Use `character_ngrams` as the cheap substitute.

## Keywords

Urdu NLP &middot; Roman Urdu &middot; transliteration &middot; Unicode normalisation &middot; text preprocessing &middot; tokenization &middot; word segmentation &middot; low-resource languages &middot; South Asian languages &middot; Nastaliq &middot; Arabic script &middot; zero dependencies &middot; pure Python &middot; diacritics &middot; language tooling

## License

MIT

---

## Run it yourself

```bash
git clone https://github.com/hammasbuilds/urdunlp
cd urdunlp

pytest -q               # 57 tests, no install step needed
python demo.py          # see it work
```

```python
from urdunlp import normalize, transliterate_to_urdu, words, remove_stopwords

normalize("كتاب")                          # 'کتاب'
transliterate_to_urdu("main theek hoon")   # 'میں ٹھیک ہوں'
words("کیا، واقعی؟", keep_punctuation=True)
remove_stopwords(words("یہ اچھا نہیں ہے")) # ['اچھا', 'نہیں'] — negation kept
```

Works on Python 3.10–3.13, Linux and Windows. No models, no downloads, no GPU.

## Problems hit while building this

**Urdu punctuation lives inside the Arabic letter block.** The obvious range `؀-ۿ`
silently swallows `،` `؟` `۔` into word tokens, so `words("کیا، واقعی؟")` returned
`['کیا،', 'واقعی؟']` — punctuation glued to words, which corrupts every downstream
count. *Fixed* by enumerating letter sub-ranges that skip each punctuation codepoint
individually.

**`ھ` was treated as a standalone consonant.** It marks *aspiration* on the letter
before it — `کھ` is one sound — so inserting a vowel around it turned کھانا into
`kahana` instead of `khana`. *Fixed* by excluding it from vowel insertion, with a test.

**Short vowels do not exist in written Urdu.** A literal character mapping gives `jmlh`
for جملہ, which no Roman Urdu reader would write. *Fixed* with a heuristic `a`
insertion between consonants — right more often than not, and switchable off, because
pretending a heuristic is a rule is how a toolkit loses trust.

**Negation was almost a stopword.** The first stopword list included `نہیں`. That
single word carries the meaning of a sentence, and removing it inverts every sentiment
label. *Fixed* by holding negation in a separate set that is preserved by default.

**`pip install urdu-nlp-toolkit` did not work, and this README said it did.** The
package is not on PyPI. Anything that followed that instruction failed to install, which
is strictly worse than documenting no install method at all. *Fixed* by publishing the
`git+https` form that works today and saying plainly that PyPI is pending.

**`pytest` failed from a fresh clone.** The package lives in `src/`, so `import urdunlp`
only resolved after `pip install -e .`. CI does that before running tests, so CI was
green the whole time while anyone cloning the repository got `ModuleNotFoundError`. A
project whose claim is "zero dependencies, nothing to download" should not need an
install step to run its own tests. *Fixed* with a `conftest.py`.

**Urdu fed to the Roman → Urdu direction was reported as successfully transliterated.**
`_apply_rules` matches Latin graphemes only, so an Urdu token passed straight through —
the right output, labelled `rules`, as though the rule engine had resolved it. With
`lexicon_coverage` then reading `0.0`, a call in the wrong direction looked like a
confident bad guess rather than a no-op. *Fixed* with an `already-urdu` source and an
`already_urdu_share` property.

**The README's own transliteration example was wrong.** It showed
`mera naam Ali hai` → `میرا نام علی ہے`. The code returns `الی`, because ع is unwritable
in Roman and no lexicon covers proper nouns. The published output was what a reader
expects rather than what the function does. *Fixed*, and pinned by a test so the
documented example cannot drift from the code again.

**`fix_spacing` missed a fifth of the compounds it exists to repair.** It split the
input on whitespace, so any punctuation stayed glued to the token: `کردیا` matched the
table and `کردیا۔` did not. These are perfective auxiliaries, so the end of a clause is
exactly where they sit. Across all 84,581 articles there are **60,305 occurrences of the
19 compounds, and whitespace splitting found 48,582 — missing 11,723, or 19.4%.** The
per-word split is the proof: the completive `ہوگئے` was missed **34.2%** of the time and
`کردیں` **35.6%**, while the progressive `کررہے`, which sits mid-clause, was missed
**0.7%**. *Fixed* by matching word spans, which also stopped the function reflowing the
whole document — `" ".join(text.split())` collapsed every newline and indent as a side
effect of inserting one space.

**A measurement script that measured nothing.** The first version of
`scripts/measure_corpus.py` computed `normalize(t) != t` over tokens from `words()` —
but `words()` normalises internally, so the comparison was false for every token by
construction. It reported a 0% normalisation rate across 247,064 tokens, which reads
like a finding and is a tautology. *Fixed* by measuring against raw whitespace tokens.
A second version round-tripped with `transliterate_with_confidence`, which is the
*Roman → Urdu* direction: fed Urdu it returns the input untouched, so the round-trip was
identity in, identity out, and reported **99.96%**. The real figure is 44.7%.
