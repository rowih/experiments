"""One agent's turn with Claude, and the meter that prices it (PLAN.md § 6).

The meter prices every response's reported usage after the call. Given a limit, it
refuses a call before it is made when the spend so far, the worst case of the calls in
flight and the worst case of this one could together pass the limit.
"""

import asyncio
import json
import logging
import time
import traceback
from dataclasses import dataclass, field

import anthropic

log = logging.getLogger("conventions")

MILLION = 1_000_000


class SpendLimitReached(Exception):
    """A call refused because it could take the spend past the limit given."""


@dataclass
class Prices:
    """Dollars per million tokens for one model, with the higher prices that apply to a
    request whose prompt passes the threshold."""
    input: float
    output: float
    cache_read: float
    cache_write: float
    threshold: int
    long_input: float
    long_output: float
    long_cache_read: float
    long_cache_write: float

    @classmethod
    def of(cls, config: dict) -> "Prices":
        p = config["prices_usd_per_million"]
        return cls(p["input"], p["output"], p["cache_read"], p["cache_write_5m"],
                   p["long_context_threshold"], p["long_input"], p["long_output"],
                   p["long_cache_read"], p["long_cache_write_5m"])

    def cost(self, usage: dict) -> float:
        fresh = usage.get("input_tokens") or 0
        read = usage.get("cache_read_input_tokens") or 0
        written = usage.get("cache_creation_input_tokens") or 0
        out = usage.get("output_tokens") or 0
        if fresh + read + written > self.threshold:
            rates = (self.long_input, self.long_cache_read, self.long_cache_write,
                     self.long_output)
        else:
            rates = (self.input, self.cache_read, self.cache_write, self.output)
        return (fresh * rates[0] + read * rates[1] + written * rates[2]
                + out * rates[3]) / MILLION

    def worst_case(self, prompt_tokens: int, max_tokens: int) -> float:
        """The most a call could cost: its whole prompt written to the cache, at the
        higher prices if it could pass the threshold, and its whole output."""
        long = prompt_tokens > self.threshold
        write = self.long_cache_write if long else self.cache_write
        out = self.long_output if long else self.output
        return (prompt_tokens * write + max_tokens * out) / MILLION


@dataclass
class Meter:
    limit: float | None
    spent: float
    prices: Prices
    in_flight: float = 0.0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def reserve(self, worst: float) -> None:
        async with self.lock:
            if self.limit is not None and self.spent + self.in_flight + worst > self.limit:
                raise SpendLimitReached(
                    "spent $%.4f, in flight $%.4f, next call up to $%.4f, limit $%.2f"
                    % (self.spent, self.in_flight, worst, self.limit))
            self.in_flight += worst

    async def settle(self, worst: float, usage: dict | None) -> float:
        cost = self.prices.cost(usage) if usage else 0.0
        async with self.lock:
            self.in_flight -= worst
            self.spent += cost
        return cost


@dataclass
class Settings:
    model: str
    effort: str
    max_tokens: int
    max_calls: int
    system: str
    refusal_attempts: int = 3


@dataclass
class TurnResult:
    """How a turn ended: `value` is what the terminal tool returned, or None when the turn
    ended without one, with `reason` saying why."""
    value: object
    reason: str
    calls: int
    cost: float
    models: list
    model_refusals: int = 0


def _dump(blocks) -> list:
    """The blocks of a response as the transcript keeps them: a thinking block's
    signature, and a redacted block's data, are left out, since they serve only to send a
    conversation back to the model and carry nothing a reader of the transcript can use."""
    out = []
    for b in blocks:
        d = b.model_dump(mode="json", exclude_none=True)
        if d.get("type") in ("thinking", "redacted_thinking"):
            d.pop("signature", None)
            d.pop("data", None)
        out.append(d)
    return out


def _details(response):
    details = getattr(response, "stop_details", None)
    return details.model_dump(mode="json", exclude_none=True) if details else None


def _usage(response) -> dict:
    return response.usage.model_dump(mode="json", exclude_none=True)


