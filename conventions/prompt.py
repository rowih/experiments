"""The texts the agents read: the frozen system prompt every call shares, built from the
repository's own sources, and the user message of each turn.

The system prompt is the same bytes for every call of every agent, so that one cached
prefix serves the whole population (PLAN.md § 6). Everything that varies, the agent's
number, its memory and its task, goes in the user message.
"""

import os
import re

from rowih import data, summary

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LETTERS = "ABCDEF"

GAME = """# The game

You are one of ten agents taking part in a game played in rounds. Each agent is known by its participant number, from 1 to 10. In each round two agents are drawn at random, one as speaker and one as hearer.

- The speaker is shown one of six concepts, privately and in English, and refers to it in a single Rowih message to the hearer.
- The hearer receives the message and chooses which of the six concepts it refers to. The six are shown to the hearer in English, in an order shuffled for each round.
- The round succeeds if the hearer chooses the concept the speaker was shown. Both agents are told the outcome, and the hearer is told the concept the speaker was shown.

Every agent keeps a memory of its last ten rounds. No one coordinates the agents, and they communicate only through the messages of the game. The lexicon has no word for any of the six concepts.

## The speaker's message

The game refuses a message unless it meets both of these conditions:

1. Reading it draws no diagnostic.
2. Its quoted words, examples and declared data hold only words of Rowih: words of the lexicon, or words of Rowih's shape made of the nineteen letters of the transliteration; declared data must be of the type text/prs.rowih. English, or any other text, inside them is refused.

A refused message may be corrected and sent again twice. A third refusal loses the round.

A speaker that lacks a word may refer to a concept by any means the language gives: with words and idioms of the lexicon; with a compound or a derivation formed from the lexicon's roots and suffixes and written `(unknown "FORM")`, which a hearer reads from its parts; or by defining a word with the act of definition. A definition gives the word its meaning only in later messages of an exchange, and in this game every message is checked on its own, so a word defined in the game cannot be used in a message: a message that defines a word refers to the concept through the definition itself.

The game sets each message's envelope (its sender, recipient, time, serial and first entry), and the tools write it. You may call several tools at once.

## The tools

- `lookup`: find a word of the lexicon by its key, its form, or an English word of its gloss.
- `write`: write a message from moves in the notation and read it back, without sending it.
- `read`: read a received message through the toolchain.
- `send`: as the speaker, send the message written from your notation.
- `choose`: as the hearer, choose the concept by its letter.
"""


def _skill() -> str:
    """The skill's instructions without the front matter its loader reads."""
    text = open(os.path.join(ROOT, "skill", "rowih", "SKILL.md"), encoding="utf-8").read()
    return re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S).strip()


def _reference(name: str) -> str:
    path = os.path.join(ROOT, "skill", "rowih", "references", name)
    text = open(path, encoding="utf-8").read()
    return re.sub(r"\A<!--.*?-->\n", "", text, count=1, flags=re.S).strip()


def _section(path: str, heading: str, until: str) -> str:
    """The text of a Markdown file from `heading` up to the line `until`."""
    text = open(os.path.join(ROOT, path), encoding="utf-8").read()
    start = text.index(heading + "\n")
    end = text.index(until + "\n", start)
    body = re.sub(r"<!-- (generated: [a-z-]+|end generated) -->\n", "", text[start:end])
    return body.strip()


def system_prompt() -> str:
    """The system prompt: the game, the skill with its three references, and the
    specification's rules of word formation and of coining a word by definition. The
    grammar reference is the summary `rowih summary grammar` prints, made from the data."""
    formation = _section("specification/lexicon.md", "## Word formation",
                         "### Listed derivations and compounds")
    definition = _section("specification/lexicon.md", "## Coining a word by definition",
                          "## The codes from which forms are drawn")
    parts = [GAME, "# The skill\n\n" + _skill(), summary.grammar(data.load()).strip(),
             _reference("notation.md"), _reference("lexicon.md"),
             "# Word formation and definition, from the specification\n\n"
             + formation + "\n\n" + definition]
    return "\n\n".join(parts) + "\n"


def memory_text(memory: list) -> str:
    if not memory:
        return "Your memory holds no rounds yet."
    lines = ["Your memory of your last rounds, oldest first:", ""]
    for entry in memory:
        lines.append(entry)
        lines.append("")
    return "\n".join(lines).rstrip()


def speaker_task(agent: int, partner: int, round_no: int, concept: str,
                 memory: list) -> str:
    return (
        "You are agent %d. This is round %d.\n\n%s\n\n"
        "In this round you are the speaker. You are participant %d and your hearer is "
        "agent %d, participant %d.\n\n"
        "The concept to refer to: \"%s\"\n\n"
        "Compose one Rowih message that refers to it. Find words with `lookup`, write and "
        "check the message with `write`, and when it draws no diagnostic and says what you "
        "mean, call `send` with its notation."
        % (agent, round_no, memory_text(memory), agent, partner, partner, concept))


def hearer_task(agent: int, partner: int, round_no: int, message: str,
                candidates: list, memory: list) -> str:
    options = "\n".join("%s. %s" % (LETTERS[i], c) for i, c in enumerate(candidates))
    return (
        "You are agent %d. This is round %d.\n\n%s\n\n"
        "In this round you are the hearer. Agent %d (participant %d) sent you this "
        "message:\n\n<message>\n%s</message>\n\n"
        "Which of these concepts does it refer to?\n\n%s\n\n"
        "Read the message with `read`, look up any word you need with `lookup`, then call "
        "`choose` with the letter of the concept."
        % (agent, round_no, memory_text(memory), partner, partner, message, options))


def fresh_hearer_task(message: str, candidates: list) -> str:
    """The task of a hearer that was never in the population (PLAN.md § 4, the decoding
    test): the same message and choice, with no memory."""
    options = "\n".join("%s. %s" % (LETTERS[i], c) for i, c in enumerate(candidates))
    return (
        "You have received this Rowih message:\n\n<message>\n%s</message>\n\n"
        "It refers to one of these six concepts, for none of which the lexicon has a "
        "word. Which one?\n\n%s\n\n"
        "Read the message with `read`, look up any word you need with `lookup`, then call "
        "`choose` with the letter of the concept." % (message, options))
