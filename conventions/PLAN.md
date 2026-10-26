# Do conventions emerge in Rowih? Plan of the experiment

**Status:** designed and approved by the repository owner on 2026-10-26; not yet built or run. This file is the handoff: a session on the owner's machine builds and runs the experiment from it without repeating the research.
**Where it runs:** the owner's development machine, with the owner's API keys (owner's decision, 2026-10-26).
**Not part of any release:** `experiments/` is not among the directories `release/assemble.py` copies, so nothing here ships in the public repository until a later decision says how the results are published.

## 1. Why, and what it decides

The README states that use is untested: "The corpus was written by one designer, so whether conventions emerge in use, whether agents read new formations from their parts, and whether a model hearer recovers what a device of economy leaves out are unknown" (`README.md`, *What it does not do*). The owner aims at use among agents enough for conventions to emerge (2026-10-26), and asked whether the language will have a life of its own. This experiment is the first evidence on that question. It is an exploration, not a case for adoption: the owner decided on 2026-10-26 that the comparison of English and Rowih is not to be made, since operators adopt the language knowing the benefits and costs its page states.

Three questions, fixed before any run:

- **Q1, convergence.** Does a population of agents, interacting in pairs with no central coordination, settle on one Rowih form for each new concept?
- **Q2, transparency.** Can an agent that was never in the population recover the concept from a settled form, reading it through the toolchain?
- **Q3, route.** Which of the language's routes to a new word do the settled forms take, and do forms shorten with use?

## 2. What the language offers a speaker who lacks a word

The governance names three routes ([How Rowih changes](https://github.com/rowih/rowih/blob/main/governance/README.md#slang-and-new-words)): "Coinage is free, spread is in a community's hands, and standardisation is governed."

1. **A compound or a derivation** from the 119 productive patterns, which "any hearer reads from its parts" ([The lexicon](https://github.com/rowih/rowih/blob/main/specification/lexicon.md#word-formation), [the productive patterns](https://github.com/rowih/rowih/blob/main/specification/lexicon.md#the-productive-patterns)).
2. **A definition**, made by the act of definition, scoped to the exchange or to a dialect ([The lexicon](https://github.com/rowih/rowih/blob/main/specification/lexicon.md#coining-a-word-by-definition); [The record and discourse](https://github.com/rowih/rowih/blob/main/specification/discourse.md#definitions)). A definition holds within its exchange, so a defined form can spread across pairs only if each speaker defines it again with each new partner. Whether agents do so is itself a finding.
3. **A proposal** to a dialect or the shared lexicon. This route is outside the experiment.

## 3. The method it follows

The naming game, as Ashery, Aiello and Baronchelli applied it to populations of language-model agents: A. F. Ashery, L. M. Aiello and A. Baronchelli, "Emergent social conventions and collective bias in LLM populations", *Science Advances* 11(20), eadu9368, 2025 (DOI 10.1126/sciadv.adu9368; preprint arXiv:2410.08948). Read on 2026-10-26 at abstract and summary level: the paper reports that conventions emerge spontaneously in decentralised populations of LLM agents, that collective biases arise even from agents without individual bias, and that committed minorities can overturn a convention. The design below borrows the game's structure: pairwise interaction, local memory, success feedback and no global coordination. It does not borrow the paper's population sizes or memory lengths, which were not read, and should not claim to replicate the paper.

## 4. The design

**Population.** Ten agents, each an instance of `claude-haiku-5-5`, each with:

- the skill `skill/rowih/SKILL.md` as part of its system prompt, with the grammar summary that `rowih summary grammar` prints;
- three tools over the Python package, called in process: **look up** (`rowih.api.lookup`), **write** (`rowih.api.write`, which writes a message from the notation under an envelope and returns it with the diagnostics of reading it back), and **read** (`rowih.api.parse`, `rowih.api.translate` and `rowih.api.gloss`);
- a private memory of its last ten rounds: the concept or the candidates, the message sent or received, and whether the round succeeded.

**Concepts.** Six concepts of the agents' own world that the lexicon has no word for. The building session proposes candidates, and each is kept only if `rowih lookup` finds no entry whose definition states it. Among the candidates to try: an instruction hidden inside retrieved text; a cached result that no longer holds; a task delegated onward a second time; an agent's fork that has diverged from it; a tool that answers without having run; a commitment kept only in part. The six chosen, and the lookups that cleared them, are written to `config.json` before the pilot.

**A round.**

1. Two distinct agents are drawn at random, one as speaker and one as hearer.
2. The speaker is shown one concept, in English, privately, and must refer to it in a single Rowih message that passes `rowih validate`. It may use any route of § 2.
3. The message is refused, and the speaker asked again at most twice, if it draws a diagnostic or if any quoted, reported or declared material in it carries text other than Rowih words. Inert material is the language's back door for English, and the game closes it. A third refusal fails the round.
4. The hearer receives the message, may read it with its tools, and chooses one of the six concepts, shown to it in English in a shuffled order.
5. Both agents are told the outcome, and the hearer is told the intended concept, as the naming game's feedback.
6. Each agent appends the round to its memory and drops the oldest past ten.

**The decoding test, after the run.** For each concept, its **settled form** is the commonest form among the last 200 rounds in which it was the concept, provided that form has a share of at least 0.5; a concept with no such form has no settled form, and that is reported. Each settled form is shown, with the toolchain's tools, to fresh hearers that were never in the population: three new `claude-haiku-5-5` agents, one Gemini model and one OpenAI model. Each chooses among the six concepts, so chance is 1 in 6. The Gemini and OpenAI model identifiers are taken at run time from each provider's own model listing; none is assumed here.

**Length.** The pilot runs 50 rounds, to measure real cost per round and to check the harness. The main run continues to 1,200 rounds.

## 5. Measures, fixed before any run

1. **Success**: the share of successful rounds in each successive block of 100 rounds.
2. **Convergence**: for each concept, the number of distinct forms in use, and the share of its commonest form, in each block of 200 rounds.
3. **Route**: each form classified from its parse as a definition, a compound or derivation from the productive patterns, an existing word or idiom of the lexicon, or other; the share of each route among all forms and among the settled forms.
4. **Length**: the mean number of words a reference takes, excluding the envelope, in each block of 100 rounds.
5. **Transparency**: each fresh hearer's accuracy on the settled forms, against chance at 1 in 6.
6. **Refusals**: the rate of messages refused, by reason.

A *form* is the move's normal form as the toolchain writes it, so that two surfaces of one meaning count as one form. The analysis script is written and committed before the pilot runs. Any change to it afterwards is recorded with its reason and the date.

## 6. Cost

List prices at 2026-10-26 for `claude-haiku-5-5` are $0.10 per million input tokens and $0.50 per million output tokens; cache reads cost about a tenth of input, and cache writes about 1.25 times input. Check them against Anthropic's pricing page before the pilot. The system prompt, with the skill and the grammar summary, is the same for every call, so it is cached.

Estimated cost is about $0.006 a round: six calls of about 15,000 cached and 1,000 fresh input tokens and 1,500 output tokens each. Then 1,200 rounds come to about $8. This is an estimate, not a measurement; the pilot measures it.

## 7. Building it

- **Location:** `experiments/conventions/`: `run.py` (the harness), `analyse.py` (the measures of § 5), `config.json` (concepts, seeds, models), `transcripts/` (one JSON line per call and per round, with the usage it reported), and `report.md` (the results).
- **Dependencies:** a dependency group `experiments` in `pyproject.toml`, holding the Anthropic, Google Gen AI and OpenAI SDKs pinned to exact versions, installed with `uv sync --group experiments`. The package `rowih` keeps no dependency at run time. Any SDK version with a known advisory is refused, by the PyPI advisory check used for 1.1.2 or by `uv audit` where it can reach its database.
- **Keys:** read from the owner's environment as `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` and `OPENAI_API_KEY`. No key is written to any file, transcript or commit.
- **Reproducibility:** every random choice (pairs, concepts, candidate order) comes from one seed in `config.json`. Each call's model identifier, as the response reports it, is recorded.
- **A single round is the demo.** `run.py --rounds 1` plays one round end to end and prints both messages, their glosses and their English explanations. It serves as the two-agent demonstration that operators can run.
- **Commits:** as William Short with no co-author trailers, as `PROGRESS.md` records. The experiment is recorded in `PROGRESS.md`, not in the changelog, since it makes no release.

## 8. Order of work on the owner's machine

1. Pull `ccr-04c16bfa-ks9gzi` of this repository, or `master` once pull request 1 is merged.
2. Pull request 1, release 1.1.2: run the suite, `uv run pytest`, over the branch's head before merging. The suite run in the cloud session had passed 79% with no failure when the session ended.
3. Choose the six concepts by lookup, and write `config.json`, `run.py` and `analyse.py`.
4. Commit the plan of analysis and the configuration before any run.
5. Run the pilot of 50 rounds. Report its measured cost per round to the owner, and stop if the estimate of § 6 is off by more than half.
6. Run the main game to 1,200 rounds.
7. Run the decoding test with the three fresh Haiku hearers, one Gemini model and one OpenAI model.
8. Write `report.md`, with every measure of § 5, and record the experiment in `PROGRESS.md`.

## 9. What would count as each answer

These rules are fixed here, before any run.

- **Q1** is answered yes for a concept that has a settled form by § 4's rule, and no for one that does not. The overall answer is the count of the six that settle.
- **Q2** is answered by each fresh hearer's accuracy on the settled forms, reported per hearer and per form against chance; no threshold is set.
- **Q3** is answered by the shares of § 5, measure 3, and the trend of measure 4.

The report states the experiment's limits:
- one designer's corpus taught the agents;
- the population is of one model;
- the concepts were chosen by the experimenter;
- the feedback names the intended concept, which a real exchange need not do.
