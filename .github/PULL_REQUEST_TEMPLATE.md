<!--
Thanks for the PR! A few quick guidelines before you submit:

1. Keep the PR focused — one logical change per PR.
2. CI must pass before review (lint, sanitize scan, docs build, CodeQL).
3. Sign-off is not required, but please ensure your commits follow Conventional Commits style:
     feat: ..., fix: ..., docs: ..., chore: ..., refactor: ..., test: ..., ci: ...
4. For UI changes, attach a before/after screenshot under "Screenshots".
5. For docs-only PRs, the title should start with `docs:` so reviewers know to skip code-review tooling.
-->

## What changed

<!-- 1-3 sentences. The diff already shows *what*; tell us *why*. -->

## Why

<!-- Link to a related issue/discussion. If none exists, describe the user-visible problem this solves. -->

Closes #

## Type of change

<!-- Check one. -->

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing deployments to fail without action)
- [ ] Documentation only
- [ ] CI / build / repo-hygiene

## How was this tested?

<!-- For code changes: describe the test setup. For UI changes: include screenshots. For docs changes: confirm `mkdocs build --strict` passes locally. -->

## Screenshots (if UI)

<!-- Drag images here; before/after preferred. -->

## Checklist

- [ ] My commit messages follow Conventional Commits style.
- [ ] I have added tests that prove my fix is effective or that my feature works (or explained why no test is needed).
- [ ] I have updated the docs (under `docs/`) for any user-visible change.
- [ ] I have updated `examples/` if I changed env-var names, defaults, or compose shape.
- [ ] I have NOT included secrets, API keys, or PII in this diff.
- [ ] If this is a security-sensitive change, I have flagged it for the maintainer in the PR description.
