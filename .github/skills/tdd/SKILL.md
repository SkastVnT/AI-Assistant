---
name: tdd
description: Test-driven development with red-green-refactor loop. Use when building a new feature or fixing a bug with TDD, or when asked for test-first development.
---

# TDD — Test-Driven Development

Vertical slices via tracer bullets. One test → one implementation → repeat.

## Philosophy

Tests verify **behavior through public interfaces**, not implementation details.

- Good: exercises a real code path through a public API — "user can send message, gets SSE stream back"
- Bad: mocks internal collaborators, tests private methods, checks DB state directly

If renaming an internal function breaks your test, the test was testing implementation, not behavior.

## Anti-pattern: Horizontal Slices

**Do NOT** write all tests first, then all code.

```
WRONG:  RED: test1, test2, test3, test4  →  GREEN: impl1, impl2, impl3, impl4

RIGHT:  RED→GREEN: test1→impl1
        RED→GREEN: test2→impl2
        RED→GREEN: test3→impl3
```

## Workflow

### 1. Plan — before any code

- [ ] Confirm which behaviors to test (prioritise critical paths)
- [ ] Identify the correct test seam (unit vs integration vs SSE endpoint)
- [ ] Design public interface first — what will callers see?
- [ ] List behaviors to test (not implementation steps)
- [ ] Get user approval

For chatbot tasks — seam selection guide:
| What to test | Correct seam |
|---|---|
| Tool function | `core/tools.py` function directly |
| Route returns right JSON | `pytest` with Flask test client |
| SSE stream fields | `routes/stream.py` integration test |
| Provider routing | `core/chatbot.py` or `chatbot_v2.py` unit test |
| DB read/write | `database/repositories/` with test DB |

Run existing tests first: `cd services/chatbot && pytest tests/ -v`

### 2. Tracer Bullet

Write ONE test confirming ONE behavior:
```
RED:   Write test for first behavior → fails
GREEN: Write minimal code to pass → passes
```

### 3. Incremental Loop

For each remaining behavior:
```
RED:   Write next test → fails
GREEN: Minimal code to pass → passes
```

Rules:
- One test at a time
- Only enough code to pass current test
- Don't anticipate future tests
- Tests must be runnable: `pytest tests/<file> -v`

### 4. Refactor

Only after ALL tests pass:
- [ ] Extract duplication
- [ ] Simplify over-engineered paths
- [ ] Run tests after each refactor step

**Never refactor while RED.**

## Checklist per cycle

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
[ ] Tests pass: pytest tests/ -v
```
