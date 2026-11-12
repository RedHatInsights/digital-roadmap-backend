# Digital Roadmap — Security Logging Reference

This is the log dictionary for the **Digital Roadmap backend** (`roadmap`), written so
that Sumo Logic administrators and the Information Risk and Security team can read its
log entries and understand their contents. It covers the SEC-MON-REQ-1 (Logging &
Monitoring) control.

How these records reach Sumo Logic is a separate concern, covered in
[LOG_FORWARDING.md](LOG_FORWARDING.md). Nothing in this dictionary depends on the
destination.

---

## 1. What the service is

Digital Roadmap is a read-only REST API on the Red Hat Hybrid Cloud Console
(`console.redhat.com/api/roadmap`). It reports RHEL lifecycle and roadmap information
for the systems in a customer's Host Inventory.

| | |
|---|---|
| Application name | `roadmap` |
| Platform | OpenShift (Clowder/ClowdApp), managed by app-sre |
| Components | `api` (web deployment, 3+ replicas) and `notificator` (scheduled job) |
| Upstream data | Host Inventory read-replica database (read-only), RBAC/Kessel, Kafka |
| Authentication | Performed upstream. 3scale injects an `x-rh-identity` header; the service does not hold credentials and has no login of its own. |

### Data classification

The service **processes and transmits**, but does not itself store, data classified as
**Red Hat Internal** and **Red Hat Restricted (+PII)**:

- Customer system inventory — hostnames/display names, operating system versions,
  installed packages and subscription products, read per `org_id`.
- Caller identity — Red Hat or customer username, user ID, organisation ID.

