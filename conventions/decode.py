"""The decoding test of PLAN.md § 4: each settled form shown, with the toolchain's tools,
to hearers that were never in the population: three new instances of the population's
model, one Gemini model and one OpenAI model. Each chooses among the six concepts.

    uv run --with-requirements experiments/conventions/requirements.txt python experiments/conventions/decode.py --env-file .env

The forms decoded are the settled forms of the primary rule. As a secondary test,
declared before any run, the settled forms of the secondary rule (each concept's last 50
rounds) that differ from them are decoded too, and reported apart.

An exploratory test was added on 2026-10-26, after the main run and before any decoding:
only one concept settled by either rule, so the decoding test of PLAN.md § 4 had a single
form, which says little about whether a hearer outside the population reads the coined
words. For each concept with no settled form, the commonest form of its last 50 rounds is
decoded by the same hearers. It is reported apart, as exploratory, and answers no question
of PLAN.md § 9.
"""

import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import agents  # noqa: E402
import analyse  # noqa: E402
import prompt  # noqa: E402
import run  # noqa: E402
import tools  # noqa: E402

log = logging.getLogger("conventions")


def forms_to_decode(out: str, config: dict) -> list:
    rounds, _ = analyse.load(out)
    n, share = len(config["concepts"]), config["settled"]["share"]
    items = []
    for c in range(n):
        primary = analyse.settled(rounds, c, config["settled"]["window"], share)
        secondary = analyse.settled(rounds, c, 50, share)
        if primary["form"]:
            items.append(("primary", c, primary["message"]))
        if secondary["form"] and secondary["form"] != primary["form"]:
            items.append(("secondary", c, secondary["message"]))
        if not primary["form"] and not secondary["form"]:
            items.append(("exploratory", c, commonest(rounds, c, 50)["message"]))
    return items


def commonest(rounds: list, concept: int, window: int) -> dict:
    """The commonest form of a concept's last `window` rounds, with its latest message,
    whatever its share."""
    return analyse.settled(rounds, concept, window, 0.0)


def handle_hearer(order: tuple, message: str):
    def handle(name, args):
        if name == "lookup":
            return tools.lookup(args["term"]), False, False, None
        if name == "read":
            return tools.read(args["message"], message), False, False, None
        if name == "choose" and args.get("concept") in prompt.LETTERS:
            return "", False, True, order[prompt.LETTERS.index(args["concept"])]
        return "Call `choose` with a letter from A to F.", True, False, None
    return handle


def _version_key(name: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", name))


def choose_openai(client) -> tuple:
    listing = sorted(m.id for m in client.models.list())
    flagship = [m for m in listing if re.fullmatch(r"gpt-\d+(\.\d+)?", m)]
    return max(flagship, key=_version_key), listing


def choose_gemini(client) -> tuple:
    listing = [(m.name, list(m.supported_actions or [])) for m in client.models.list()]
    names = [n.split("/", 1)[-1] for n, actions in listing if "generateContent" in actions]
    flagship = [n for n in names if re.fullmatch(r"gemini-\d+(\.\d+)?-pro", n)]
    return max(flagship, key=_version_key), [n for n, _ in listing]


def openai_hearer(client, model: str, system: str, text: str, handle, max_calls: int):
    spec = [{"type": "function", "function": {
        "name": t["name"], "description": t["description"],
        "parameters": t["input_schema"], "strict": True}} for t in tools.HEARER_TOOLS]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": text}]
    usage = []
    for n in range(1, max_calls + 1):
        r = client.chat.completions.create(model=model, messages=messages, tools=spec,
                                           max_completion_tokens=16000)
        usage.append(r.usage.model_dump(exclude_none=True) if r.usage else {})
        msg = r.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            messages.append({"role": "user", "content": "Call `choose` with the letter."})
            continue
        for call in msg.tool_calls:
            out, _, done, value = handle(call.function.name, json.loads(call.function.arguments))
            if done:
                return value, n, usage, r.model
            messages.append({"role": "tool", "tool_call_id": call.id, "content": out})
    return None, max_calls, usage, model


def gemini_hearer(client, model: str, system: str, text: str, handle, max_calls: int):
    from google.genai import types
    declarations = [types.FunctionDeclaration(name=t["name"], description=t["description"],
                                              parameters_json_schema=t["input_schema"])
                    for t in tools.HEARER_TOOLS]
    config = types.GenerateContentConfig(
        system_instruction=system, max_output_tokens=16000,
        tools=[types.Tool(function_declarations=declarations)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]
    usage = []
    for n in range(1, max_calls + 1):
        r = client.models.generate_content(model=model, contents=contents, config=config)
        usage.append(r.usage_metadata.model_dump(exclude_none=True) if r.usage_metadata
                     else {})
        contents.append(r.candidates[0].content)
        if not r.function_calls:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(
                text="Call `choose` with the letter.")]))
            continue
        parts = []
        for call in r.function_calls:
            out, _, done, value = handle(call.name, dict(call.args or {}))
            if done:
                return value, n, usage, model
            parts.append(types.Part.from_function_response(name=call.name,
                                                           response={"result": out}))
        contents.append(types.Content(role="tool", parts=parts))
    return None, max_calls, usage, model


