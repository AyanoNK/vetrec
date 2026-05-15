# Project conventions

These rules apply to all work in this repository. They sit on top of any global
rules already in place.

## Commit messages

- Start with a **lowercase** letter (`add gitignore`, not `Add gitignore`).
- **Present-tense imperative** (`add`, `fix`, `update` — never `added` or `adding`).
- Concise and direct. Keep the subject under ~50 characters.
- One logical change per commit. Split unrelated work into separate commits.
- No trailing period on the subject line.
- No AI attribution. No `Co-Authored-By: Claude` trailers.

Examples:

```
add gitignore
add fastapi extract endpoint
fix vitals parsing for missing temperature
```

## Python tooling

- Use `uv` for everything Python-related.
  - `uv sync` to install, `uv add <pkg>` to add a dep, `uv run <cmd>` to execute.
  - `pyproject.toml` declares deps; `uv.lock` is committed.
- No `requirements.txt`, no `pip install`, no Poetry, no Pipenv.

## Branches and pushes

- Do not push without explicit instruction.
- Do not force-push to `main`.