class Turn:
    """One agent's turn: calls the model until a terminal tool ends the turn, the turn
    runs out of calls, or the model refuses.

    `handle(name, input)` runs a tool and returns (text, is_error, done, value): `done`
    ends the turn with `value`."""

    def __init__(self, client: anthropic.AsyncAnthropic, meter: Meter, settings: Settings,
                 tools: list, handle, record, nudge: str):
        self.client, self.meter, self.settings = client, meter, settings
        self.tools, self.handle, self.record, self.nudge = tools, handle, record, nudge
        self.prompt_tokens = 0
        self.cost = 0.0
        self.models = []
        self.refusals = 0

    async def _call(self, messages: list):
        s = self.settings
        estimate = (self.prompt_tokens or len(s.system) // 2) + 8_000
        worst = self.meter.prices.worst_case(estimate, s.max_tokens)
        await self.meter.reserve(worst)
        usage = None
        try:
            response = await self.client.messages.create(
                model=s.model, max_tokens=s.max_tokens, tools=self.tools,
                system=[{"type": "text", "text": s.system,
                         "cache_control": {"type": "ephemeral"}}],
                messages=messages, cache_control={"type": "ephemeral"},
                output_config={"effort": s.effort})
            usage = _usage(response)
        finally:
            cost = await self.meter.settle(worst, usage)
        self.cost += cost
        self.prompt_tokens = sum(usage.get(k) or 0 for k in (
            "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        self.models.append(response.model)
        return response, cost

    def _log(self, n: int, attempt: int, response, cost: float, sent, results) -> None:
        self.record({"call": n, "attempt": attempt, "model": response.model,
                     "request": response._request_id, "stop_reason": response.stop_reason,
                     "stop_details": _details(response), "usage": _usage(response),
                     "cost": cost, "spent": self.meter.spent, "sent": sent,
                     "content": _dump(response.content), "tool_results": results})

    async def _answer(self, messages: list, n: int, sent) -> tuple:
        """A response to `messages`. A response the model's safety classifier declines,
        with stop_reason refusal, is logged and the same request made again, up to the
        number of attempts the settings allow; the last is returned whatever it is."""
        for attempt in range(1, self.settings.refusal_attempts + 1):
            response, cost = await self._call(messages)
            if response.stop_reason != "refusal" or \
                    attempt == self.settings.refusal_attempts:
                return response, cost, attempt
            self.refusals += 1
            self._log(n, attempt, response, cost, sent, [])
        raise AssertionError("unreachable: the loop returns on its last attempt")

    def _result(self, value, reason: str, calls: int) -> TurnResult:
        return TurnResult(value, reason, calls, self.cost, self.models, self.refusals)

    async def run(self, user_text: str) -> TurnResult:
        messages = [{"role": "user", "content": user_text}]
        for n in range(1, self.settings.max_calls + 1):
            sent = messages[-1]["content"]
            response, cost, attempt = await self._answer(messages, n, sent)
            messages.append({"role": "assistant", "content": response.content})
            results, done, value = self._tools(response)
            self._log(n, attempt, response, cost, sent, results)
            if done:
                return self._result(value, "done", n)
            if response.stop_reason == "refusal":
                self.refusals += 1
                return self._result(None, "model refusal", n)
            messages.append({"role": "user", "content": results or self.nudge})
        return self._result(None, "no terminal tool within %d calls"
                            % self.settings.max_calls, self.settings.max_calls)

    def _run_tool(self, block) -> tuple:
        """A tool's answer. The toolchain is meant to refuse bad input with its own error
        types, which the tools turn into text; any other exception is a defect of the
        toolchain, so it is logged with the input that raised it and reported to the agent
        as a failed call, and the game goes on (the boundary of the harness)."""
        try:
            return self.handle(block.name, block.input)
        except Exception as e:  # noqa: BLE001  reported to the agent and logged, see above
            log.warning("tool %s raised %s: %s on %s", block.name, type(e).__name__, e,
                        json.dumps(block.input, ensure_ascii=False))
            self.record({"tool_error": {"tool": block.name, "input": block.input,
                                        "error": "%s: %s" % (type(e).__name__, e),
                                        "trace": traceback.format_exc(limit=-6)}})
            return ("The toolchain raised an internal error (%s: %s) on this input; it is "
                    "a fault of the toolchain, not a diagnostic of the message. Try another "
                    "way of writing it." % (type(e).__name__, e)), True, False, None

    def _tools(self, response) -> tuple:
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            text, is_error, done, value = self._run_tool(block)
            if done:
                return results, True, value
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": text, "is_error": is_error})
        return results, False, None


def make_client(timeout: float = 120.0) -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(timeout=timeout, max_retries=4)


def jsonl(path: str):
    """An appender of one JSON line per record, flushed at once."""
    handle = open(path, "a", encoding="utf-8")

    def append(record: dict) -> None:
        record = dict(record, at=time.time())
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        handle.flush()
    return append