**The log records described here deliberately do not contain that data.** A data-access
event records *that* an organisation's inventory was read and under what authorisation
scope; it does not include hostnames, package lists, or the caller's search terms. The
identity header also carries the user's email address and real name, and those are
dropped before logging. See [Section 6](#6-pii-handling).

---

## 2. How the data reaches Sumo Logic

| | |
|---|---|
| Data source | Container **stdout** (not a file on disk) |
| Format | **JSON**, one object per line, one line per event |
| Collection | Vector, via the OpenShift `ClusterLogForwarder` → Cribl Stream (HEC) → Sumo Logic |
| Log location | No path. Records are the container logs of the `roadmap` pods. |
| Production | Cluster `crcp01ue1`, namespace `roadmap-prod` |
| Stage | Cluster `crcs02ue1`, namespace `roadmap-stage` |
| Index | `rh_DRM-001` — dedicated, so access can be scoped per [Section 6](#6-pii-handling) |
| Field location | Under `structured.*` after the forwarder's `parse` filter |

See [LOG_FORWARDING.md](LOG_FORWARDING.md) for the forwarder configuration, the
authentication choice, ingest volume and what remains outstanding.

The application writes only to stdout. It has no Sumo Logic client, no syslog output,
and writes no log files, so there is no file for a forwarder to tail and no log rotation
to configure. JSON output is enforced in every deployed environment by the
`ROADMAP_JSON_LOGGING` environment variable, set in `deploy/config.yml`.

> **Prerequisite, not yet in place:** forwarding itself. `crcp01ue1` already runs a
> cluster-wide `ClusterLogForwarder` in `openshift-logging`; getting these records to
> the log store is an entry in that template's output list, raised as an app-interface
> MR. It is not configured from this repository — see
> [LOG_FORWARDING.md](LOG_FORWARDING.md).

### Host-level logs

The Linux host logs named in the Infosec guidelines (`/var/log/audit/audit.log`,
`/var/log/messages`, `/var/log/secure`) belong to the OpenShift worker nodes. They are
the responsibility of the platform team that operates the cluster, not of this service,
which runs in an unprivileged container with no access to them.

---

## 3. Record schema

Every record carries the common fields. Security events additionally carry `action` and
`result`, which is what distinguishes them from ordinary application logs.

### Common fields (all records)

| Field | Description |
|---|---|
| `timestamp` | ISO 8601, UTC. Date and time of the event. |
| `level` | `info`, `warning`, `error`, `critical`. |
| `logger` | Emitting logger. `roadmap.security` for the events of interest; `api.access` for HTTP access logs. |
| `message` | Human-readable description. For security events this equals `action`. |
| `request_id` | Correlates every record emitted while handling one HTTP request. |
| `dd.trace_id`, `dd.span_id` | Datadog trace correlation. `0` when not traced. |

### User identification

Present on any record emitted while handling a request. Values are `null` when the
caller presented no identity header or an unreadable one — which is itself searchable.

| Field | Description |
|---|---|
| `user` | Username of the caller (the `userid`). For service accounts, the service account username. |
| `user_id` | Stable user identifier; service account `client_id` for service accounts. |
| `org_id` | Customer organisation whose data is being acted on. |
| `account_number` | Legacy Red Hat account number. |
| `identity_type` | `User`, `ServiceAccount`, `System`, … |
| `auth_type` | How the caller authenticated upstream, e.g. `jwt-auth`, `basic-auth`, `cert-auth`. |
| `is_internal` | `true` for Red Hat associates. |
| `is_org_admin` | `true` if the caller administers their organisation. |

### Network identification / upstream session data

These are the join keys to the edge, load balancer and 3scale logs for the same request.

| Field | Description |
|---|---|
| `src_ip` | **The user's IP address, as reported by the request headers.** Taken from `true-client-ip` when present, else the left-most entry of `x-forwarded-for`, else the peer address. **Not verified** — see the caveat below. |
| `true_client_ip` | Akamai `True-Client-IP` header, verbatim. |
| `x_forwarded_for` | `X-Forwarded-For` header, verbatim — the full hop list. |
| `peer_ip` | `request.client.host`. **Not the TCP peer and not the router.** Uvicorn runs with `--forwarded-allow-ips=*`, so its proxy-headers middleware overwrites the client address with the left-most `X-Forwarded-For` entry — the same value `src_ip` usually holds, from the same caller-supplied header. Only when no `X-Forwarded-For` is present does this fall back to the real peer. Do not use it as independent corroboration of `src_ip`. |
| `edge_request_id` | Akamai/edge request identifier (`x-rh-edge-request-id`). Joins this event to the edge logs. |
| `user_agent` | Caller's `User-Agent`. |

> `src_ip` is the field to use for "where did this user come from".

> **`src_ip` is an assertion, not a verified fact.** It is derived entirely from request
> headers, and the container runs uvicorn with `--forwarded-allow-ips=*`, so the
> application accepts `X-Forwarded-For` and `True-Client-IP` from any peer that can
> reach it rather than from a trusted proxy list. A caller able to reach the pod
> directly can therefore set `src_ip` to any value.
>
> In practice the edge and the namespace network policy are what make the value
> trustworthy: ingress is restricted to the gateway namespaces, and the edge overwrites
> these headers. The field is only as good as that, and the guarantee lives outside this
> application. **Do not treat `src_ip` as verified attribution in an investigation
> without confirming the ingress path for the request in question** — join to
> `edge_request_id` and the edge logs, which are produced by something the caller cannot
> set.
>
> **`peer_ip` is not a second opinion.** It is `request.client.host`, and
> `--forwarded-allow-ips=*` means uvicorn has already overwritten that with the
> left-most `X-Forwarded-For` entry before the application sees it. On a request
> carrying that header, `src_ip` and `peer_ip` are the same caller-supplied value
> reached by two routes. Two fields agreeing is not corroboration when both derive from
> the same header.
>
> Restricting `--forwarded-allow-ips` to the router's address range is what would make
> these fields trustworthy at the application. That is a deployment change, tracked
> separately; this note exists so nobody reads the records as stronger than they are in
> the meantime.

### Security event fields

| Field | Description |
|---|---|
| `action` | Type of event. One of the values in [Section 4](#4-events-of-interest). |
| `result` | `success` or `failure`. |
| `error_code` | HTTP status for a failure, e.g. `401`, `403`, `500`, `502`. |
| `reason` | Short machine-readable cause, e.g. `missing-identity`, `not-internal`. |
| `endpoint` | `METHOD /path` of the administrative action attempted. |
| `resource` | What was acted on. Currently always `host_inventory`. |
| `data_classification` | Classification of the data reached, e.g. `red-hat-restricted`. |
| `scope` | `unrestricted` (caller may read the whole org) or `host_groups` (restricted subset). |
| `host_group_count` | Number of host groups the caller was limited to. |
| `record_count` | Number of records returned, where known. |
| `authz_backend` | `rbac_v1` or `kessel`, i.e. which authorization service decided. |
| `phase` | What actually completed, where "the event succeeded" would be ambiguous. See [Phases](#phases) below. |
| `authorization` | On admin events: `internal-user`, or `skipped-non-prod`. |
| `os_major`, `os_minor` | RHEL version the inventory read was filtered to, if any. |
| `lifecycle_type` | Lifecycle filter applied: `mainline`, `EUS`, `ELS`, `E4S`. |
| `searched` | `true` if the caller supplied a search term. The term itself is not logged. |
| `includes_packages` | `true` if the read included installed packages and dnf modules. |
| `env_name`, `app_name`, `component` | On startup/shutdown: which environment and which process (`notificator` for the scheduled job). |
| `audit_level_invalid` | Diagnostic. Present only if a caller passed an unrecognised log level; the event is still emitted, at `error`. Should never appear. |

### Phases

Some operations are not a single moment, so `result` alone would overstate what
happened. Where that is true the event carries a `phase`:

| `phase` | On | Means |
|---|---|---|
| `stream-created` | `data.access` | The query ran and the row stream was opened. The endpoint reads the rows *after* this record is written. |
| `stream-consumed` | `data.access` | A database error occurred while the rows were being read. |
| `channel-created` | `network.egress` (Kessel) | The gRPC channel object was built. gRPC connects lazily, so nothing has been dialled yet. |

One read that fails part-way therefore emits two records — a `stream-created`
success and a `stream-consumed` failure. That is deliberate: both are true, and the
pair is what shows an access began and then broke. Count distinct `request_id`
values, not events, when counting accesses.

---

## 4. Events of interest

Search for security events with `logger="roadmap.security"`, or on `action`.

| `action` | Event of interest | When emitted | `result` |
|---|---|---|---|
| `data.access` | Accessing Red Hat Internal / Restricted (+PII) data | Every read of an organisation's host inventory | `success`, or `failure` on database error |
| `admin.action` | Administrative action by a privileged user | Any request to an `/admin` route that passes the internal-user check | `success` |
| `authorization` | Authorization failure | Caller denied access to host inventory (403), denied an admin route (403), or the authorization service itself failed | `failure` |
| `authentication` | Invalid login attempt | Admin route reached with a missing or unreadable identity header (401) | `failure` |
| `application.startup` | Process startup | API process starts; notificator job starts | `success` |
| `application.shutdown` | Process shutdown | API process stops; notificator job finishes or aborts | `success`, or `failure` at `error` with `reason` set to the exception class if the stop itself failed |
| `network.egress` | Outbound connection (SEC-NET-REQ-5) | Any connection this service makes to an external dependency | `success`, or `failure` on an error response or transport error |
| `network.egress.denied` | Outbound connection to an unlisted destination | Destination host is not in the egress allow list | `failure` |

The two `network.egress*` actions cover a different control, **SEC-NET-REQ-5**, and are
documented in full — including the allow list and the fields they add — in
[EGRESS_MONITORING.md](EGRESS_MONITORING.md). They are listed here because they share
this logger and this index. Filter them out with `direction!="egress"` when searching
for the SEC-MON-REQ-1 events above.

### Warnings and errors from these events

The guidelines also ask for the warnings and errors generated by the events above.

- Denials are logged at `warning`.
- A failure of the authorization service itself (RBAC or Kessel unreachable, HTTP 502,
  timeout 504) is logged at `error` with `action="authorization"`. This matters because
  an authorization service that is not answering is how a denial would fail to be
  recorded at all.
- Database errors while reading inventory are logged at `error` with
  `action="data.access"` and `result="failure"`.

Security events are emitted at `info` and above, and the `roadmap.security` logger is
pinned to `info` in code. Raising the application's log level suppresses ordinary
application logs but **cannot** suppress these events.

### Events of interest that do not apply

| Event of interest | Why not applicable |
|---|---|
| User login / logout | Authentication happens upstream in Red Hat SSO and 3scale, which log it. This service never sees a credential; it receives an already-authenticated identity header. Failed *authentication* against an admin route is logged (`action="authentication"`). |
| Grant / modify / revoke user access | Access is granted in RBAC/Kessel, which record it. This service only reads authorization decisions, never changes them. Note for Infosec: RBAC keeps these as rows in its own `AuditLog` table (`rbac/management/audit_log/`) exposed over an API — covering group, role, user, permission, workspace and role-binding changes — **not** as a log stream. They are therefore not searchable alongside the records described here. |
| Creation / deletion of system-level objects | The service is read-only against Host Inventory and installs nothing at runtime. Package and image changes happen at build time and are recorded in the Konflux build pipeline and git history. |
| Tampering with audit trails | Records go to stdout and leave the pod immediately; there is no local log file for the application to alter. Loss of the stream is detected by the gap-detection alert in [Section 7](#7-suggested-monitoring). |
| Accepting a network connection | Terminated at the edge, load balancer and OpenShift router, which log it. `src_ip` and `edge_request_id` on each record join to those logs. |

---

## 5. Worked examples

Administrative action by an internal user (note `src_ip` is the user, `peer_ip` the router):

```json
{"action": "admin.action", "result": "success", "endpoint": "POST /api/roadmap/admin/notifications/lifecycle/custom",
 "authorization": "internal-user", "user": "rmonk", "user_id": "u-1", "org_id": "12345",
 "account_number": "67890", "identity_type": "User", "auth_type": "jwt-auth", "is_internal": true,
 "is_org_admin": false, "src_ip": "1.2.3.4", "true_client_ip": "1.2.3.4",
 "x_forwarded_for": "1.2.3.4, 55.66.3.2", "peer_ip": "10.128.0.9", "edge_request_id": "edge-abc",
 "user_agent": "curl/8.0", "request_id": "01JB2…", "logger": "roadmap.security", "level": "info",
 "timestamp": "2026-10-05T15:47:10.063245Z", "message": "admin.action"}
```

Authorization failure — caller has no inventory permission:

```json
{"action": "authorization", "result": "failure", "error_code": 403,
 "reason": "Not authorized to access host inventory", "resource": "host_inventory",
 "authz_backend": "rbac_v1", "user": "someone", "org_id": "12345", "src_ip": "1.2.3.4",
 "request_id": "01JB2…", "logger": "roadmap.security", "level": "warning",
 "timestamp": "2026-10-05T15:47:11.101Z", "message": "authorization"}
```

Access to Red Hat Restricted (+PII) data — note that no host data appears:

```json
{"action": "data.access", "result": "success", "resource": "host_inventory",
 "data_classification": "red-hat-restricted", "os_major": 9, "os_minor": 4,
 "scope": "host_groups", "host_group_count": 2, "record_count": 42, "searched": true,
 "user": "customer-user", "org_id": "12345", "src_ip": "1.2.3.4", "request_id": "01JB2…",
 "logger": "roadmap.security", "level": "info", "timestamp": "2026-10-05T15:47:12.880Z",
 "message": "data.access"}
```

Invalid identity presented to an admin route:

```json
{"action": "authentication", "result": "failure", "error_code": 401, "reason": "invalid-identity",
 "endpoint": "POST /api/roadmap/admin/notifications/lifecycle/custom", "user": null, "org_id": null,
 "src_ip": "4.5.6.7", "request_id": "01JB2…", "logger": "roadmap.security", "level": "warning",
 "timestamp": "2026-10-05T15:47:13.002Z", "message": "authentication"}
```

### HTTP access log

Separate from the events above, every request produces an access record on the
`api.access` logger, carrying the same user and network fields plus `http.status_code`,
`http.method`, `http.url` and `duration` (nanoseconds). Health checks (`/v1/ping`) and
`/metrics` are excluded. These are not events of interest in themselves, but they are
the per-request context for the ones that are — join on `request_id`.

---

## 6. PII handling

Deliberately **not** logged:

- Email address, first name and last name from the identity header.
- Hostnames, display names, installed packages and other host inventory contents.
- Caller-supplied search terms, which may name a customer's systems.
- Database credentials and the raw identity header.

Deliberately **logged**, because attribution is the point of an audit record:
`user`, `user_id`, `org_id`, `account_number`, and the caller's IP address.

Anyone granted access to this data in Sumo Logic can see which Red Hat associate or customer
user accessed which organisation's inventory and when. Access should be scoped
accordingly.

---

## 7. Suggested monitoring

| Alert | Condition |
|---|---|
| Data source gap | No `roadmap` events for 15 minutes while the service is running — the control requires detecting loss of log delivery. |
| Admin route abuse | Any `action="authentication" result="failure"`, or `action="authorization" reason="not-internal"`. These routes are internal-only, so failures should be rare and are worth reviewing individually. |
| Authorization denial spike | Sustained rise in `action="authorization" error_code=403` for one `user` or `src_ip` — possible enumeration. |
| Authorization service failure | Any `action="authorization" level="error"` — authorization decisions are not being made reliably. |
| Broad data access | One `user` raising `data.access` across an unusual number of distinct `org_id` values. |
| Unexpected restarts | `action="application.startup"` more often than deployments would explain. |

---

## 8. Open items

The events themselves are implemented and tested. What remains is delivery, tracked in
full in [LOG_FORWARDING.md](LOG_FORWARDING.md) §9. The ones that bear on this document:

- [ ] **Get the `ClusterLogForwarder` applied** by app-sre for `roadmap-prod`. Until
      then these records go no further than the pod.
- [ ] **Confirm whether a production index exists.** The token in hand is
      `Int_DRM-001`, which looks like integration/stage only.
- [ ] **Confirm the Rover/LDAP group** that should receive access.
- [ ] **Set up the data source gap alert** in [Section 7](#7-suggested-monitoring).
      Detecting loss of log delivery is a requirement of the control, not an optional
      extra.

---

## 9. Where this is implemented

| What | Where |
|---|---|
| Event definitions, field schema, PII filtering | `src/roadmap/audit.py` |
| Per-request user and network context binding | `src/roadmap/main.py` (`logging_middleware`) |
| JSON rendering, audit log level pinning | `src/roadmap/custom_logging.py` |
| Data access and authorization events | `src/roadmap/common.py` |
| Administrative action and authentication events | `src/roadmap/admin/__init__.py` |
| Startup / shutdown events | `src/roadmap/main.py`, `src/notificator/__main__.py` |
| JSON logging enabled per environment | `deploy/config.yml` (`ROADMAP_JSON_LOGGING`) |
| Forwarding to Sumo Logic | Not in this repository — app-interface, see [LOG_FORWARDING.md](LOG_FORWARDING.md) |
| Outbound connection events (SEC-NET-REQ-5) | `src/roadmap/egress.py` — see [EGRESS_MONITORING.md](EGRESS_MONITORING.md) |
| Tests | `tests/test_audit.py`, `tests/test_egress.py` |
