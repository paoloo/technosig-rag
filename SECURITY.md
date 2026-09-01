# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Email `paolocmo@gmail.com` with a description of the problem, the affected component, reproduction steps, and any known impact. You should receive an acknowledgement within seven days.

Avoid including ADS tokens, institutional credentials, private corpus content, or other secrets in the report. Please allow reasonable time for investigation and a fix before publicly disclosing the issue.

## Deployment responsibility

The example MCP deployment does not provide application-level authentication. Operators should keep it on a trusted network or place it behind an authenticated reverse proxy, restrict access to the Ollama endpoint and mounted corpus, and review container and model updates before deploying them.

Only the latest commit on the default branch is actively maintained. Older snapshots and locally modified deployments may not receive security fixes.
