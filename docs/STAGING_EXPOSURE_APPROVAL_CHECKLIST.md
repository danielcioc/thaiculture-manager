# Staging Exposure Approval Checklist

Staging exposure remains **not approved** until every required field is completed and the approver signs off. Keep `WEBSITE_INTEGRATION_ENABLED=false` until then.

## Owners and contacts

- Proxy/hosting owner: Daniel Cioc
- Backend owner: Daniel Cioc
- Monitoring/alert owner: Daniel Cioc
- Retention and cleanup owner: Daniel Cioc; the approved Inquiry policy is delete if unconverted after 30 days
- DBA/backup owner: Daniel Cioc
- Migration owner: Daniel Cioc
- Rollback/release owner: Daniel Cioc
- Staging exposure approval owner: Daniel Cioc
- Alert channel: ________________________________________

Because operational ownership is currently concentrated in one person, backup, migration, and rollback require an explicit independent confirmation before execution.

## Staging scope and window

- Staging hostname: _____________________________________
- Exposure start: _______________________________________
- Exposure end: _________________________________________
- Approval date: ________________________________________
- Approver: _____________________________________________

## Proxy configuration to approve

- Exact distributed proxy rate limits: ______________________________
- Exact proxy request/header/body timeouts: _________________________
- Required route: same-origin `/api/website/*`
- CORS for same-origin route: empty
- Backend public reachability: **blocked**; allow only trusted proxy/internal callers
- Forwarded headers: proxy must not trust arbitrary client-supplied forwarded headers
- Route exposure: proxy must not expose broader Manager API paths
- Confirmed by proxy/hosting owner: _________________________________

## Technical values already established

- Request body limit: **16 KiB**
- Backend process limits: catalog **60/minute**, pricing **20/minute**, booking **5/minute**
- Database connect timeout: **5 seconds**
- Database statement timeout: **5000 ms**
- Website routes: same-origin `/api/website/*`
- CORS: empty for same-origin requests
- `WEBSITE_INTEGRATION_ENABLED`: **false by default**; any staging activation is limited to the approved window
- Quote retention proposal: **30 days after expiry**
- Website booking idempotency TTL: **24 hours**, separate from inquiry retention
- Inquiry PII retention: **delete unconverted Website Inquiry bookings after 30 days**; subsequent email conversation is outside this Manager workflow

The process-local limits are defense in depth. They do not replace the distributed proxy limits entered above.

## Backup and migration gates

- [ ] Target hostname and database confirmed as staging by the DBA/backup owner.
- [ ] Custom-format PostgreSQL backup created before migration or mutable tests.
- [ ] Backup validated with `pg_restore --list`.
- [ ] Migration reviewed and applied only after target confirmation and verified backup.
- [ ] Post-migration tables, columns, indexes, and migration state verified.
- [ ] Backup artifact location and verification recorded: __________________

## Rollback gates

- [ ] Rollback/release owner identified above.
- [ ] Disable `WEBSITE_INTEGRATION_ENABLED` and remove public proxy routing as the first containment steps.
- [ ] Rollback keeps additive tables and business data; no automatic `DROP` or data deletion.
- [ ] Any restore from backup requires explicit approval from the responsible owners.
- [ ] Rollback verification steps and completion recorded: __________________

## Final approval

- [ ] All owner and contact fields completed.
- [ ] Proxy limits and timeouts approved.
- [ ] Monitoring and alert routing approved.
- [x] Inquiry PII retention policy is documented per the approved 30-day decision.
- [ ] Exposure hostname and start/end window approved.
- [ ] Backup and migration gates passed.
- [ ] Rollback gates reviewed.
- [ ] Feature flag remains false outside the approved staging exposure window.

- Approver decision: ____________________________________
- Approval date: ________________________________________
