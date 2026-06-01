# Incident and On-Call Readiness

## Rotations

- Primary: backend platform engineer
- Secondary: integrations engineer
- Tertiary: data/infra engineer

## Alert Routing

- Critical API + DB alerts -> pager + incident channel
- Queue + AI degradation alerts -> pager + async operations channel
- KPI anomaly alerts -> business ops + product channel

## Runbook Mapping

- AI degradation: `docs/runbooks.md` (AI section)
- Messaging degradation: `docs/runbooks.md` (Messaging section)
- Database degradation: `docs/runbooks.md` (Database section)

## Readiness Drills

- Weekly rollback tabletop
- Bi-weekly queue replay drill
- Monthly tenant isolation audit review
