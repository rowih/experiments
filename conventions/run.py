"""The naming game of PLAN.md § 4: a population of agents, interacting in pairs with no
central coordination, each referring to concepts the lexicon has no word for.

    uv run --with-requirements experiments/conventions/requirements.txt python experiments/conventions/run.py --rounds 50
    uv run --with-requirements experiments/conventions/requirements.txt python experiments/conventions/run.py --rounds 1 --out DIR

The run continues from what its transcripts already hold, to `--rounds` rounds in all;
given `--max-spend`, it stops before any call that could take the measured spend, in
dollars at the prices of config.json, past that limit. Rounds whose
agents differ run at once; each agent's rounds run in order, so every agent meets the
same sequence of rounds, and holds the same memory, as in a run one round at a time.
When an invocation plays a single round, it prints it: the message, its gloss and its
explanation, and the hearer's choice, which serves as the demonstration of two agents.
"""

import argparse
import asyncio
import glob
import json
import logging
import os
import random
import sys
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agents  # noqa: E402  the experiment's own modules, beside this file
import prompt  # noqa: E402
import tools  # noqa: E402
from rowih.writer import Envelope  # noqa: E402

log = logging.getLogger("conventions")


@dataclass(frozen=True)
class Spec:
    """A round as the seed fixes it before any is played."""
    number: int
    speaker: int
    hearer: int
    concept: int
    order: tuple


def schedule(config: dict, rounds: int) -> list:
    """Every random choice of the game, drawn from the one seed: the pair, the concept
    and the order in which the hearer is shown the six (PLAN.md § 7)."""
    rng = random.Random(config["seed"])
    n = config["population"]
    out = []
    for r in range(1, rounds + 1):
        speaker, hearer = rng.sample(range(1, n + 1), 2)
        concept = rng.randrange(len(config["concepts"]))
        order = tuple(rng.sample(range(len(config["concepts"])), len(config["concepts"])))
        out.append(Spec(r, speaker, hearer, concept, order))
    return out


def load_env(path: str | None) -> None:
    """Read KEY=VALUE lines into the environment, leaving any key already set. Nothing
    read here is logged or written."""
    if not path or not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def spent_so_far(root: str) -> float:
    """The measured spend of every call any transcript under `root` records."""
    total = 0.0
    for path in glob.glob(os.path.join(root, "**", "calls.jsonl"), recursive=True):
        for line in open(path, encoding="utf-8"):
            total += json.loads(line).get("cost", 0.0)
    return total


class Game:
    def __init__(self, config: dict, out: str, meter: agents.Meter):
        self.config, self.out, self.meter = config, out, meter
        self.concepts = [c["english"] for c in config["concepts"]]
        self.settings = agents.Settings(config["model"], config["effort"],
                                        config["max_tokens"], config["max_calls_per_turn"],
                                        prompt.system_prompt(),
                                        config["attempts_on_model_refusal"])
        self.client = agents.make_client()
        self.calls = agents.jsonl(os.path.join(out, "calls.jsonl"))
        self.rounds_log = agents.jsonl(os.path.join(out, "rounds.jsonl"))
        self.done = {}            # round number -> its record
        self.stop = None          # why the run stopped, once it has
        self._load()

    def _load(self) -> None:
        path = os.path.join(self.out, "rounds.jsonl")
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                rec = json.loads(line)
                self.done[rec["round"]] = rec

    def _history(self, agent: int, before: int) -> list:
        return [self.done[r] for r in sorted(self.done) if r < before
                and agent in (self.done[r]["speaker"], self.done[r]["hearer"])
                and (self.done[r]["speaker"] == agent or self.done[r]["message"])]

    def memory(self, agent: int, before: int) -> list:
        """The agent's last rounds, as many as the memory holds (PLAN.md § 4)."""
        rounds = self._history(agent, before)[-self.config["memory"]:]
        return [memory_entry(r, agent, self.concepts) for r in rounds]

    def envelope(self, spec: Spec) -> Envelope:
        """The speaker's envelope: its serial on the channel to this hearer, and the entry
        its first move adds, counted over the messages it has sent."""
        sent = [r for r in self._history(spec.speaker, spec.number)
                if r["speaker"] == spec.speaker and r["message"]]
        serial = 1 + sum(1 for r in sent if r["hearer"] == spec.hearer)
        first = 1 + sum(len(r["normal"]) for r in sent)
        clock = self.config["clock"]
        time = str(clock["start"] + spec.number * clock["seconds_per_round"])
        return Envelope(sender=spec.speaker, recipients=(spec.hearer,), time=time,
                        identifier=serial, first_entry=first)

    def _recorder(self, spec: Spec, agent: int, role: str):
        def record(entry: dict) -> None:
            self.calls(dict(entry, round=spec.number, agent=agent, role=role))
        return record

    async def speak(self, spec: Spec, envelope: Envelope) -> dict:
        state = {"attempts": [], "written": None, "failure": None}
        limit = self.config["refusals_before_failure"]

        def handle(name, args):
            if name == "lookup":
                return tools.lookup(args["term"]), False, False, None
            if name == "write":
                return tools.write(args["notation"], envelope), False, False, None
            if name == "read":
                return tools.read(args["message"]), False, False, None
            if name != "send":
                return "In this round you are the speaker: send a message.", True, False, None
            return send(state, args["notation"], envelope, limit)

        turn = agents.Turn(self.client, self.meter, self.settings, tools.TOOLS, handle,
                           self._recorder(spec, spec.speaker, "speaker"),
                           "Call `send` with your message's notation.")
        text = prompt.speaker_task(spec.speaker, spec.hearer, spec.number,
                                   self.concepts[spec.concept],
                                   self.memory(spec.speaker, spec.number))
        result = await turn.run(text)
        if state["written"] is None and state["failure"] is None:
            state["failure"] = result.reason
        return dict(state, turn=result)

    async def hear(self, spec: Spec, message: str) -> tuple:
        candidates = [self.concepts[i] for i in spec.order]

        def handle(name, args):
            if name == "lookup":
                return tools.lookup(args["term"]), False, False, None
            if name == "read":
                return tools.read(args["message"], message), False, False, None
            if name != "choose":
                return "In this round you are the hearer: choose a concept.", True, False, None
            return "", False, True, spec.order[prompt.LETTERS.index(args["concept"])]

        turn = agents.Turn(self.client, self.meter, self.settings, tools.TOOLS, handle,
                           self._recorder(spec, spec.hearer, "hearer"),
                           "Call `choose` with the letter of the concept.")
        text = prompt.hearer_task(spec.hearer, spec.speaker, spec.number, message,
                                  candidates, self.memory(spec.hearer, spec.number))
        result = await turn.run(text)
        return result.value, result

    async def play(self, spec: Spec) -> dict:
        envelope = self.envelope(spec)
        spoken = await self.speak(spec, envelope)
        written, choice, hearer_turn = spoken["written"], None, None
        if written is not None:
            choice, hearer_turn = await self.hear(spec, written.text)
        record = round_record(spec, envelope, spoken, written, choice, hearer_turn,
                              self.config)
        self.done[spec.number] = record
        self.rounds_log(record)
        log.info("round %d: %d to %d, concept %d, %s, $%.4f (spent $%.4f)", spec.number,
                 spec.speaker, spec.hearer, spec.concept,
                 "success" if record["success"] else "failure", record["cost"],
                 self.meter.spent)
        return record


