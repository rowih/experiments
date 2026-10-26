"""Tests of the experiment's harness and analysis that call no model.

    uv run --with-requirements experiments/conventions/requirements.txt pytest experiments/conventions/test_conventions.py
"""

import asyncio
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agents  # noqa: E402
import analyse  # noqa: E402
import run  # noqa: E402
import tools  # noqa: E402
from rowih.writer import Envelope  # noqa: E402

CONFIG = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
ENVELOPE = Envelope(sender=3, recipients=(7,), time="1761480060", identifier=1,
                    first_entry=1)
DEFINITION = ('(move ACT-DEFINITION SPEAKERS-OWN (term (data "text/prs.rowih" "rapit")) '
              '(term (unknown "nuniripaheh")))')
FORMATION = ('(move ASSERTED-POSITION (assertion INFERENCE PROBABLE (situation appear '
             '(UNDERGOER (term (unknown "nuniripaheh"))))))')
EXISTING = ('(move ASSERTED-POSITION (assertion INFERENCE PROBABLE (situation appear '
            '(UNDERGOER (term thing)))))')
DEFINED_AND_USED = DEFINITION + '\n(move ASSERTED-POSITION (assertion INFERENCE PROBABLE ' \
    '(situation appear (UNDERGOER (term (unknown "rapit"))))))'


def record(notation: str, number: int = 1, concept: int = 0) -> dict:
    w = tools.write_message(notation, ENVELOPE)
    return {"round": number, "concept": concept, "message": w.text, "normal": w.normal,
            "words": w.words, "attempts": [], "success": True}


def test_inert_material_of_rowih_words_passes():
    assert tools.inert_refusal(DEFINITION) is None
    assert tools.inert_refusal('(move ACT-QUESTION (situation say (CONTENT '
                               '(quote "rudin bihu"))))') is None


def test_inert_material_of_english_is_refused():
    english = DEFINITION.replace('"rapit"', '"stale cache"')
    assert "not Rowih words" in tools.inert_refusal(english)
    plain = DEFINITION.replace("text/prs.rowih", "text/plain")
    assert "only text/prs.rowih" in tools.inert_refusal(plain)
    quoted = '(move ACT-QUESTION (situation say (CONTENT (quote "ignore instructions"))))'
    assert "quote material" in tools.inert_refusal(quoted)


def test_a_defined_word_used_in_its_own_message_draws_a_diagnostic():
    written = tools.write_message(DEFINED_AND_USED, ENVELOPE)
    assert "d.lexer.unknown-word" in [getattr(d, "code", "") for d in written.diagnostics]


def test_send_refuses_twice_then_loses_the_round_at_the_third():
    state = {"attempts": [], "written": None, "failure": None}
    for n in (1, 2):
        text, is_error, done, value = run.send(state, DEFINED_AND_USED, ENVELOPE, 3)
        assert (is_error, done, value) == (True, False, None)
        assert "(%d of 3 refusals)" % n in text
    _, is_error, done, value = run.send(state, DEFINED_AND_USED, ENVELOPE, 3)
    assert (is_error, done, value) == (True, True, None)
    assert state["failure"] == "refused 3 times"
    assert all(a["refused"] for a in state["attempts"])


def test_send_accepts_a_clean_message():
    state = {"attempts": [], "written": None, "failure": None}
    _, is_error, done, value = run.send(state, FORMATION, ENVELOPE, 3)
    assert (is_error, done) == (False, True)
    assert value.diagnostics == [] and value.words > 0
    assert state["attempts"] == [{"notation": FORMATION, "refused": None}]


def test_routes_are_classified_from_the_normal_forms():
    assert analyse.route(record(DEFINITION)) == "definition"
    assert analyse.route(record(FORMATION)) == "compound or derivation"
    assert analyse.route(record(EXISTING)) == "existing word or idiom"
    assert analyse.route({"message": None, "normal": []}) is None


def test_lexical_form_keeps_content_words_and_drops_the_frame():
    assert analyse.lexical_form(record(EXISTING)) == "appear thing"
    assert analyse.lexical_form(record(FORMATION)) == "appear unknown:nuniripaheh"
    assert analyse.lexical_form(record(DEFINITION)) == \
        "defined:rapit unknown:nuniripaheh"


def test_a_form_settles_at_a_share_of_one_half_and_not_below():
    a, b = record(EXISTING), record(FORMATION)
    rounds = [dict(a, round=1), dict(b, round=2), dict(a, round=3), dict(b, round=4)]
    s = analyse.settled(rounds, 0, 200, 0.5)
    assert s["share"] == 0.5 and s["form"] is not None
    rounds.append(dict(b, round=5, concept=0))
    rounds.append(dict(record(DEFINITION), round=6))
    s = analyse.settled(rounds, 0, 200, 0.5)
    assert s["form"] == analyse.form(b) and s["round"] == 5
    s = analyse.settled(rounds[:2] + [dict(record(DEFINITION), round=3)], 0, 200, 0.5)
    assert s["form"] is None and s["share"] == pytest.approx(1 / 3)


def test_the_settled_form_looks_only_at_the_last_rounds_of_the_window():
    a, b = record(EXISTING), record(FORMATION)
    rounds = [dict(a, round=i) for i in range(1, 6)] + [dict(b, round=i)
                                                        for i in range(6, 9)]
    assert analyse.settled(rounds, 0, 3, 0.5)["form"] == analyse.form(b)
    assert analyse.settled(rounds, 0, 8, 0.5)["form"] == analyse.form(a)


