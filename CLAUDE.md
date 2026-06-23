# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**IMPORTANT:** Whenever possible, keep responses to the user under 150 words.

## Purpose

A learning project for **dbt Core + DuckDB**. The domain (stylometric "fingerprints" of authors vs the user's own prose) is the vehicle; the goal is mastering the analytics-engineering stack.

## Implementation doc

`docs/dbt-Project.md` is the working plan. Treat it as a **rough, LLM-written draft**: many specifics are likely wrong, and most of it can and will change as we build. Consult it for direction, not as ground truth.

## How we work

- **Propose, then WAIT for an explicit go-ahead. Do NOT implement in the same turn you explain.** This is the #1 rule. When the user asks "what's next?", a question, or anything ambiguous, the answer is words only — explanation/options, zero file writes or commands. Only run a tool that changes things after the user clearly says go (e.g. "do it", "go ahead", "yes"). When unsure whether you have the green light, you don't — ask.
- The user is here to learn; **you write most of the code**, but you are also **the documentation**. Before writing anything, explain what we're about to do and why, step by step, so the user never has to leave the editor to understand it.
- **One step at a time.** Once approved, do exactly ONE discrete action (one command or one file), then STOP and wait for the user again. Never chain steps or implement a whole phase ahead, even when the plan lists several bullets together. Approval for one step is NOT approval for the next.
- At any **design or tech choice, stop and lay out the options, then consult the user.** Don't pick silently.
- **Never rely on memory for code/tech specs.** Check the local refs in `docs/reference/` first (`dbt-core.md`, `dbt-duckdb.md`, `duckdb.md`). If they don't cover it, fetch current docs (Context7 / official sources), then update the ref file. Keep these refs current.
- **Be lean.** Fewest words possible in chat and in prose docs. No extended justification, no restating known facts, no exhaustive examples.
- **Never stage or commit.** Don't run `git add`/`git commit` unless explicitly instructed; the user handles version control.

## Environment

- Windows 11, bash terminal, VS Code. Python 3.14 and `uv` are installed.
- Before suggesting any `uv` command, explain how it differs from plain `python`/`pip`.

---

**REMINDER:** Whenever possible, keep responses to the user under 150 words.