def send(state: dict, notation: str, envelope: Envelope, limit: int) -> tuple:
    """The game's checks on a message sent (PLAN.md § 4, step 3): refused for a
    diagnostic or for inert material holding anything but Rowih words, and the round lost
    at the third refusal."""
    reason, written = None, None
    try:
        reason = tools.inert_refusal(notation)
        if reason is None:
            written = tools.write_message(notation, envelope)
            if written.diagnostics:
                reason = "the message draws diagnostics: %s" % " | ".join(
                    tools.diagnostic_text(d) for d in written.diagnostics)
    except (tools.InputError, tools.NotationError) as e:
        reason = "the notation could not be written: %s" % e
    state["attempts"].append({"notation": notation, "refused": reason})
    if reason is None:
        state["written"] = written
        return "", False, True, written
    refusals = sum(1 for a in state["attempts"] if a["refused"])
    if refusals >= limit:
        state["failure"] = "refused %d times" % refusals
        return "", True, True, None
    return ("Refused: %s. Correct the message and send it again (%d of %d refusals)."
            % (reason, refusals, limit)), True, False, None


def round_record(spec: Spec, envelope: Envelope, spoken: dict, written, choice,
                 hearer_turn, config: dict) -> dict:
    turns = [spoken["turn"]] + ([hearer_turn] if hearer_turn else [])
    return {
        "round": spec.number, "speaker": spec.speaker, "hearer": spec.hearer,
        "concept": spec.concept, "concept_key": config["concepts"][spec.concept]["key"],
        "order": list(spec.order),
        "envelope": {"identifier": envelope.identifier, "first_entry": envelope.first_entry,
                     "time": envelope.time},
        "attempts": spoken["attempts"], "failure": spoken["failure"],
        "message": written.text if written else None,
        "moves_text": written.moves_text if written else None,
        "normal": written.normal if written else [],
        "english": written.english if written else None,
        "words": written.words if written else None,
        "choice": choice, "success": choice == spec.concept,
        "hearer_ended": hearer_turn.reason if hearer_turn else None,
        "calls": sum(t.calls for t in turns), "cost": sum(t.cost for t in turns),
        "model_refusals": sum(t.model_refusals for t in turns),
        "models": sorted({m for t in turns for m in t.models}),
    }


