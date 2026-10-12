# Repository Guidelines

## Project Structure & Module Organization

This Python lab evaluates RAG answers, LLM judges, and input/output guardrails. Implement phase logic in `src/phase_a_ragas.py`, `phase_b_judge.py`, and `phase_c_guard.py`; reuse the runners, support utilities, and report contracts in `src/`. CLI entry points live in `scripts/`; tests live in `tests/`.

Keep supplied datasets in `fixtures/` and RAG source documents in `data/`. Save generated JSON evidence under `artifacts/`, Markdown reports under `doc/reports/`, and individual contributions in `doc/TEAM.md`. Guard configuration belongs in `guardrails/`; Docker Compose configuration lives in `infra/`.

## Build, Test, and Development Commands

Run commands from the repository root using Python 3.11 and a virtual environment.

- `python -m pip install -r requirements/requirements-test.lock.txt` installs offline test dependencies.
- `python -m pytest tests/ -q` runs the default offline suite.
- `python -m pytest tests/ -m support -q` checks supplied scaffold behavior.
- `python scripts/setup_answers.py --live` generates the 50-answer dataset.
- `python scripts/run_experiments.py --phase a --live` runs Phase A; use `--phase b` or `--phase c --latency-samples 20` for the other phases.
- `python scripts/check_lab.py --with-tests` validates submission evidence and runs unit tests.

Follow `doc/ENVIRONMENT.md` for full runtime dependencies, models, and Qdrant setup. Live commands use network services and may incur API charges.

## Coding Style & Naming Conventions

Use four-space indentation, snake_case functions and modules, PascalCase dataclasses, and uppercase configuration constants. Preserve existing type annotations, function interfaces, and JSON schemas. Follow surrounding code; no dedicated formatter or linter configuration is supplied.

## Testing Guidelines

Use pytest with `test_*.py` files and `test_*` functions. Mock external SDKs in offline tests. Mark tests as `student`, `support`, or `integration`. Live integration requires `python -m pytest -m integration --run-live`. No numerical coverage threshold is configured; test changed behavior and edge cases. Unimplemented starter TODOs intentionally fail student tests.

## Commit & Pull Request Guidelines

History uses `Update`/`update` and establishes no detailed convention. Prefer concise, descriptive imperative messages. PRs should explain the affected phase, behavior changes, validation commands and results, and related issues when applicable. Keep reports consistent with generated evidence.

## Security & Evaluation Integrity

Keep secrets in ignored `.env` files. Inspect required artifact JSON before committing for API keys and personal data. Never substitute ground truth for generated answers or expose human labels to the judge.
