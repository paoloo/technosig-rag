# Contributing

Thank you for considering a contribution. Improvements to retrieval quality, corpus coverage, reproducibility, documentation, and deployment are all welcome.

## Before making a change

For a bug fix or a small documentation improvement, feel free to open a pull request directly. For a larger change, open an issue first so the approach and its effect on the corpus can be discussed before substantial work begins.

Never commit ADS tokens, downloaded papers, model caches, databases, or other local research data. The repository intentionally keeps those artifacts outside Git.

## Set up a development environment

Fork and clone the repository, then create an isolated Python environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add an ADS token to your local `.env` only when testing corpus acquisition. Most unit tests do not need credentials, network access, a GPU, or a running inference server.

## Make the change easy to review

- Keep each commit focused on one understandable change.
- Use plain-English commit messages that explain what the change accomplishes.
- Add or update tests whenever behavior changes.
- Update the README when commands, models, resource needs, or deployment details change.
- Preserve stable identifiers and citation metadata when changing parsing or chunking.

Run the unit suite before submitting a pull request:

```bash
pytest tests/unit -q
```

Changes that affect a deployed MCP service should also pass the smoke test described in the README. If a test needs private infrastructure or a large local corpus, explain how you validated it in the pull request instead of adding those artifacts to Git.

## Pull requests

Describe the problem, the chosen approach, and any tradeoffs. Include before-and-after measurements for retrieval, reranking, or performance changes when possible. By contributing, you agree that your work may be distributed under this project's MIT license.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md) in all project spaces. Security-sensitive findings should be reported privately as described in [SECURITY.md](SECURITY.md).
