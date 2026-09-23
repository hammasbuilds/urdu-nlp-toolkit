"""Transliteration between Roman Urdu and Urdu script.

Roman Urdu is how most Pakistanis actually type Urdu - in messages, comments, reviews
and support tickets. It is also close to unprocessable by standard NLP tooling,
because it has **no standard orthography**. One word has many spellings:

    نہیں  ->  nahi, nahin, nhi, nahee, naheen
    ہے    ->  hai, hay, he, h
    کیا   ->  kya, kia, kaya

and the same Roman string can map to different Urdu words:

    khana  ->  کھانا (food / to eat)   or   خانہ (compartment, in compounds)
    sher   ->  شیر (lion)              or   شعر (couplet)

So this module does **not** pretend to be a solved problem. It works in two stages
and reports which one produced each answer:

  1. **Lexicon.** A curated map of high-frequency words, covering the closed-class
     vocabulary - pronouns, postpositions, auxiliaries, common verbs - which is where
     most tokens in real text actually are.
  2. **Rules.** Longest-match grapheme substitution for everything else.

The lexicon exists because rules cannot disambiguate `khana`, and closed-class words
are both the most frequent and the most irregular. The rules exist because no lexicon
will ever cover proper nouns.

`transliterate_to_urdu` returns the text; `transliterate_with_confidence` returns the
same thing plus which stage handled each token, so a caller can decide whether to
trust it. Hiding that distinction would be the dishonest design.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import normalize

# --- Stage 1: lexicon -------------------------------------------------------------
# High-frequency Roman Urdu, mapped to correct Urdu script. Deliberately weighted
# towards closed-class words, which dominate token counts and are the most irregular.
LEXICON: dict[str, str] = {
    # pronouns
    "main": "میں",
    "mein": "میں",
    "mai": "میں",
    "me": "میں",
    "tum": "تم",
    "tu": "تو",
    "ap": "آپ",
    "aap": "آپ",
    "hum": "ہم",
    "hm": "ہم",
    "wo": "وہ",
    "woh": "وہ",
    "ye": "یہ",
    "yeh": "یہ",
    "mera": "میرا",
    "meri": "میری",
    "mere": "میرے",
    "tumhara": "تمہارا",
    "tumhari": "تمہاری",
    "apka": "آپ کا",
    "apki": "آپ کی",
    "hamara": "ہمارا",
    "hamari": "ہماری",
    "uska": "اس کا",
    "uski": "اس کی",
    "unka": "ان کا",
    # auxiliaries and copulas
    "hai": "ہے",
    "hay": "ہے",
    "he": "ہے",
    "hain": "ہیں",
    "hn": "ہیں",
    "ho": "ہو",
    "hoon": "ہوں",
    "hun": "ہوں",
    "hu": "ہوں",
    "tha": "تھا",
    "thi": "تھی",
    "thay": "تھے",
    "the": "تھے",
    "hoga": "ہوگا",
    "hogi": "ہوگی",
    "honge": "ہوں گے",
    "raha": "رہا",
    "rahi": "رہی",
    "rahe": "رہے",
    "gaya": "گیا",
    "gayi": "گئی",
    "gaye": "گئے",
    "diya": "دیا",
    "liya": "لیا",
    "kiya": "کیا",
    "kia": "کیا",
    # negation and question words
    "nahi": "نہیں",
    "nahin": "نہیں",
    "nhi": "نہیں",
    "naheen": "نہیں",
    "na": "نہ",
    "mat": "مت",
    "bina": "بغیر",
    "kya": "کیا",
    "kyun": "کیوں",
    "kyu": "کیوں",
    "kiyun": "کیوں",
    "kaise": "کیسے",
    "kaisa": "کیسا",
    "kaisi": "کیسی",
    "kahan": "کہاں",
    "kahaan": "کہاں",
    "kab": "کب",
    "kaun": "کون",
    "kon": "کون",
    "kitna": "کتنا",
    "kitni": "کتنی",
    "kitne": "کتنے",
    # postpositions and particles
    "ka": "کا",
    "ki": "کی",
    "ke": "کے",
    "ko": "کو",
    "se": "سے",
    "par": "پر",
    "pe": "پے",
    "tak": "تک",
    "liye": "لیے",
    "lye": "لیے",
    "sath": "ساتھ",
    "saath": "ساتھ",
    "bhi": "بھی",
    "hi": "ہی",
    "aur": "اور",
    "or": "اور",
    "ya": "یا",
    "agar": "اگر",
    "to": "تو",
    "tou": "تو",
    "lekin": "لیکن",
    "magar": "مگر",
    "phir": "پھر",
    "fir": "پھر",
    "abhi": "ابھی",
    "ab": "اب",
    "jab": "جب",
    "tab": "تب",
    # common verbs
    "karna": "کرنا",
    "karta": "کرتا",
    "karti": "کرتی",
    "karte": "کرتے",
    "kar": "کر",
    "karo": "کرو",
    "karen": "کریں",
    "hona": "ہونا",
    "jana": "جانا",
    "jata": "جاتا",
    "jati": "جاتی",
    "ana": "آنا",
    "aana": "آنا",
    "ata": "آتا",
    "aata": "آتا",
    "dena": "دینا",
    "lena": "لینا",
    "kehna": "کہنا",
    "kaha": "کہا",
    "dekhna": "دیکھنا",
    "dekha": "دیکھا",
    "sunna": "سننا",
    "suna": "سنا",
    "khana": "کھانا",
    "peena": "پینا",
    "sona": "سونا",
    "chalna": "چلنا",
    "milna": "ملنا",
    "mila": "ملا",
    "bolna": "بولنا",
    "likhna": "لکھنا",
    "parhna": "پڑھنا",
    "samajhna": "سمجھنا",
    "samajh": "سمجھ",
    "chahiye": "چاہیے",
    "chahta": "چاہتا",
    "chahti": "چاہتی",
    "sakta": "سکتا",
    "sakti": "سکتی",
    "sakte": "سکتے",
    # adjectives and adverbs
    "acha": "اچھا",
    "accha": "اچھا",
    "achi": "اچھی",
    "ache": "اچھے",
    "bura": "برا",
    "buri": "بری",
    "theek": "ٹھیک",
    "thik": "ٹھیک",
    "bohat": "بہت",
    "bahut": "بہت",
    "buhat": "بہت",
    "bht": "بہت",
    "thora": "تھوڑا",
    "thori": "تھوڑی",
    "zyada": "زیادہ",
    "ziada": "زیادہ",
    "kam": "کم",
    "bara": "بڑا",
    "bari": "بڑی",
    "chota": "چھوٹا",
    "choti": "چھوٹی",
    "naya": "نیا",
    "nayi": "نئی",
    "purana": "پرانا",
    "khush": "خوش",
    "udaas": "اداس",
    "sach": "سچ",
    "jhoot": "جھوٹ",
    "jaldi": "جلدی",
    "dheere": "دھیرے",
    "aaram": "آرام",
    # nouns
    "ghar": "گھر",
    "kaam": "کام",
    "kam2": "کام",
    "waqt": "وقت",
    "wqt": "وقت",
    "din": "دن",
    "raat": "رات",
    "subah": "صبح",
    "sham": "شام",
    "aaj": "آج",
    "aj": "آج",
    "kal": "کل",
    "parso": "پرسوں",
    "saal": "سال",
    "mahina": "مہینہ",
    "hafta": "ہفتہ",
    "pani": "پانی",
    "paani": "پانی",
    "roti": "روٹی",
    "chai": "چائے",
    "paisa": "پیسہ",
    "paise": "پیسے",
    "rupay": "روپے",
    "dost": "دوست",
    "bhai": "بھائی",
    "behen": "بہن",
    "ammi": "امی",
    "abbu": "ابو",
    "walid": "والد",
    "walida": "والدہ",
    "beta": "بیٹا",
    "beti": "بیٹی",
    "dil": "دل",
    "jaan": "جان",
    "pyar": "پیار",
    "muhabbat": "محبت",
    "zindagi": "زندگی",
    "khushi": "خوشی",
    "gham": "غم",
    "kitab": "کتاب",
    "school": "اسکول",
    "university": "یونیورسٹی",
    "sarak": "سڑک",
    "gari": "گاڑی",
    "shehar": "شہر",
    "gaon": "گاؤں",
    "mulk": "ملک",
    "duniya": "دنیا",
    "log": "لوگ",
    "admi": "آدمی",
    "aurat": "عورت",
    # greetings and fixed phrases
    "salam": "سلام",
    "assalam": "السلام",
    "walaikum": "وعلیکم",
    "shukriya": "شکریہ",
    "meherbani": "مہربانی",
    "khuda": "خدا",
    "allah": "اللہ",
    "inshallah": "ان شاء اللہ",
    "mashallah": "ماشاء اللہ",
    "hafiz": "حافظ",
    "khudahafiz": "خدا حافظ",
    "mubarak": "مبارک",
    "maaf": "معاف",
    "sorry": "معذرت",
    # place names
    "pakistan": "پاکستان",
    "lahore": "لاہور",
    "karachi": "کراچی",
    "islamabad": "اسلام آباد",
    "peshawar": "پشاور",
    "quetta": "کوئٹہ",
    "multan": "ملتان",
    "faisalabad": "فیصل آباد",
    "punjab": "پنجاب",
    "sindh": "سندھ",
    "urdu": "اردو",
}

# --- Stage 2: rules ---------------------------------------------------------------
# Ordered longest-first, so digraphs win over the single letters inside them: `kh`
# must be tried before `k`, or "khana" becomes ک+ہ instead of کھ.
#
# Aspirated consonants use do-chashmi he (ھ U+06BE), which is the correct letter for
# aspiration and a different codepoint from the he that appears as a standalone
# letter (ہ U+06C1). Getting this wrong is the single most common mistake in
# machine-produced Urdu.
RULES: list[tuple[str, str]] = [
    # trigraphs
    ("sch", "سچ"),
    ("tch", "چ"),
    # aspirated consonants
    ("bh", "بھ"),
    ("ph", "پھ"),
    ("th", "تھ"),
    ("jh", "جھ"),
    ("chh", "چھ"),
    ("dh", "دھ"),
    ("rh", "رھ"),
    ("kh", "کھ"),
    ("gh", "گھ"),
    ("lh", "لھ"),
    ("mh", "مھ"),
    ("nh", "نھ"),
    # digraph consonants
    ("ch", "چ"),
    ("sh", "ش"),
    ("zh", "ژ"),
    ("ng", "نگ"),
    ("ny", "نی"),
    # long vowels before short ones
    ("aa", "ا"),
    ("ee", "ی"),
    ("ii", "ی"),
    ("oo", "و"),
    ("uu", "و"),
    ("ai", "ے"),
    ("ay", "ے"),
    ("ei", "ی"),
    ("au", "و"),
    ("ou", "و"),
    # single consonants
    ("b", "ب"),
    ("p", "پ"),
    ("t", "ت"),
    ("j", "ج"),
    ("d", "د"),
    ("r", "ر"),
    ("z", "ز"),
    ("s", "س"),
    ("f", "ف"),
    ("q", "ق"),
    ("k", "ک"),
    ("g", "گ"),
    ("l", "ل"),
    ("m", "م"),
    ("n", "ن"),
    ("v", "و"),
    ("w", "و"),
    ("h", "ہ"),
    ("y", "ی"),
    ("c", "ک"),
    ("x", "کس"),
    # short vowels
    ("a", "ا"),
    ("e", "ے"),
    ("i", "ی"),
    ("o", "و"),
    ("u", "و"),
]

# Urdu -> Roman. Lossy by nature: Urdu has several letters that share one Roman
# sound (س ص ث all -> s), and that merge cannot be undone.
URDU_TO_ROMAN: dict[str, str] = {
    "ا": "a",
    "آ": "aa",
    "ب": "b",
    "پ": "p",
    "ت": "t",
    "ٹ": "t",
    "ث": "s",
    "ج": "j",
    "چ": "ch",
    "ح": "h",
    "خ": "kh",
    "د": "d",
    "ڈ": "d",
    "ذ": "z",
    "ر": "r",
    "ڑ": "r",
    "ز": "z",
    "ژ": "zh",
    "س": "s",
    "ش": "sh",
    "ص": "s",
    "ض": "z",
    "ط": "t",
    "ظ": "z",
    "ع": "a",
    "غ": "gh",
    "ف": "f",
    "ق": "q",
    "ک": "k",
    "گ": "g",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ں": "n",
    "و": "o",
    "ہ": "h",
    "ھ": "h",
    "ۂ": "h",
    "ۃ": "h",
    "ء": "",
    "ی": "i",
    "ے": "e",
    "ئ": "y",
    "ؤ": "o",
    "أ": "a",
}

_ROMAN_TOKEN = re.compile(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]+")
_SORTED_RULES = sorted(RULES, key=lambda r: -len(r[0]))

# Spans that are identifiers rather than words, and must survive untouched.
#
# Without this, the tokeniser splits `http://x.co` into `http`, `://`, `x`, `co`,
# transliterates the three alphabetic pieces, and returns `ہتتپ:// کس. کو` - a URL
# that no longer resolves. The same applies to @mentions, #hashtags and emails.
#
# This deliberately does NOT skip ordinary English words. `lahore` -> لاہور is the
# function working correctly, and a Roman Urdu sentence is full of words that are
# also English. Only spans whose *syntax* marks them as identifiers are protected.
_PASSTHROUGH = re.compile(
    r"""(
        https?://\S+                      # http(s) URL
      | www\.\S+                          # bare www URL
      | \b[\w.+-]+@[\w-]+\.[\w.-]+\b      # email
      | [@#]\w+                           # mention or hashtag
    )""",
    re.VERBOSE,
)


# Any character in the Arabic/Urdu blocks. Used to spot text that is already in
# Urdu script, which the Roman->Urdu direction must not claim to have converted.
_IS_URDU_SCRIPT = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")


@dataclass
class Transliteration:
    text: str
    # Per token: "lexicon" (trusted), "rules" (best effort), "passthrough"
    # (punctuation and digits), "identifier" (a URL, email, @mention or #hashtag,
    # emitted verbatim) or "already-urdu" (the token was not Roman at all).
    sources: list[tuple[str, str]]

    @property
    def lexicon_coverage(self) -> float:
        """Share of Roman words resolved by the lexicon rather than guessed by rule.

        Tokens already in Urdu script are excluded from the denominator. They are not
        words the lexicon failed on - there was nothing to look up - and counting them
        made a wrong-direction call report 0.0 coverage, which reads as a confident bad
        answer rather than as "this input was not Roman Urdu".
        """
        words = [s for t, s in self.sources if t.isalpha() and s != "already-urdu"]
        if not words:
            return 0.0
        return round(sum(1 for s in words if s == "lexicon") / len(words), 4)

    @property
    def already_urdu_share(self) -> float:
        """Share of alphabetic tokens that were already Urdu script.

        A non-zero value on input you believed was Roman Urdu means the text is mixed,
        or the call is in the wrong direction.
        """
        words = [s for t, s in self.sources if t.isalpha()]
        if not words:
            return 0.0
        return round(sum(1 for s in words if s == "already-urdu") / len(words), 4)


def _apply_rules(token: str) -> str:
    out: list[str] = []
    i = 0
    lowered = token.lower()
    while i < len(lowered):
        for roman, urdu in _SORTED_RULES:
            if lowered.startswith(roman, i):
                out.append(urdu)
                i += len(roman)
                break
        else:
            out.append(lowered[i])
            i += 1
    return "".join(out)


def transliterate_with_confidence(text: str) -> Transliteration:
    """Roman Urdu to Urdu script, reporting how each token was resolved."""
    pieces: list[str] = []
    sources: list[tuple[str, str]] = []

    # re.split with a capturing group alternates: text, identifier, text, ...
    for index, segment in enumerate(_PASSTHROUGH.split(text)):
        if not segment:
            continue
        if index % 2:  # an odd index is a captured identifier - emit it verbatim
            pieces.append(segment)
            sources.append((segment, "identifier"))
            continue
        for token in _ROMAN_TOKEN.findall(segment):
            if not token.isalpha():
                pieces.append(token)
                sources.append((token, "passthrough"))
                continue
            if _IS_URDU_SCRIPT.search(token):
                # Already in Urdu script: this direction has nothing to do.
                #
                # Without this the token fell through to _apply_rules, which matches
                # only Latin graphemes and so returned it unchanged - correct output
                # labelled `rules`, as though the rule engine had resolved it. Feeding
                # Urdu to the Roman->Urdu direction by mistake then produced a result
                # that looked transliterated, with `lexicon_coverage` reading 0.0,
                # which says "guessed badly" rather than "wrong direction".
                pieces.append(token)
                sources.append((token, "already-urdu"))
                continue
            lowered = token.lower()
            if lowered in LEXICON:
                pieces.append(LEXICON[lowered])
                sources.append((token, "lexicon"))
            else:
                pieces.append(_apply_rules(token))
                sources.append((token, "rules"))

    # Join with spaces, but keep *punctuation* attached to the word before it.
    # Digits are their own words and must not be glued on: "main 25 saal" would
    # otherwise render as "میں25 سال".
    out = ""
    for piece, (token, kind) in zip(pieces, sources, strict=True):
        glue = kind == "passthrough" and out and not token[0].isalnum()
        out += piece if glue else (" " if out else "") + piece

    return Transliteration(text=out.strip(), sources=sources)


def transliterate_to_urdu(text: str) -> str:
    """Roman Urdu to Urdu script.

    URLs, emails, @mentions and #hashtags are passed through unchanged. Ordinary
    English words are not: `lahore` gives لاہور, because Roman Urdu is written in
    English letters and the two cannot be told apart by spelling.
    """
    return transliterate_with_confidence(text).text


_ROMAN_VOWELS = set("aeiou")
# Letters that attach to the preceding consonant rather than standing alone.
_ASPIRATION = {"ھ", "ء"}
_URDU_PUNCT_TO_ASCII = {"،": ",", "؛": ";", "؟": "?", "۔": "."}


def transliterate_to_roman(text: str, *, insert_short_vowels: bool = True) -> str:
    """Urdu script to Roman Urdu.

    Lossy and one-way: several Urdu letters share a Roman sound (س ص ث all give `s`),
    and that merge cannot be undone.

    Urdu does not write short vowels, so a literal character mapping produces
    consonant runs - جملہ becomes `jmlh`, which no Roman Urdu reader would write.
    With `insert_short_vowels` an `a` is placed between adjacent consonants, giving
    `jamlah`. That is a heuristic, not a pronunciation model: it is right far more
    often than it is wrong, and it is off with one flag when you need the raw mapping.
    """
    text = normalize(text)
    out: list[str] = []

    for char in text:
        if char in URDU_TO_ROMAN:
            piece = URDU_TO_ROMAN[char]
            if (
                insert_short_vowels
                and piece
                # ھ marks aspiration on the letter before it - کھ is one sound, not
                # two. A vowel inserted here turns کھانا into "kahana".
                and char not in _ASPIRATION
                and out
                and out[-1]
                and out[-1][-1].isalpha()
                and out[-1][-1] not in _ROMAN_VOWELS
                and piece[0] not in _ROMAN_VOWELS
            ):
                out.append("a")
            out.append(piece)
        elif char in _URDU_PUNCT_TO_ASCII:
            out.append(_URDU_PUNCT_TO_ASCII[char])
        elif char.isspace() or char.isascii():
            out.append(char)
        # Anything else - a stray mark - is dropped rather than emitted as noise.

    return re.sub(r"\s+", " ", "".join(out)).strip()
