# Rowih experiments

Experiments on [Rowih](https://github.com/rowih/rowih), a language for AI agents to communicate with one another, run on the language's released toolchain. Each experiment has a directory holding its plan, fixed before any run, the code that ran it, the system prompt its agents read, every call and round it made, its analysis and its report.

| Experiment | Question | Report |
|---|---|---|
| [Conventions](conventions/) | Do conventions emerge among agents that use Rowih, can agents outside the population read them, and which of the language's routes to a new word do they take? A naming game among ten agents, run on 2026-10-26. | [conventions/report.md](conventions/report.md) |

The experiments are run with the released packages and the files of a tagged release of the language's repository; each report names the release, the commit of the code that ran it, the models and their identifiers as the providers reported them, and the measured cost.

The code is licensed under Apache-2.0, and the plans, reports, prompts and transcripts under CC BY 4.0 ([licensing](LICENSING.md)).
