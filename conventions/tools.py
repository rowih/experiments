"""The agents' tools over the Python package, called in process (PLAN.md § 4), and the
game's checks on a message a speaker sends.

Every tool returns text for the model. Nothing here calls a model.
"""

import re
from dataclasses import dataclass

from rowih import api, data
from rowih.diagnostics import InputError
from rowih.notation import NotationError, Printer, sexp
from rowih.writer import Envelope

MAX_LOOKUP = 25
CONSONANTS = "ptkbdgmnslrwyh"
VOWELS = "aeiou"
ROWIH_WORD = re.compile(r"^(?:[%s][%s])+[%s]?$" % (CONSONANTS, VOWELS, CONSONANTS))
ROWIH_TYPE = "text/prs.rowih"
EXCLUDED_CATEGORIES = ("jargon", "dialect form")
WALL_HEADS = ("quote", "example", "data")

LOOKUP_TOOL = {
    "name": "lookup",
    "description": "Look up a word of Rowih's lexicon by its key (as the notation writes "
                   "it), its form, or an English word of its gloss. Returns, for each "
                   "match, how the notation writes it, its form, its category and its "
                   "meaning; a predicate root also lists the roles it takes.",
    "input_schema": {"type": "object", "additionalProperties": False,
                     "properties": {"term": {"type": "string"}}, "required": ["term"]},
    "strict": True,
}
WRITE_TOOL = {
    "name": "write",
    "description": "Write a message from one or more moves in the notation, under this "
                   "round's envelope, and read it back. Returns the message, its "
                   "diagnostics, and for each move its literal semantic form and the "
                   "English explanation. Writing sends nothing.",
    "input_schema": {"type": "object", "additionalProperties": False,
                     "properties": {"notation": {"type": "string"}},
                     "required": ["notation"]},
    "strict": True,
}
READ_TOOL = {
    "name": "read",
    "description": "Read a Rowih message through the toolchain. Returns its diagnostics "
                   "and, for each move, its transliteration, morpheme gloss, literal "
                   "semantic form and English explanation. Pass the whole message, "
                   "envelope included, or an empty string to read the message you "
                   "received in this round.",
    "input_schema": {"type": "object", "additionalProperties": False,
                     "properties": {"message": {"type": "string"}},
                     "required": ["message"]},
    "strict": True,
}
SEND_TOOL = {
    "name": "send",
    "description": "As the speaker, send to your hearer the message written from this "
                   "notation under the round's envelope. The game refuses a message that "
                   "draws a diagnostic or whose quoted words, examples or declared data "
                   "hold anything but Rowih words, and says why.",
    "input_schema": {"type": "object", "additionalProperties": False,
                     "properties": {"notation": {"type": "string"}},
                     "required": ["notation"]},
    "strict": True,
}
CHOOSE_TOOL = {
    "name": "choose",
    "description": "As the hearer, choose the concept the message refers to, by its "
                   "letter.",
    "input_schema": {"type": "object", "additionalProperties": False,
                     "properties": {"concept": {"type": "string",
                                                "enum": ["A", "B", "C", "D", "E", "F"]}},
                     "required": ["concept"]},
    "strict": True,
}
# One tool list for every agent and role, so that every call shares one cached prefix.
TOOLS = [LOOKUP_TOOL, WRITE_TOOL, READ_TOOL, SEND_TOOL, CHOOSE_TOOL]
# The fresh hearers of the decoding test read and choose; they write nothing.
HEARER_TOOLS = [LOOKUP_TOOL, READ_TOOL, CHOOSE_TOOL]

_LANG = None
_PRINTER = None


def _lang():
    global _LANG, _PRINTER
    if _LANG is None:
        _LANG = data.load()
        _PRINTER = Printer(_LANG)
    return _LANG


def _printer() -> Printer:
    _lang()
    return _PRINTER


def _codes(diagnostics: list) -> list:
    return [getattr(d, "code", None) or str(d) for d in diagnostics]


def diagnostic_text(d) -> str:
    """A diagnostic as a reader states it: its code, and what was expected and found."""
    code = getattr(d, "code", None)
    if code is None:
        return str(d)
    parts = [code]
    expected, detected = getattr(d, "expected", None), getattr(d, "detected", None)
    if expected:
        parts.append("expected: %s" % ", ".join(map(str, expected)))
    if detected:
        parts.append("found: %s" % ", ".join(map(str, detected)))
    return "; ".join(parts)


def _diagnostic_lines(diagnostics: list) -> str:
    if not diagnostics:
        return "none"
    return "\n".join("- %s" % diagnostic_text(d) for d in diagnostics)


