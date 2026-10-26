"""The measures of PLAN.md § 5 over a run's transcripts, and the answers of § 9.

    uv run --with-requirements experiments/conventions/requirements.txt python experiments/conventions/analyse.py [--out DIR]

Written and committed before the pilot (PLAN.md § 5). Choices the plan leaves open are
fixed here, before any run:

- A round's *form* is the sequence of its message's moves' normal forms, as the
  toolchain's printer writes them, joined by line breaks. A round with no message, every
  attempt refused, has no form.
- A concept's *settled form* is the commonest form among the last 200 rounds in which it
  was the concept, provided its share is at least 0.5; the share is counted over those of
  the 200 rounds that have a form, and the rounds with none are reported beside it.
- *Route* is classified from the normal forms: a definition, if a move is a setting of
  kind definition; else a compound or derivation, if a move holds a word read from its
  parts, written `(unknown "FORM")`; else an existing word or idiom of the lexicon, if a
  move names a content word or an idiom; else other. The shares are given over messages
  and over distinct forms.
- *Length* is the number of words of a message's moves, without the envelope.
- *Refusals* are counted over every attempt to send, and classed by the diagnostic's
  code, by inert material, or by a notation that could not be written.

Two measures are secondary, declared here before any run, and reported as such:

- the settled form over each concept's last 50 rounds, by the same rule, since at the
  length of this run the window of 200 rounds covers nearly every round of a concept;
- the *lexical form* of a round: the sorted content words of its moves (roots, words read
  from their parts, idioms and defined words), without the grammatical frame, and its
  convergence by the measure of § 5.2.
"""

import argparse
import gzip
import json
import math
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))

NOTATION_HEADS = {"move", "assertion", "situation", "term", "readings", "quote", "example",
                  "data", "idiom", "slot", "unknown", "q", "party", "dialect", "names",
                  "deadline", "authority", "message", "entry", "same"}
ROUTES = ("definition", "compound or derivation", "existing word or idiom", "other")
STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


