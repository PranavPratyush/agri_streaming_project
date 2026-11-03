---
title: "Security and Secrets Management"
description: "Rules enforcing zero committed credentials, local service isolation, least-privilege service accounts, and approval gates for public exposure or destructive actions."
always_apply: true
---

# Security & Secrets Management — AgriKafka-Agent

This rule protects developer environments, API keys, database credentials, and system integrity.

---

## 1. Zero Committed Credentials
- **Never commit secrets:** API keys, database passwords, Telegram bot tokens, bearer tokens, private keys, or SSH credentials must never be committed to git.
- All credentials must be loaded exclusively via environment variables or local `.env` files (which are strictly gitignored).
- Root `.env.example` must contain only safe, non-sensitive placeholders.

## 2. Local-Only Service Exposure
- By default, all containerized services (Kafka brokers, TimescaleDB, Grafana, Prometheus, API) must bind exclusively to `localhost` (`127.0.0.1`).
- Never bind services to `0.0.0.0` or open public inbound firewall ports without explicit user review and justification.

## 3. Least Privilege for Accounts & MCP Integrations
- MCP servers (PostgreSQL MCP, Grafana MCP, GitHub MCP, Lenses MCP) must operate with read-only or minimally scoped credentials.
- Do not use administrative/superuser database accounts (`postgres`) for application services or coding assistants. Create a dedicated application user with restricted permissions.

## 4. Approval Gates for Destructive Commands
- Never execute destructive disk operations, system-level modifications, container pruning (`docker system prune -a`), or process termination (`kill`, `Stop-Process`) without explicit user consent.
- Never execute shell scripts downloaded from untrusted external URLs (`curl | bash`).

## 5. Privacy & Hosted Service Usage
- Do not transmit proprietary farmer field data, personal identity records, or private credentials to hosted cloud LLM providers without explicit authorization.
- Mask or anonymize sensitive field identifiers prior to sending investigation prompts to external inference APIs.