def lookup(term: str) -> str:
    """The lexicon's matches for `term`, as `rowih.api.lookup` finds them. The dialects'
    terms are left out: a message names no dialect in this game, so a hearer could not
    read them."""
    lang = _lang()
    items = [i for i in api.lookup(term) if i.category not in EXCLUDED_CATEGORIES]
    if not items:
        return "No word of the lexicon matches %r." % term
    lines = []
    for item in items[:MAX_LOOKUP]:
        entry = lang.entries.get(item.identifier)
        written = _printer().atom_of(item) or "(not written in the notation)"
        meaning = entry["definition"] if entry else item.gloss.lower().replace("-", " ")
        category = entry["grammatical category"] if entry else "grammatical member"
        line = "%s | form %s | %s | %s" % (written, item.form, category, meaning)
        if entry and entry.get("argument structure"):
            line += " | roles: " + ", ".join(r["role"] for r in entry["argument structure"])
        lines.append(line)
    if len(items) > MAX_LOOKUP:
        lines.append("(%d more matches not shown)" % (len(items) - MAX_LOOKUP))
    return "\n".join(lines)


@dataclass(frozen=True)
class Written:
    """A message written from a notation, with what reading it back found."""
    text: str
    diagnostics: list
    normal: list            # each move's literal semantic form, as the printer writes it
    english: str
    moves_text: str         # the moves' lines of the transliteration, without the envelope
    words: int              # the number of words of the moves, without the envelope


def analyse_text(text: str) -> Written:
    """A message read back: its diagnostics, normal forms, explanation and size."""
    analysis = api.parse(text)
    normal = [_printer().move(n) for n in analysis.normal]
    english, _, _ = api.translate(text)
    moves = analysis.message.moves if analysis.message is not None else []
    moves_text = "\n".join(" ".join(w.form for w in m.words) for m in moves)
    words = sum(len(m.words) for m in moves)
    return Written(text, list(analysis.diagnostics), normal, english, moves_text, words)


def write_message(notation: str, envelope: Envelope) -> Written:
    """The message written from `notation`; raises InputError where it cannot be
    written."""
    text, _ = api.write(notation, envelope)
    return analyse_text(text)


def write(notation: str, envelope: Envelope) -> str:
    try:
        w = write_message(notation, envelope)
    except (InputError, NotationError) as e:
        return "The notation could not be written: %s" % e
    return ("The message:\n%s\nDiagnostics:\n%s\n\nLiteral semantic form of each move:\n%s"
            "\n\nEnglish explanation:\n%s" % (w.text.rstrip("\n"), _diagnostic_lines(
                w.diagnostics), "\n".join(w.normal), w.english.rstrip("\n")))


def read(message: str, received: str | None = None) -> str:
    """The reading of `message`, or of the message received where `message` is empty."""
    if not message.strip():
        if received is None:
            return "You have received no message in this round; pass the message to read."
        message = received
    gloss, diagnostics = api.gloss(message if message.endswith("\n") else message + "\n")
    shown = "\n".join(line for line in gloss.splitlines() if not line.startswith("NATIVE"))
    return "Diagnostics:\n%s\n\n%s" % (_diagnostic_lines(diagnostics), shown.strip())


def _value(x) -> str:
    """An atom or a string of the notation's reader, which reads a string as ("str", s)."""
    return x[1] if isinstance(x, tuple) else str(x)


def _walls(tree, out: list) -> list:
    """Every quote, example and declared datum in a read notation, as lists of values."""
    if isinstance(tree, list):
        if tree and tree[0] in WALL_HEADS:
            out.append([_value(x) for x in tree])
        for x in tree:
            _walls(x, out)
    return out


def is_rowih_word(token: str) -> bool:
    """A word of the lexicon, or a string of Rowih's shape: consonant and vowel
    alternating from a consonant, over the nineteen letters of the transliteration."""
    return token in _lang().by_form or bool(ROWIH_WORD.match(token))


def inert_refusal(notation: str) -> str | None:
    """Why the game refuses the notation's inert material, or None: quoted words,
    examples and declared data may carry only Rowih words (PLAN.md § 4, step 3)."""
    for wall in _walls(sexp(notation), []):
        texts = wall[2:3] if wall[0] == "data" else wall[1:2]
        if wall[0] == "data" and wall[1] != ROWIH_TYPE:
            return "declared data of type %s; only %s is admitted" % (wall[1], ROWIH_TYPE)
        for text in texts:
            bad = [t for t in text.split() if not is_rowih_word(t)]
            if bad:
                return "%s material holds text that is not Rowih words: %s" % (
                    wall[0], " ".join(bad[:5]))
    return None
