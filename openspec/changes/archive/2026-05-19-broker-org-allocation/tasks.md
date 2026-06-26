## 1. API spike and settings

- [x] 1.1 Capture Universal Broker OpenAPI response shapes for deployments, connections (`attributes.type`), and `.../connections/{id}/integrations` (org id/name fields); document in broker client module
- [x] 1.2 Extend [`config/snyk_settings.py`](../../../src/config/snyk_settings.py) (or add `broker_settings.py`) with `tenant_id`, `install_id`, and Broker REST path helpers reusing `api_origin` / `api_version` / token / retry settings

## 2. Universal Broker read client

- [x] 2.1 Add [`integrations/snyk/broker_client.py`](../../../src/integrations/snyk/broker_client.py) with paginated GET for deployments and per-deployment connections
- [x] 2.2 Implement `bitbucket-server` connection filter and `list_connection_integrations(connection_id)`
- [x] 2.3 Wire retries via [`integrations/http_retry.py`](../../../src/integrations/http_retry.py); add unit tests with mocked `urlopen` fixtures

## 3. Plan logic and document builder

- [x] 3.1 Add [`snyk/broker_plan.py`](../../../src/snyk/broker_plan.py): parse `snyk-orgs.json`, optional name→id map from `iter_group_orgs`, pre-check, round-robin allocator
- [x] 3.2 Implement `broker-org-plan.json` version 1 builder (`connections`, `already_integrated`, `assignments`, `warnings`)
- [x] 3.3 Unit tests: ACCP-style fixture (one org with APM, siblings without) does not assign all orgs to one connection; pre-check excludes already-integrated orgs

## 4. CLI and dispatcher

- [x] 4.1 Add [`commands/snyk_broker_plan_cli.py`](../../../src/commands/snyk_broker_plan_cli.py) with `--snyk-orgs`, `--output`, `--tenant-id`, `--install-id`, `--dry-run`, `--env-file`
- [x] 4.2 Register `snyk-broker-plan` in [`commands/dispatch.py`](../../../src/commands/dispatch.py) and update top-level help text
- [x] 4.3 Integration test: mocked Broker + group APIs produce expected plan JSON and exit codes (no connections → failure)

## 5. Documentation

- [x] 5.1 Update [README.md](../../../README.md): pipeline Stages 2.1–2.2 (Broker Plan / Broker Apply), env vars, example commands, plan and apply report schemas
- [x] 5.2 Document that orgs must exist in Snyk before `snyk-broker-apply`; deployments/connections are not created by this tool

## 6. Broker apply

- [x] 6.1 Implement `BrokerClient.create_org_integration` (POST with retries; 409 → conflict/skip)
- [x] 6.2 Add [`snyk/broker_apply.py`](../../../src/snyk/broker_apply.py): load plan v1, resolve org ids, idempotent apply, build report
- [x] 6.3 Add [`commands/snyk_broker_apply_cli.py`](../../../src/commands/snyk_broker_apply_cli.py): `--plan`, `--output`, `--dry-run`
- [x] 6.4 Register `snyk-broker-apply` in dispatch + README Stage 2.2 — Broker Apply
- [x] 6.5 Tests: mock POST; skip `already_integrated`; fail missing `org_id`; dry-run issues no POST