def _lines(out: str, name: str) -> list:
    """The records of `name`, read from the file or, where only that is present, from its
    compressed copy, as the published transcripts are kept."""
    path = os.path.join(out, name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f]
    with gzip.open(path + ".gz", "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load(out: str) -> tuple:
    rounds = _lines(out, "rounds.jsonl")
    rounds.sort(key=lambda r: r["round"])
    return rounds, _lines(out, "calls.jsonl")


def form(record: dict) -> str | None:
    return "\n".join(record["normal"]) if record["message"] else None


def lexical_form(record: dict) -> str | None:
    """The sorted content words of a round's moves, without the frame around them."""
    if not record["message"]:
        return None
    words = []
    for nf in record["normal"]:
        for kind, value in re.findall(r'\((unknown|idiom) "?([^")\s]+)"?\)', nf):
            words.append("%s:%s" % (kind, value))
        for value in re.findall(r'\(data "text/prs\.rowih" "([^"]+)"\)', nf):
            words.append("defined:%s" % value)
        bare = re.sub(r"\((unknown|idiom|data)[^()]*\)", " ", STRING.sub(" ", nf))
        words += [a for a in re.findall(r"(?<![\w.-])[a-z][a-z0-9.-]*", bare)
                  if a not in NOTATION_HEADS]
    return " ".join(sorted(words))


def route(record: dict) -> str | None:
    if not record["message"]:
        return None
    normal = record["normal"]
    if any(nf.startswith("(move SETTING DEFINITION") for nf in normal):
        return "definition"
    if any('(unknown "' in nf for nf in normal):
        return "compound or derivation"
    if any(lexical_form(dict(record, normal=[nf])) for nf in normal):
        return "existing word or idiom"
    return "other"


def blocks(rounds: list, size: int) -> list:
    """The rounds in successive blocks of `size` round numbers."""
    if not rounds:
        return []
    last = max(r["round"] for r in rounds)
    return [(start, [r for r in rounds if start <= r["round"] < start + size])
            for start in range(1, last + 1, size)]


def success(rounds: list) -> list:
    return [{"rounds": "%d-%d" % (s, s + 99), "played": len(b),
             "success": sum(r["success"] for r in b) / len(b) if b else None}
            for s, b in blocks(rounds, 100)]


def _spread(rounds: list, concept: int, of) -> dict:
    forms = [of(r) for r in rounds if r["concept"] == concept and of(r)]
    if not forms:
        return {"rounds": 0, "distinct": 0, "commonest share": None}
    top = Counter(forms).most_common(1)[0][1]
    return {"rounds": len(forms), "distinct": len(set(forms)),
            "commonest share": top / len(forms)}


def convergence(rounds: list, n_concepts: int, of=form) -> list:
    return [{"rounds": "%d-%d" % (s, s + 199),
             "concepts": [_spread(b, c, of) for c in range(n_concepts)]}
            for s, b in blocks(rounds, 200)]


def settled(rounds: list, concept: int, window: int, share: float, of=form) -> dict:
    """The settled form of a concept by PLAN.md § 4, with the latest message in it."""
    mine = [r for r in rounds if r["concept"] == concept][-window:]
    forms = [(of(r), r) for r in mine if of(r)]
    out = {"window rounds": len(mine), "with a form": len(forms),
           "without a form": len(mine) - len(forms), "form": None, "share": None,
           "message": None, "round": None}
    if not forms:
        return out
    top, count = Counter(f for f, _ in forms).most_common(1)[0]
    out["share"] = count / len(forms)
    if out["share"] >= share:
        latest = [r for f, r in forms if f == top][-1]
        out.update(form=top, message=latest["message"], round=latest["round"],
                   route=route(latest), words=latest["words"])
    return out


def routes(rounds: list, settled_forms: list) -> dict:
    sent = [r for r in rounds if r["message"]]
    by_form = {form(r): route(r) for r in sent}

    def shares(items):
        c = Counter(items)
        return {k: c[k] / len(items) if items else None for k in ROUTES}
    return {"messages": shares([route(r) for r in sent]),
            "distinct forms": shares(list(by_form.values())),
            "settled forms": shares([s["route"] for s in settled_forms if s["form"]])}


def length(rounds: list) -> list:
    out = []
    for s, b in blocks(rounds, 100):
        words = [r["words"] for r in b if r["message"]]
        out.append({"rounds": "%d-%d" % (s, s + 99), "messages": len(words),
                    "mean words": sum(words) / len(words) if words else None})
    return out


def refusal_reason(reason: str) -> str:
    if reason.startswith("the message draws diagnostics"):
        codes = sorted(set(re.findall(r"d\.[a-z0-9.-]+[a-z0-9]", reason)))
        return "diagnostic " + ", ".join(codes) if codes else "diagnostic"
    if reason.startswith("the notation could not be written"):
        return "notation not written"
    return "inert material"


def refusals(rounds: list) -> dict:
    attempts = [a for r in rounds for a in r["attempts"]]
    refused = [a["refused"] for a in attempts if a["refused"]]
    return {"attempts": len(attempts), "refused": len(refused),
            "rate": len(refused) / len(attempts) if attempts else None,
            "by reason": dict(Counter(refusal_reason(x) for x in refused).most_common()),
            "rounds lost to refusals": sum(1 for r in rounds if not r["message"])}


def binomial_tail(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p): how often chance alone would do as well."""
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def transparency(out: str, n_concepts: int, test: str = "primary") -> dict | None:
    """Each fresh hearer's accuracy on the forms of one test, against chance at 1 in
    `n_concepts`, with how often chance alone would do as well; no threshold is set
    (PLAN.md § 9)."""
    path = os.path.join(out, "decoding", "results.jsonl")
    if not os.path.exists(path):
        return None
    results = [r for r in map(json.loads, open(path, encoding="utf-8")) if r["test"] == test]
    by_hearer = {}
    for r in results:
        by_hearer.setdefault(r["hearer"], []).append(r)
    chance = 1 / n_concepts
    table = {}
    for hearer, rs in sorted(by_hearer.items()):
        k = sum(r["correct"] for r in rs)
        table[hearer] = {"model": rs[0]["model"], "forms": len(rs), "correct": k,
                         "accuracy": k / len(rs), "chance": chance,
                         "P(as good by chance)": binomial_tail(k, len(rs), chance),
                         "per form": {r["concept_key"]: r["correct"] for r in rs}}
    return table


def spend(calls: list) -> dict:
    """The calls' measured spend and the models that answered them; the log's records of
    a toolchain fault are counted apart, since they are not calls."""
    faults = [c["tool_error"] for c in calls if "tool_error" in c]
    calls = [c for c in calls if "cost" in c]
    return {"calls": len(calls), "usd": sum(c["cost"] for c in calls),
            "models": dict(Counter(c["model"] for c in calls)),
            "declined by the model's classifier": sum(1 for c in calls
                                                       if c["stop_reason"] == "refusal"),
            "toolchain faults": len(faults),
            "toolchain faults by error": dict(Counter(f["error"] for f in faults))}


def analyse(out: str, config: dict) -> dict:
    rounds, calls = load(out)
    n = len(config["concepts"])
    window, share = config["settled"]["window"], config["settled"]["share"]
    primary = [dict(settled(rounds, c, window, share), concept=config["concepts"][c]["key"])
               for c in range(n)]
    return {
        "rounds played": len(rounds),
        "1 success": success(rounds),
        "2 convergence": convergence(rounds, n),
        "settled forms (Q1)": primary,
        "Q1 answer": sum(1 for s in primary if s["form"]),
        "3 route": routes(rounds, primary),
        "4 length": length(rounds),
        "5 transparency (Q2)": transparency(out, n),
        "6 refusals": refusals(rounds),
        "secondary: transparency of the forms settled over the last 50 rounds":
            transparency(out, n, "secondary"),
        "exploratory: transparency of each unsettled concept's commonest recent form":
            transparency(out, n, "exploratory"),
        "secondary: settled over the last 50 rounds of each concept":
            [dict(settled(rounds, c, 50, share), concept=config["concepts"][c]["key"])
             for c in range(n)],
        "secondary: convergence of lexical forms": convergence(rounds, n, lexical_form),
        "spend": spend(calls),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="The measures of PLAN.md § 5.")
    parser.add_argument("--out", default=os.path.join(HERE, "transcripts"))
    parser.add_argument("--config", default=os.path.join(HERE, "config.json"))
    args = parser.parse_args()
    config = json.load(open(args.config, encoding="utf-8"))
    result = analyse(args.out, config)
    path = os.path.join(args.out, "analysis.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in result.items() if k != "2 convergence"
                      and not k.startswith("secondary: convergence")}, indent=1,
                     ensure_ascii=False)[:20000])


if __name__ == "__main__":
    main()
