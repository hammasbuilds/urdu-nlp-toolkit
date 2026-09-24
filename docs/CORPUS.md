# Measured against 84,581 real Urdu articles

[<- back to README](../README.md)

Every claim this toolkit makes was qualitative. This measures them against
[XL-Sum Urdu](https://huggingface.co/datasets/csebuetnlp/xlsum): **84,581 BBC Urdu news
articles, 206,887,475 characters, 44,698,779 tokens**.

Reproduce it on any corpus:

```bash
python scripts/measure_corpus.py <directory-of-txt-or-a-parquet> --json out.json
```

## The corpus

| | |
|---|---:|
| Articles | 84,581 |
| Characters | 206,887,475 |
| Tokens | 44,698,779 |
| Distinct normalised types | 353,358 |

---

## 1. The Arabic/Urdu codepoint problem is real, and it is common

The README claims scraped Urdu freely mixes Arabic codepoints with Urdu ones. It does.

**7,495 of 84,581 articles (8.9%)** contain at least one Arabic letter standing in for its
Urdu counterpart — in professionally edited BBC copy, not user-generated text.

| Codepoint | Should be | Occurrences |
|---|---|---:|
| `U+064A` ARABIC YEH | `U+06CC` FARSI YEH | **20,555** |
| `U+0643` ARABIC KAF | `U+06A9` KEHEH | **4,132** |
| `U+0647` ARABIC HEH | `U+06BE` or `U+06C1`, by context | 981 |
| `U+0649` ALEF MAKSURA | `U+06CC` FARSI YEH | 40 |
| `U+0629` TEH MARBUTA | `U+06C1` HEH GOAL | 20 |

The heh row is a late addition, and the reason it was missing is worth stating: this
script's substitution list and `normalize()`'s mapping table were written from the same
list of letters. The one absent from the table was absent from the measurement too, so the
figure published here was counting only the letters the code already handled. A
measurement that shares a blind spot with the code it measures cannot find the gap — it
returns a clean result for the part nobody looked at. The earlier figure was 8.8%.

`normalize()` fixes **24,046 tokens** that Unicode NFC leaves alone, because these are
genuinely distinct codepoints for distinct languages.

Nearly one article in eleven. Any exact-match lookup, vocabulary build or deduplication
over this corpus is silently wrong without normalisation.

### The obvious mapping for ARABIC HEH is wrong nine times in ten

The other four letters have one Urdu counterpart each. `ه` has two, and Urdu uses them for
different jobs:

| | | |
|---|---|---|
| `ہ` | `U+06C1` HEH GOAL | an ordinary *h* — نہ, اللہ |
| `ھ` | `U+06BE` DOACHASHMEE HE | aspiration — بھی, تھا, کھانا |

Which one a stray `ه` stands for is decided by the letter before it. That can be checked
rather than argued about: a token containing no `ه` is correctly spelled by definition, so
the corpus vocabulary adjudicates each candidate spelling. Of the 977 occurrences, 934
have at least one candidate the corpus recognises:

| rule | correct |
|---|---:|
| always `ہ` — what this toolkit's docstring promised | 84/934 = **9.0%** |
| `ھ` after an aspirable consonant, else `ہ` | 905/934 = **96.9%** |

The intuitive mapping is wrong more than nine times in ten, and the reason is mechanical:
a keyboard without `ھ` is a keyboard without *bh, ph, th, kh, gh*, so that is where the
substitution turns up. `بهی` outnumbers everything else in the list.

```
لکها   ->  لکھا   seen 12,909 times    vs  لکہا   seen 1
سنده   ->  سندھ   seen 13,399 times    vs  سندہ   seen 93
نه     ->  نہ     seen 75,285 times    vs  نھ     seen 1
```

The remaining 3.1% is not noise to be engineered away: بہار (spring) and بھار (weight)
differ only in this letter, and nothing context-free separates them. `resolve_arabic_heh`
is exported so the heuristic can be applied, inspected or switched off, rather than
presented as a rule.

## 2. Normalisation moves 0.59% of tokens, and merges 14,611 types

| | |
|---|---:|
| Raw whitespace tokens | 44,682,626 |
| Changed by `normalize()` | **263,833** (0.59%) |
| Types written more than one way | **14,611** |
| Tokens moved onto the majority spelling | 210,906 |

0.59% sounds small until you notice it is concentrated: 14,611 distinct words appear in two
or more spellings, and 210,906 token instances are the minority form. Those are exactly the
words a vocabulary fragments on.

## 3. 115 stopwords cover 41.4% of running text

The README calls the list "closed-class vocabulary — pronouns, postpositions, auxiliaries —
which is where most tokens in real text actually are". Measured:

| | |
|---|---:|
| Stopword list size | 115 |
| Entries that appear in the corpus | **114 of 115** |
| Token hits | 18,492,484 |
| **Share of all tokens** | **41.4%** |

114 of 115 entries earn their place. The ten most frequent types in 44.7M tokens:

| | Count | | Count |
|---|---:|---|---:|
| کے | 2,047,014 | اور | 830,808 |
| میں | 1,472,477 | کہ | 770,042 |
| کی | 1,327,136 | نے | 758,610 |
| ہے | 1,093,615 | کا | 713,233 |
| سے | 893,078 | کو | 670,246 |

Every one is a function word. That is the claim, measured.

## 4. Transliteration is lossy — and the default setting is the worse one

Round-tripping Urdu → Roman → Urdu on **457,380 sampled tokens** (every 97th, spread across
the whole corpus, 21,766 distinct types):

| `insert_short_vowels` | Exact round-trip |
|---|---:|
| `True` **(the default)** | **44.7%** |
| `False` | **61.2%** |

**The default round-trips 16.5 points worse than turning it off.** That is not a bug in the
round-trip — it is the cost of the default being right for its actual job. Urdu does not
write short vowels, so `صرف` maps to the consonants `srf`, which no English reader can
pronounce. Inserting them gives `saraf`, which is readable and is what Roman Urdu users
type. But every inserted vowel comes back as an alef:

| Urdu | Roman (default) | Back | Roman (bare) | Back |
|---|---|---|---|---|
| کتاب | `katab` | کاتاب ✗ | `ktab` | کتاب ✓ |
| پاکستان | `pakasatan` | پاکاساتان ✗ | `pakstan` | پاکستان ✓ |
| مشکل | `mashakal` | ماشاکال ✗ | `mshkl` | مشکل ✓ |
| تقریبا | `taqariba` | تاقاریبا ✗ | `tqriba` | تقریبا ✓ |
| امریکی | `amariki` | اماریکی ✗ | `amriki` | امریکی ✓ |

So: use the default when a human reads the output, and `insert_short_vowels=False` when
something has to convert it back.

### Three losses no setting recovers

The remaining 38.8% is not the vowel setting. Urdu distinguishes letters that Roman spells
identically, so the map back can only pick one:

| Urdu | Bare roman | Back | What collapsed |
|---|---|---|---|
| صرف | `srf` | سرف | ص and س are both `s` |
| حسن | `hsn` | ہسن | ح, ہ and ھ are all `h` |
| بیماریاں | `bimarian` | بیماریان | ں nasalisation is a plain `n` |
| اختلافات | `akhtlafat` | اکھتلافات | خ and کھ are both `kh` |

`لاہور` → `lahor` → `لاہور` round-trips under **both** settings — no ambiguous letter, no
inserted vowel. That is the control: without it, the rows above could be describing a
transliterator that never round-trips anything.

These are properties of the two writing systems, not of the implementation. A round-trip
figure of 100% would mean the transliteration was not doing its job.

*(The first draft of this table used `صرف` as a vowel example. It is not one — it fails
both ways because of the sibilant collapse. The test that pins these examples caught it.)*

## 5. The lexicon is small on purpose, and the README's own example shows why

249 lexicon entries and 55 grapheme rules. The lexicon deliberately covers closed-class
vocabulary — the words rules cannot disambiguate — and not proper nouns:

```python
>>> transliterate_with_confidence("mera naam Ali hai")
Transliteration(text='میرا نام الی ہے',
                sources=[('mera', 'lexicon'), ('naam', 'rules'),
                         ('Ali', 'rules'), ('hai', 'lexicon')])
```

`Ali` resolves by rule to `الی`, not the conventional `علی`, because ع is unwritable in
Roman and no lexicon covers names. `lexicon_coverage` reports `0.5` rather than hiding it.

An earlier version of this page, and the README, showed `علی` in that output. That was
wrong: it is what the reader expects, not what the code returns.

---

## 6. Merged compounds cluster at the end of a clause, where the old matcher could not see them

`fix_spacing` repairs 19 compounds that Urdu typists routinely write without the space.
It used to find them by splitting the text on whitespace, which attaches any adjacent
punctuation to the token — so `کردیا` matched and `کردیا۔` did not.

Over the full corpus, counting each compound as a word span rather than a whitespace
chunk:

| | count |
|---|---:|
| occurrences present | 60,305 |
| found by whitespace splitting | 48,582 |
| **missed** | **11,723 (19.4%)** |

The loss is not spread evenly, and that is what identifies the cause. These compounds are
verb + auxiliary. The *completive* ones end a clause, so a sentence mark sits against
them; the *progressive* ones continue it:

| compound | | occurrences | missed | |
|---|---|---:|---:|---:|
| `کردیں` | did | 1,069 | 381 | **35.6%** |
| `ہوگئے` | became | 12,156 | 4,161 | **34.2%** |
| `ہوگیا` | became | 6,428 | 1,792 | 27.9% |
| `کردیا` | did | 10,291 | 1,898 | 18.4% |
| `آرہا` | is coming | 821 | 48 | 5.8% |
| `جارہا` | is going | 3,588 | 50 | 1.4% |
| `کررہے` | are doing | 3,151 | 23 | **0.7%** |

A fiftyfold difference in miss rate between `کردیں` and `کررہے` is not noise in the
matcher — it is clause position, and it is why the bug was invisible to a unit test
written from a single example.

Matching word spans also stopped the function rewriting text it was not asked to touch:
`" ".join(text.split())` collapsed every newline, indent and double space in the input as
a side effect of inserting one.

---

## What this does not measure

**One corpus, one register.** XL-Sum Urdu is edited BBC news prose. Social media, legal
text, poetry and transcribed speech all differ, and the Arabic-substitution rate is very
likely *higher* in user-generated text than the 8.9% measured in professional copy.

**No Roman Urdu corpus.** Every number about the Roman → Urdu direction here is derived by
round-tripping Urdu, which is not the same as measuring real Roman Urdu input. A corpus of
what people actually type is the single most valuable thing missing.

**No accuracy figure for transliteration.** Round-trip fidelity is not correctness — a
wrong-but-stable mapping round-trips perfectly. Measuring correctness needs human-checked
pairs, which do not exist for Urdu at any useful scale.