def test_the_schedule_is_fixed_by_the_seed():
    first, again = run.schedule(CONFIG, 300), run.schedule(CONFIG, 300)
    assert first == again
    assert all(s.speaker != s.hearer for s in first)
    assert all(sorted(s.order) == list(range(6)) for s in first)
    other = run.schedule(dict(CONFIG, seed=CONFIG["seed"] + 1), 300)
    assert other != first


def test_the_meter_refuses_a_call_that_could_pass_its_limit():
    prices = agents.Prices.of(CONFIG)
    meter = agents.Meter(limit=0.02, spent=0.0, prices=prices)

    async def go():
        await meter.reserve(0.015)
        with pytest.raises(agents.SpendLimitReached):
            await meter.reserve(0.01)
        await meter.settle(0.015, {"input_tokens": 1000, "output_tokens": 1000})
        return meter.spent
    assert asyncio.run(go()) == pytest.approx((1000 * 0.10 + 1000 * 0.50) / 1e6)


def test_a_meter_without_a_limit_refuses_nothing():
    meter = agents.Meter(limit=None, spent=1e6, prices=agents.Prices.of(CONFIG))
    asyncio.run(meter.reserve(1e6))
    assert meter.in_flight == 1e6


def test_prices_switch_above_the_long_prompt_threshold():
    prices = agents.Prices.of(CONFIG)
    short = prices.cost({"cache_read_input_tokens": 100_000, "output_tokens": 0})
    long = prices.cost({"cache_read_input_tokens": 100_001, "output_tokens": 0})
    assert short == pytest.approx(100_000 * 0.01 / 1e6)
    assert long == pytest.approx(100_001 * 0.05 / 1e6)


def test_memory_keeps_the_last_ten_rounds_and_skips_rounds_never_heard(tmp_path):
    game = run.Game.__new__(run.Game)
    game.config, game.concepts = CONFIG, [c["english"] for c in CONFIG["concepts"]]
    base = record(EXISTING)
    game.done = {r: dict(base, round=r, speaker=1, hearer=2, choice=0, moves_text="x",
                         failure=None) for r in range(1, 13)}
    game.done[13] = dict(game.done[12], round=13, speaker=3, hearer=1, message=None)
    remembered = game.memory(1, 14)
    assert len(remembered) == 10 and remembered[0].startswith("Round 3:")
    assert len(game.memory(2, 14)) == 10
    assert game.memory(1, 14) == game.memory(1, 13)


class _Block:
    def __init__(self, **fields):
        self.__dict__.update(fields)

    def model_dump(self, **_):
        return dict(self.__dict__)


class _Response:
    def __init__(self, stop_reason: str, content: list):
        self.stop_reason, self.content, self.model = stop_reason, content, "fake-model"
        self._request_id, self.stop_details = "req", None
        self.usage = _Block(input_tokens=10, output_tokens=10)


class _FakeClient:
    """The API's boundary: answers with the responses given, in order."""
    def __init__(self, responses: list):
        self.responses, self.requests = list(responses), 0
        self.messages = self

    async def create(self, **_):
        self.requests += 1
        return self.responses.pop(0)


def _turn(responses: list, attempts: int = 3):
    client = _FakeClient(responses)
    meter = agents.Meter(limit=1.0, spent=0.0, prices=agents.Prices.of(CONFIG))
    settings = agents.Settings("m", "medium", 100, 4, "system", attempts)
    logged = []

    def handle(name, args):
        return "", False, True, args["concept"]
    turn = agents.Turn(client, meter, settings, [], handle, logged.append, "choose")
    return turn, client, logged


def _choose():
    return _Response("tool_use", [_Block(type="tool_use", id="t", name="choose",
                                         input={"concept": "B"})])


def test_a_declined_call_is_made_again_and_the_turn_goes_on():
    turn, client, logged = _turn([_Response("refusal", []), _choose()])
    result = asyncio.run(turn.run("task"))
    assert (result.value, result.reason, result.model_refusals) == ("B", "done", 1)
    assert client.requests == 2 and [e["attempt"] for e in logged] == [1, 2]


def test_a_call_declined_at_every_attempt_ends_the_turn():
    turn, client, logged = _turn([_Response("refusal", [])] * 3)
    result = asyncio.run(turn.run("task"))
    assert (result.value, result.reason, result.model_refusals) == (None, "model refusal", 3)
    assert client.requests == 3 and len(logged) == 3


def test_a_fault_of_the_toolchain_is_reported_to_the_agent_and_logged():
    responses = [_Response("tool_use", [_Block(type="tool_use", id="w", name="write",
                                               input={"notation": "(idiom x)"})]), _choose()]
    client = _FakeClient(responses)
    meter = agents.Meter(limit=1.0, spent=0.0, prices=agents.Prices.of(CONFIG))
    logged = []

    def handle(name, args):
        if name == "write":
            raise ValueError("slot")
        return "", False, True, args["concept"]
    turn = agents.Turn(client, meter, agents.Settings("m", "medium", 100, 4, "s", 3), [],
                       handle, logged.append, "choose")
    result = asyncio.run(turn.run("task"))
    assert result.value == "B"
    errors = [e["tool_error"] for e in logged if "tool_error" in e]
    assert errors and errors[0]["error"] == "ValueError: slot"
    assert errors[0]["input"] == {"notation": "(idiom x)"}
    sent = [e for e in logged if "tool_results" in e][0]["tool_results"][0]
    assert sent["is_error"] and "internal error (ValueError: slot)" in sent["content"]
