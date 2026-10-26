# Do conventions emerge in Rowih? Report of the experiment

**Run:** 2026-10-26. **Language:** Rowih 1.0, lexicon 1.0, toolchain 1.1.2 (the files and code of the public repository at `v1.1.2`). **Population:** ten instances of `claude-haiku-5-5`. **Plan:** [PLAN.md](PLAN.md), fixed and approved before any run. **Cost:** $5.34 on Anthropic's API.

## What was found

The plan fixed three questions and the rules that answer them before any run (PLAN.md § 9).

- **Q1, convergence.** By the plan's rule, one concept of six has a settled form: *riyobudim*, 'one that has descended (as a fork)', for an agent's fork that has diverged from it, the commonest form in 71% of the last 200 rounds of that concept. The other five never reach a share of one half. The population did converge, however, at another level: by the last 200 rounds 99% of all messages used one frame, an assertion, by introspection and with certainty, that a single coined word is true, and only the word varied with the concept. That observation was not planned, and is reported as exploratory.
- **Q2, transparency.** Each of five hearers that were never in the population, three new instances of Haiku 5.5, `gpt-5.5` and `gemini-2.5-pro`, chose the right concept for the one settled form, where chance is 1 in 6. In an exploratory test added after the run, the same hearers chose the right concept for the commonest recent form of each of the other five concepts, 25 times in 25. They read each message through the toolchain, whose morpheme gloss names the parts of a coined word in English.
- **Q3, route.** Agents coined words from the lexicon's productive patterns: 80% of messages referred by a compound or a derivation, 20% by existing words, and none by definition, which the game's rules left open only in a limited form (§ *What the language's rules allowed*). Messages shortened from a mean of 24.4 words in the first 100 rounds to 18.0 or 18.1 from round 801 onwards, without the envelope.

Success stood at 97% to 100% in every block of 100 rounds from the first. The task was therefore easy from the start, and the failure feedback that drives a naming game seldom came into play; that is the experiment's chief limit, and it bears on every answer above.

## What was run

### The game

The design is the naming game of Ashery, Aiello and Baronchelli, "Emergent social conventions and collective bias in LLM populations", *Science Advances* 11(20), eadu9368, 2025, borrowed in its structure only: pairwise interaction, local memory, success feedback and no global coordination (PLAN.md § 3). It does not replicate the paper.

- **Population.** Ten agents, each an instance of `claude-haiku-5-5` at effort `medium`, every response reporting that model.
- **What each agent read.** One system prompt, the same bytes for every call ([system-prompt.txt](system-prompt.txt), 45,484 tokens): the rules of the game, the skill `skill/rowih/SKILL.md` with its three references (the grammar summary, the notation and the lexicon listing), and the specification's rules of word formation and of coining a word by definition.
- **Tools.** Five, in process over the Python package `rowih`: `lookup` (`rowih.api.lookup`, without the dialects' terms), `write` (writes a message from the notation under the round's envelope and reads it back), `read` (the toolchain's gloss and English explanation), `send` for the speaker and `choose` for the hearer.
- **Memory.** Each agent's last ten rounds: the concept, the message sent or received with its literal semantic form, the choice and the outcome.
- **Concepts.** Six concepts of the agents' own world, each kept only because no entry of lexicon 1.0 states it ([config.json](config.json), `concept_clearance`, with the nearest entries found): an instruction hidden inside retrieved text; a cached result that no longer holds; a task delegated onward a second time; an agent's fork that has diverged from it; a tool that answers without having run; a commitment kept only in part.
- **A round.** Two agents are drawn at random. The speaker is shown one concept in English and sends one Rowih message, which the game refuses if reading it draws a diagnostic or if quoted, example or declared material in it holds anything but Rowih words; a third refusal loses the round. The hearer reads the message and chooses among the six concepts, shown in English in a shuffled order. Both remember the outcome, and the hearer the intended concept.
- **Length.** A pilot of 50 rounds, then the main run to 1,200 rounds. Every random choice came from the seed 20261026.

The harness played rounds whose agents differ at the same time, and each agent's rounds in order, so that every agent met the same rounds, and held the same memory, as in a run one round at a time.

### The decoding test

For each concept with a settled form, the latest message in that form was shown, with the tools `read` and `lookup` and the same system prompt, to five hearers that were never in the population: three new instances of `claude-haiku-5-5`, one OpenAI model and one Gemini model. Each chose among the six concepts, in an order drawn from the seed 20261027. The OpenAI and Gemini models were taken at run time from each provider's own listing, by a rule fixed before any run: the newest generally available model of the flagship line, excluding previews. The rule gave `gpt-5.5` (reported as `gpt-5.5-2026-04-23`) and `gemini-2.5-pro`; Gemini 3.1 Pro was listed only as a preview ([models.json](transcripts/decoding/models.json)).

## Results

Every measure of PLAN.md § 5 follows. The measures and the rules that answer the questions were fixed in [analyse.py](analyse.py) and committed before the pilot; the one change to it since is recorded under *Departures from the plan*.

### 1. Success

| Rounds | Played | Success |
|---|---|---|
| 1–100 | 100 | 99% |
| 101–200 | 100 | 100% |
| 201–300 | 100 | 99% |
| 301–400 | 100 | 100% |
| 401–500 | 100 | 100% |
| 501–600 | 100 | 100% |
| 601–700 | 100 | 100% |
| 701–800 | 100 | 100% |
| 801–900 | 100 | 99% |
| 901–1000 | 100 | 99% |
| 1001–1100 | 100 | 99% |
| 1101–1200 | 100 | 97% |

Of the eight failures, one was a round whose speaker sent nothing, and five of the seven others fell late in the run on the tool that answers without having run, for which three coined words were then competing.

### 2. Convergence

For each concept, the number of distinct forms in use and the share of its commonest form, in each block of 200 rounds. A form is the sequence of a message's moves' normal forms, as the toolchain's printer writes them.

| Rounds | Hidden instruction | Stale cache | Re-delegation | Diverged fork | Tool that did not run | Commitment in part |
|---|---|---|---|---|---|---|
| 1–200 | 9 / 30% | 9 / 30% | 9 / 56% | 11 / 25% | 10 / 45% | 9 / 27% |
| 201–400 | 7 / 69% | 10 / 50% | 6 / 42% | 5 / 62% | 5 / 58% | 10 / 26% |
| 401–600 | 6 / 50% | 6 / 49% | 8 / 38% | 4 / 82% | 5 / 37% | 6 / 54% |
| 601–800 | 6 / 57% | 7 / 37% | 4 / 42% | 2 / 94% | 5 / 54% | 8 / 37% |
| 801–1000 | 9 / 25% | 7 / 38% | 6 / 46% | 2 / 88% | 5 / 32% | 7 / 40% |
| 1001–1200 | 6 / 52% | 5 / 63% | 8 / 23% | 6 / 76% | 6 / 43% | 3 / 48% |

**The settled forms (Q1).** A concept's settled form is the commonest form among the last 200 rounds in which it was the concept, provided its share is at least one half (PLAN.md § 4).

| Concept | Rounds in the window | Share of the commonest form | Settled |
|---|---|---|---|
| Hidden instruction | 197 | 24% | no |
| Stale cache | 200 | 26% | no |
| Re-delegation | 188 | 21% | no |
| Diverged fork | 187 | 71% | yes: *riyobudim* |
| Tool that did not run | 200 | 20% | no |
| Commitment in part | 200 | 18% | no |

Each concept was drawn in about 200 of the 1,200 rounds, so its window of 200 rounds covers nearly every round in which it was the concept, early variety included; analyse.py said so before any run, and declared a secondary measure over each concept's last 50 rounds. By that measure too only the diverged fork settles, at 82%; the shares of the other five lie between 30% and 46%. The secondary measure of convergence over content words alone, without the grammatical frame, gives the same figures as the table above from round 801 onwards, and nearly the same from round 401, since by then nearly every message shared one frame.

**The frame (exploratory).** The block tables do not show what the population did agree on. From round 4, when agent 7 first used it, one frame spread through the population: a single move asserting, by introspection and with certainty, that a coined word is true, `(move ASSERTED-POSITION (assertion INTROSPECTION CERTAIN (situation true (UNDERGOER (term (unknown "WORD") DEFINITE)))))`. Its share of messages was 9% in rounds 1–200, 38% in 201–400, 81% in 401–600, 86% in 601–800, 98% in 801–1000 and 99% in 1001–1200. Within it the coined words went on competing. This measure was defined after the run, on reading the forms, and answers no question of the plan.

The commonest words of the last 200 rounds, with their parts as the toolchain divides them:

| Concept | Word | Its parts | Share of the concept's messages in rounds 1001–1200 |
|---|---|---|---|
| Hidden instruction | *nulomiminuyelaminuditum* | rule + inside + text | 14 of 27 |
| Stale cache | *runayinuyuyulaniw* | record + true + not | 22 of 35 |
| Re-delegation | *robetuleginuwenut* | give + again + work | 5 of 22 |
| Diverged fork | *riyobudim* | descend (as a fork) + the one undergoing | 28 of 37 |
| Tool that did not run | *nunopipinukogemawenirudinaniw* | machine + speak + instrument + run + not | 20 of 46 |
| Commitment in part | *robahinuwenut* | part + work | 16 of 33 |

The tool that answers without having run had two other words in use at the end, *nunopipinunigag*, machine + dream (12 of 46), and *sayoirudinaniw*, tool + run + not (10 of 46).

### 3. Route

Each form classified from its normal forms.

| Route | Messages | Distinct forms | Settled forms |
|---|---|---|---|
| A definition | 0% | 0% | 0% |
| A compound or a derivation | 80% | 72% | 100% (one form) |
| An existing word or idiom | 20% | 28% | 0% |
| Other | 0% | 0% | 0% |

### 4. Length

The mean number of words of a message's moves, without the envelope: 24.4 in rounds 1–100, 26.2 in 101–200, 22.2, 20.1, 18.9, 18.9, 19.0 and 19.7 in the next six blocks, and 18.1, 18.0, 18.0 and 18.0 in the last four. The shared frame with one coined word is 18 words long, and the plateau is that frame.

### 5. Transparency (Q2)

| Hearer | Model | Settled forms | Correct | Chance alone would do as well |
|---|---|---|---|---|
| haiku-1 | `claude-haiku-5-5` | 1 | 1 | 1 time in 6 |
| haiku-2 | `claude-haiku-5-5` | 1 | 1 | 1 time in 6 |
| haiku-3 | `claude-haiku-5-5` | 1 | 1 | 1 time in 6 |
| openai | `gpt-5.5-2026-04-23` | 1 | 1 | 1 time in 6 |
| gemini | `gemini-2.5-pro` | 1 | 1 | 1 time in 6 |

**Exploratory.** Since one form settled, the plan's test says little about whether a hearer outside the population reads the coined words. After the main run and before any decoding, a test was added and committed: for each concept with no settled form, the commonest form of its last 50 rounds, shown to the same five hearers. Each hearer chose correctly 5 times in 5, which chance alone would do about once in 7,800. It answers no question of the plan.

Each hearer read the message through the toolchain, and that is what the result measures. For *riyobudim* the morpheme gloss reads `DESCEND-UNDERGOER`, and the lexicon listing in the prompt defines *descend* as "share another agent's lineage, as a fork of it or another instance of its model". A hearer that recovers 'an agent's fork that has diverged from it' from that, among six candidates given in English, has read a coined word from its parts through the toolchain; it has not read the bare form, and it has not had to name the concept unprompted.

### 6. Refusals

Of 1,212 attempts to send, the game refused 13 (1.1%): 12 because the notation could not be written and one because the message drew `d.lexer.unknown-word`. One round, the sixteenth, was lost when its speaker sent nothing within twelve calls. No message was refused for inert material.

## What the language's rules allowed

A definition gives a word its meaning in later messages of an exchange only, and the plan required every message to pass validation on its own. A word defined and used in one message, or used in a later one, therefore draws `d.lexer.unknown-word`. Within this game the definition route could appear only as a message whose definition itself referred to the concept; the agents were told so, and none took it. Whether agents define words where definitions persist across the messages of an exchange is untested.

## Faults found in the toolchain

- **A slotted idiom raises an uncaught error.** Writing an idiom that takes a slot without its slot, such as `(idiom river-forking)`, makes `rowih.api.write` raise a bare `ValueError: slot` from `python/rowih/tree.py`, where it should refuse the notation with the toolchain's own input error. The agents reached for such idioms 39 times, *river-forking* 37 times for the diverged fork and *undertaking-broken* twice. The first occurrence stopped the pilot after 25 rounds; from then on the harness reported the error to the agent as a failed tool call and logged it. It is recorded for a later release of the toolchain.
- **The safety classifier declined four calls.** Haiku 5.5's classifier declined four calls of the game with the category `bio`, a false positive on a game about service status and agents' words; the harness made each declined call again, up to three attempts, and every one then went through. The first such decline was found in a development round, before the pilot.

## Departures from the plan

Each of the first four was recorded in the repository before the step it affected, with its date and reason; the fifth and sixth concern how the code is packaged and shown, not what it measured.

1. **The agents read the skill's references and the specification's rules of formation and definition** as well as the skill and the grammar summary (config.json, `prompt`, 2026-10-26, before any run). An agent with the skill installed can read its references, and these agents had no tool that reads files; without the lexicon listing an agent cannot know which roots exist, and without the rules of formation it cannot take the route of compounds and derivations.
2. **A declined call is made again** (config.json, `attempts_on_model_refusal`, after the first development round and before the pilot), for the reason above.
3. **A fault of the toolchain is reported to the agent** rather than stopping the run (after the pilot stopped after 25 rounds). The one round the stop cut short, round 27, was played again from the start, and the calls it had made stay in the transcripts and the spend; the commit that made the change named rounds 26 to 30, of which only round 27 had begun. analyse.py was changed on the same date to count those faults apart from the calls in its summary of spend; no measure of PLAN.md § 5 changed.
4. **The exploratory decoding test** was added after the main run and before any decoding, for the reason given under measure 5.
5. **The packages the harness uses** are pinned in `requirements.txt`, not in a dependency group of the language's `pyproject.toml` as PLAN.md § 7 had them: the owner decided after the run that the experiments are published in a repository of their own and not in the language's, whose `pyproject.toml` and `uv.lock` ship with each release. The versions are those the run used, `anthropic` 1.17.0, `google-genai` 2.33.0 and `openai` 3.37.0, in which `uv audit` found no advisory on 2026-10-26.
6. **The two-agent demonstration** is `run.py --rounds 1 --out DIR`, which plays a single round into its own directory and prints it, so that a demonstration does not add to the experiment's transcripts; four such development rounds are kept in `transcripts/development/`, counted in the spend and left out of every measure.

## Cost

The plan estimated $0.006 a round from list prices (PLAN.md § 6). The pilot measured $0.0057 a round over its 50 rounds, and the main run $0.0043, as cache reads came to dominate: over the game's 5,752 calls, 273 million input tokens were read from the cache, 10.5 million written to it, 16,306 sent uncached, and 2.4 million produced. The game cost $5.26, the development rounds and their replays $0.05, and the three Haiku hearers of the decoding test $0.03: $5.34 in all. The OpenAI and Gemini hearers used about 462,000 and 683,000 input tokens and 3,900 and 12,400 output tokens, paid from the owner's credits with each provider.

## Limits

The plan names four, and the run adds five.

- One designer's corpus taught the agents, through the skill and the lexicon.
- The population is of one model.
- The concepts were chosen by the experimenter.
- The feedback names the intended concept, which a real exchange need not do.
- **The task was too easy to press for convergence.** A hearer chose among six concepts shown in English, and almost any honest description in Rowih picked out the right one; success was 99% in the first block. A naming game converges because failures make agents align, and here failures were too few to do that work. A harder game, with more concepts, near neighbours among them, or no list of candidates, would test convergence more severely.
- **The plan's window for a settled form** covered nearly every round of a concept at this length, and so counted early variety against convergence.
- **The decoding test read through the toolchain**, whose morpheme gloss names a coined word's parts in English, with the lexicon listing in the prompt and six candidates to choose among.
- **One run, from one seed**, with no replication.
- **The frame and the words were agreed by a population of identical models** with the same prompt, which may share a preference for a construction before any interaction; the frame's spread from one agent's use is consistent with that and does not establish imitation.

## Data and reproduction

- [PLAN.md](PLAN.md): the plan, fixed before any run. Its links point to the public repository of the language, and lines on the project's own administration are left out; its questions, design, measures and rules of answer are as approved.
- [config.json](config.json): the seed, the model, the prices as checked, the concepts and the lookups that cleared them, and the departures recorded before any run.
- [system-prompt.txt](system-prompt.txt): the system prompt every agent and every Haiku hearer read.
- `run.py`, `agents.py`, `tools.py` and `prompt.py`: the game. `analyse.py`: the measures. `decode.py`: the decoding test. `test_conventions.py`: their tests.
- `transcripts/rounds.jsonl.gz`: one line per round. `transcripts/calls.jsonl.gz`: one line per call, with the usage the response reported and its price; thinking blocks are kept without their signatures. `transcripts/decoding/`: the decoding test's results, calls and the model listings. `transcripts/development/`: the development rounds. `transcripts/analysis.json`: every measure as analyse.py computed it.

The code ran from `experiments/conventions/` of the language's development repository, whose files outside that directory are those of the public repository at `v1.1.2`; the system prompt built from the public tree at `v1.1.2` is byte for byte the one the agents read (SHA-256 `4ca0ea7bb69c24d2142aa7c4865ddfb1099f15ec4c6aadf4b4662633328c74da`). To run it again, place this directory at `experiments/conventions/` in a checkout of [rowih/rowih](https://github.com/rowih/rowih) at `v1.1.2`, install the packages of `requirements.txt`, and give the keys as `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` and `OPENAI_API_KEY`. Rounds 1 to 25 ran on the harness of commit `3dbf622`, rounds 26 to 1,200 on that of `d75f71c`, which adds the change of departure 3, and the decoding test on that of `a8950e2`, which adds that of departure 4. The commits are those of the language's development repository, rebased after the run onto release 1.1.2 without changing the harness or any source the prompt or the package is built from; before the rebase they were `785e665`, `ef38d8d` and `62d75ef`. The code here is that of `a8950e2`, with the reading of compressed transcripts added to analyse.py, the instructions at the head of each file pointing at `requirements.txt`, and the meter's limit on spending given by the option `--max-spend` of `run.py` and `decode.py`, which has no default.