def memory_entry(record: dict, agent: int, concepts: list) -> str:
    """A round as an agent remembers it: the concept or the candidates, the message sent
    or received, and whether the round succeeded (PLAN.md § 4)."""
    r, concept = record["round"], concepts[record["concept"]]
    chosen = concepts[record["choice"]] if record["choice"] is not None else None
    outcome = "the round succeeded" if record["success"] else "the round failed"
    if record["speaker"] == agent:
        head = "Round %d: you were the speaker, to agent %d. The concept: \"%s\"." % (
            r, record["hearer"], concept)
        if not record["message"]:
            return head + " No message was sent (%s), and the round failed." % (
                record["failure"])
        heard = ("Agent %d chose \"%s\": %s." % (record["hearer"], chosen, outcome)
                 if chosen else "Agent %d made no choice: %s." % (record["hearer"], outcome))
        return "%s You sent these moves:\n%s\nTheir literal semantic form:\n%s\n%s" % (
            head, record["moves_text"], "\n".join(record["normal"]), heard)
    head = "Round %d: you were the hearer, from agent %d. You received these moves:\n%s\n" \
           "Their literal semantic form:\n%s\n" % (r, record["speaker"], record["moves_text"],
                                                   "\n".join(record["normal"]))
    you = "You chose \"%s\"" % chosen if chosen else "You made no choice"
    return "%s%s; agent %d had been shown \"%s\": %s." % (head, you, record["speaker"],
                                                          concept, outcome)


async def play_all(game: Game, specs: list, concurrency: int) -> list:
    """Play every spec not yet played, each round after the earlier rounds of both its
    agents. A round whose earlier round failed to finish is not played."""
    gate = asyncio.Semaphore(concurrency)
    last = {}
    played = []

    async def one(spec, deps):
        await asyncio.gather(*deps)
        if game.stop:
            raise asyncio.CancelledError
        async with gate:
            if game.stop:
                raise asyncio.CancelledError
            try:
                played.append(await game.play(spec))
            except agents.SpendLimitReached as e:
                game.stop = "spend limit: %s" % e
                raise
            except Exception as e:
                game.stop = "error in round %d: %s: %s" % (spec.number, type(e).__name__, e)
                raise

    tasks = []
    for spec in specs:
        if spec.number in game.done:
            continue
        deps = [t for t in (last.get(spec.speaker), last.get(spec.hearer)) if t]
        task = asyncio.create_task(one(spec, deps))
        last[spec.speaker] = last[spec.hearer] = task
        tasks.append(task)
    await asyncio.gather(*tasks, return_exceptions=True)
    return played


def show(record: dict, concepts: list) -> None:
    """Print a single round: the demonstration of two agents (PLAN.md § 7)."""
    out = ["Round %d: agent %d speaks to agent %d." % (record["round"], record["speaker"],
                                                       record["hearer"]),
           "The concept shown to agent %d: %s" % (record["speaker"],
                                                   concepts[record["concept"]])]
    for i, a in enumerate(record["attempts"], 1):
        out.append("Attempt %d: %s" % (i, "refused: " + a["refused"] if a["refused"]
                                       else "sent"))
        out.append("  notation: " + a["notation"].replace("\n", "\n            "))
    if record["message"]:
        out += ["", "The message:", record["message"].rstrip("\n"), "",
                tools.read(record["message"]), ""]
        chosen = concepts[record["choice"]] if record["choice"] is not None else "nothing"
        out.append("Agent %d chose: %s (%s)." % (record["hearer"], chosen,
                                                  "success" if record["success"]
                                                  else "failure"))
    else:
        out.append("No message was sent: %s." % record["failure"])
    out.append("Calls: %d, cost $%.4f." % (record["calls"], record["cost"]))
    print("\n".join(out))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--rounds", type=int, required=True,
                        help="play until this many rounds in all have been played")
    parser.add_argument("--out", default=os.path.join(HERE, "transcripts"),
                        help="the directory of this run's transcripts")
    parser.add_argument("--config", default=os.path.join(HERE, "config.json"))
    parser.add_argument("--env-file", default=None,
                        help="a file of KEY=VALUE lines holding the API keys")
    parser.add_argument("--max-spend", type=float, default=None,
                        help="stop before the measured spend, in dollars, could pass this")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    for name in ("httpx", "httpx2", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    config = json.load(open(args.config, encoding="utf-8"))
    load_env(args.env_file)
    os.makedirs(args.out, exist_ok=True)
    ledger = os.path.join(HERE, "transcripts")
    spent = spent_so_far(ledger) + (0.0 if os.path.abspath(args.out).startswith(
        os.path.abspath(ledger)) else spent_so_far(args.out))
    meter = agents.Meter(args.max_spend, spent, agents.Prices.of(config))
    game = Game(config, args.out, meter)
    played = asyncio.run(play_all(game, schedule(config, args.rounds),
                                  config["concurrency"]))
    if len(played) == 1:
        show(played[0], game.concepts)
    log.info("played %d rounds; %d in all; spent $%.4f%s", len(played), len(game.done),
             meter.spent, "; stopped: " + game.stop if game.stop else "")
    return 1 if game.stop else 0


if __name__ == "__main__":
    sys.exit(main())