async def haiku_hearer(game_client, meter, settings, text: str, handle, record):
    turn = agents.Turn(game_client, meter, settings, tools.HEARER_TOOLS, handle, record,
                       "Call `choose` with the letter of the concept.")
    result = await turn.run(text)
    return result.value, result.calls, result.cost, result.models


def main() -> int:
    parser = argparse.ArgumentParser(description="The decoding test of PLAN.md § 4.")
    parser.add_argument("--out", default=os.path.join(HERE, "transcripts"))
    parser.add_argument("--config", default=os.path.join(HERE, "config.json"))
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--max-spend", type=float, default=None,
                        help="stop before the measured spend on Anthropic's API, in dollars, "
                             "could pass this")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    for name in ("httpx", "httpx2", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    config = json.load(open(args.config, encoding="utf-8"))
    run.load_env(args.env_file)
    return asyncio.run(decode(args.out, config, args.max_spend))


async def decode(out: str, config: dict, max_spend: float | None = None) -> int:
    from google import genai
    import openai
    folder = os.path.join(out, "decoding")
    os.makedirs(folder, exist_ok=True)
    results_path = os.path.join(folder, "results.jsonl")
    done = set()
    if os.path.exists(results_path):
        done = {(r["hearer"], r["test"], r["concept"]) for r in map(json.loads, open(
            results_path, encoding="utf-8"))}
    oa, gm = openai.OpenAI(timeout=300, max_retries=4), genai.Client()
    (oa_model, oa_list), (gm_model, gm_list) = choose_openai(oa), choose_gemini(gm)
    json.dump({"openai": {"chosen": oa_model, "listing": oa_list},
               "gemini": {"chosen": gm_model, "listing": gm_list}},
              open(os.path.join(folder, "models.json"), "w"), indent=1)
    meter = agents.Meter(max_spend, run.spent_so_far(out), agents.Prices.of(config))
    system = prompt.system_prompt()
    settings = agents.Settings(config["model"], config["effort"], config["max_tokens"],
                               config["decoding"]["max_calls_per_form"], system,
                               config["attempts_on_model_refusal"])
    client, rng = agents.make_client(), random.Random(config["decoding"]["seed"])
    write = agents.jsonl(results_path)
    calls = agents.jsonl(os.path.join(folder, "calls.jsonl"))
    hearers = ["haiku-%d" % i for i in range(1, config["decoding"]["haiku_hearers"] + 1)]
    hearers += ["gemini", "openai"]
    for test, c, message in forms_to_decode(out, config):
        for hearer in hearers:
            order = tuple(rng.sample(range(6), 6))
            if (hearer, test, c) in done:
                continue
            text = prompt.fresh_hearer_task(message, [config["concepts"][i]["english"]
                                                      for i in order])
            handle, cost, usage = handle_hearer(order, message), 0.0, None
            if hearer.startswith("haiku"):
                value, n, cost, models = await haiku_hearer(
                    client, meter, settings, text, handle,
                    lambda e, h=hearer, k=c: calls(dict(e, hearer=h, concept=k)))
                model = models[-1] if models else config["model"]
            elif hearer == "gemini":
                value, n, usage, model = await asyncio.to_thread(
                    gemini_hearer, gm, gm_model, system, text, handle, 8)
            else:
                value, n, usage, model = await asyncio.to_thread(
                    openai_hearer, oa, oa_model, system, text, handle, 8)
            write({"test": test, "hearer": hearer, "model": model, "concept": c,
                   "concept_key": config["concepts"][c]["key"], "order": list(order),
                   "choice": value, "correct": value == c, "calls": n, "cost": cost,
                   "usage": usage, "message": message})
            log.info("%s %s %s: chose %s, %s", test, hearer, config["concepts"][c]["key"],
                     value, "correct" if value == c else "wrong")
    return 0


if __name__ == "__main__":
    sys.exit(main())
