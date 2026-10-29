# Contributing

Use https://github.com/kpto1/TraceLoopCI/issues for bugs and proposed changes.

Install the hashed development dependencies and editable server/plugin following README. Run:

```bash
ruff check app tests sdk/python migrations examples
python -m pytest tests sdk/python/tests
cd frontend && pnpm install --frozen-lockfile && pnpm test && pnpm build
```

CI additionally runs PostgreSQL migrations, a real Redis round trip, SDK tests and Compose smoke checks. Keep production errors separate from model-quality failures. Include a regression test for each behavior fix. Never commit databases, .env files or private evaluation reports.

Update both universal Python locks after dependency changes. Run `ruff format` on changed Python files. Changes to dataset rules require baseline review. Describe actual verified behavior and any untested deployment assumptions in PRs.
