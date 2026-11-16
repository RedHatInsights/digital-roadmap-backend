# Digital Roadmap — Egress Monitoring and Allow List

Response to **SEC-NET-REQ-5 (Monitor Egress — outgoing internet traffic)** for the
Digital Roadmap backend (`roadmap`).

Companion documents: [SECURITY_LOGGING.md](SECURITY_LOGGING.md) is the log dictionary
for the Sumo Logic admins, and [LOG_FORWARDING.md](LOG_FORWARDING.md) covers how these
records get off the pods in the first place. Egress events are part of the same stream
and need no separate onboarding.

---

## 1. Summary against the three requirements

| # | Requirement | Status |
|---|---|---|
| 1 | Log connection details, send to the central log store | **Done in the application, with one exception.** HTTP(S) through `egress_client`, the Kessel gRPC channel and the SSO discovery call each emit a `network.egress` event on the `roadmap.security` logger. **Sentry does not** — it connects through the SDK's own transport and is not instrumented; see [Section 4](#what-enforcement-does-not-reach). Delivery to Sumo Logic depends on the forwarder in the companion document. |
| 2 | Consume Infosec deny lists (DNS RBL etc.) | **Not an application control.** Belongs to the cluster's egress proxy and DNS resolvers. See [Section 5](#5-deny-lists-requirement-2). |
| 3 | Enforce an allow list of internet destinations | **List provided in [Section 3](#3-the-allow-list); enforcement implemented and currently in log-only mode.** See [Section 4](#4-enforcement). |

### The headline finding

**This service may make no true internet egress connections at runtime at all.**

Every destination it reaches is either an in-cluster Clowder service or a Red Hat
internal endpoint. The two that could be internet-facing — Sentry and the Notifications
Gateway — are configured from secrets this repository cannot read, so their actual
hostnames have to be confirmed by someone with access to the namespace. Those two
confirmations are the only open questions in this document.

If both turn out to be internal, the correct answer to requirement 3 is that the
allow list is **empty**, and the control is satisfied by a default-deny egress policy
with no exceptions — a considerably stronger position than an allow list.

---

## 2. Why the allow list is static

No destination is ever derived from a request. Every outbound connection target comes
from a setting or a Clowder-injected endpoint, fixed at pod start:

- The RBAC URL is built from `settings.rbac_hostname` / `rbac_port`.
- The Notifications Gateway URL is `settings.subscriptions_url`, from a secret.
- The Kessel target and OIDC issuer are `settings.kessel_url` /
  `settings.kessel_auth_oidc_issuer`.
- The Sentry endpoint is the `SENTRY_DSN`.

Nothing a caller sends — path, query parameter, header or body — is interpolated into a
URL or hostname. The API is read-only and has no webhook, callback, proxy or
fetch-by-URL feature. **There is therefore no SSRF surface and no request-driven
egress**, which is what makes a fixed allow list a complete description of this
service's outbound traffic rather than a best effort.

---

## 3. The allow list

Generated from live configuration at pod start rather than maintained by hand, so it
cannot drift from what the process will actually do. `roadmap.egress.destinations()`
builds it; the API logs the resulting hostnames on the `application.startup` event as
`egress_allow_list`, so the log store holds a per-deployment record of what each pod
was permitted to reach.

### Scope: what the list covers

"Outbound connection" here means an **application-protocol connection to a named
service** — HTTP(S) through `roadmap.egress.egress_client`, plus the Kessel gRPC
channel and the SSO discovery call, which the kessel-sdk makes with its own transport
and which are therefore logged explicitly via `roadmap.egress.log_egress`. It does not
mean every socket the pod opens. Database and Kafka connections are deliberately out
of scope; see [Not egress](#not-egress) below for why.

Entries are **hostnames, never IP addresses**, and are matched against the request's
host exactly. That is possible only because every destination is either a
Clowder-injected service name or a stable FQDN — nothing here is addressed by IP. So
the list does not have to track pod or service IPs, which do churn, and it needs no
CIDR or subnet support. If a future destination ever has to be given as an IP, this
scheme stops being appropriate and the check belongs in a `NetworkPolicy` instead,
where CIDRs are the native unit.

### Runtime destinations

| Purpose | Destination | Protocol | Internet? | Why it is needed |
|---|---|---|---|---|
| `rbac` | RBAC v1, Clowder-injected in-cluster endpoint | HTTP | **No** — in-cluster | Authorization check on every inventory request |
| `kessel-inventory` | `kessel-inventory-api:9000` | gRPC | **No** — in-cluster | RBAC v2 workspace authorization. Disabled by default (`KESSEL_ENABLED=false`) |
| `kessel-oidc` | SSO issuer (`KESSEL_AUTH_OIDC_ISSUER`) | HTTPS | **To confirm** | OIDC discovery and client-credentials token for Kessel. Only reached when Kessel is enabled; unset today |
| `notifications-gateway` | `ROADMAP_SUBSCRIPTIONS_URL`, from the `notification-backend-url` secret | HTTPS, mTLS | **To confirm** | Notificator job only. Reads which org IDs are subscribed to lifecycle reports |
| `sentry` | `SENTRY_DSN` host, from the `sentry` secret | HTTPS | **To confirm** | Error reporting. Connections are made by the Sentry SDK's own transport, not through this application's client |

### Not egress

| Connection | Why it is out of scope |
|---|---|
| Host Inventory read-replica (PostgreSQL) | Database connection to a read-replica reached over the private network, addressed from the `host-inventory-db-readonly` secret. Not internet-bound. Confirm with app-sre that the RDS endpoint is private and has no public accessibility. |
| Kafka (`platform.notifications.ingress`) | Clowder-provisioned in-cluster brokers. |
| Container stdout → Cribl → Sumo Logic | Written to stdout. The Vector collector, not this application, makes the outbound connection, so it belongs to the cluster's egress posture rather than this service's allow list. |

### Build-time, not runtime

Image builds pull from `quay.io`, PyPI and GitHub. These happen in the Konflux
pipeline (`rhel-lightspeed-tenant`), not from the running pods, and are governed by
the build platform's own egress controls. They are listed here only so that a reviewer
comparing network captures against this document is not surprised by them. No running
`roadmap` pod connects to any of them.

### Dead configuration — recommend removal

`ROADMAP_HOST_INVENTORY_URL` defaults to `https://console.redhat.com` and is set as an
environment variable on both workloads in `deploy/config.yml`, but
`settings.host_inventory_url` **is read nowhere in the codebase**. It implies an egress
dependency on `console.redhat.com` that does not exist. It should be removed from
`config.py` and the deployment template so that the allow list and the configuration
agree; removing it requires a coordinated change in app-interface, so it is called out
here rather than done as part of this work.

---

## 4. Enforcement

`roadmap.egress.AuditedTransport` wraps every outbound HTTP client. It is implemented
as an httpx transport rather than as event hooks because hooks never see a connection
that is refused, times out or fails TLS verification — exactly the outcomes worth
alerting on.

A request to a host outside the allow list **always** emits
`network.egress.denied` at `error`. Whether it is also *blocked* is controlled by
`ROADMAP_EGRESS_ENFORCE`, which currently defaults to `false`.

That default is deliberate. Blocking is the goal, but switching it on before the list
has been checked against real traffic risks taking production down to satisfy a
monitoring control. The sequence is:

1. Deploy with `ROADMAP_EGRESS_ENFORCE=false` (the current default).
2. Watch Sumo Logic for `action="network.egress.denied"`. There should be none.
3. If the search is clean for a full notificator cycle — the job runs monthly, on
   `0 6 1 * *`, and is the only workload that reaches the Notifications Gateway —
   set `ROADMAP_EGRESS_ENFORCE=true` in app-interface.

Step 3 needs a full month to be meaningful, because the notificator's egress happens
once a month and is the path most likely to be missing from the list.

### What enforcement does not reach

`AuditedTransport` only sees requests made through `egress_client`. Two configured
destinations do not go through it:

- **Sentry** uses the SDK's own transport. It appears in `destinations()` so that the
  allow list and the `application.startup` record describe the pod's full configured
  reach, but a Sentry connection is never checked against the list and never emits a
  `network.egress` event. With `ROADMAP_EGRESS_ENFORCE=true` this is a silent no-op,
  not a block — the safe direction, but the coverage gap is real.
- **Kessel gRPC and SSO discovery** are made by the kessel-sdk. These *are* logged, at
  the point the connection is established, with an `allow_listed` field recording
  whether the destination was on the list — but they are logged, not enforced.

Application-level enforcement is **defence in depth, not the primary control**. A
compromised process can bypass it trivially by not using these clients. The real
enforcement point is the egress proxy or network policy described below; the value of
the in-process check is that it catches an accidental new dependency at review and
deploy time, close to where someone would introduce one.

Because that proxy is the primary control, `egress_client` is careful not to break it.
httpx only builds its proxy map when no transport is passed to the client constructor
(`allow_env_proxies = trust_env and transport is None`), so the client is constructed
first and its transports wrapped afterwards. `HTTP_PROXY`, `HTTPS_PROXY` and `NO_PROXY`
keep working, and requests routed through a proxy mount are wrapped too, so using a
proxy does not take traffic out of the audit trail.

---

## 5. Deny lists (requirement 2)

Consuming Infosec deny lists via DNS RBLs cannot be done from inside the application.
The pod does not choose its own resolver, and a deny list enforced by the process being
denied is not a control. This requires, from app-sre and Infosec:

- The cluster DNS resolvers for `roadmap-prod` and `roadmap-stage` to consult the
  Infosec-approved RBL feeds.
- A default-deny egress `NetworkPolicy` or egress proxy for those namespaces, with
  exceptions only for the confirmed entries in [Section 3](#3-the-allow-list).

Neither exists in this repository today, and no `NetworkPolicy` is defined by the
ClowdApp template. Both are namespace-level configuration owned by app-sre.

Given the finding in Section 1 — that the runtime destination set is in-cluster and
internal — the natural outcome is a default-deny egress policy with no internet
exceptions, which satisfies requirements 2 and 3 together and makes the deny list moot
for this service.

---

## 6. What gets logged

Egress events join the existing security event stream; the fields below are additions
to the schema in [SECURITY_LOGGING.md](SECURITY_LOGGING.md).

| `action` | When | `result` |
|---|---|---|
| `network.egress` | Any outbound connection attempt completes or fails | `success`, or `failure` on a 4xx/5xx response or a transport error |
| `network.egress.denied` | Destination host is not in the allow list | `failure`, always at `error` |

| Field | Description |
|---|---|
| `direction` | Always `egress`. The field to filter on to see outbound traffic only. |
| `purpose` | Which dependency: `rbac`, `notifications-gateway`, `kessel-inventory`, `kessel-oidc`, `sentry`. Stable across environments, unlike hostnames. |
| `dest_host`, `dest_port`, `dest_scheme` | The destination. |
| `dest_path` | Request path. **Query string excluded** — see below. |
| `http_method` | HTTP method. |
| `status_code` | Response status, when a response was received. |
| `duration` | Nanoseconds. |
| `reason` | `not-in-allow-list` on a denial, or the exception class name on a transport failure (`ConnectError`, `ConnectTimeout`, …). |
| `enforced` | On a denial: whether the connection was blocked or only recorded. |
| `allow_listed` | On gRPC and OIDC events: whether the destination was on the list. |
| `phase` | `channel-created` on the Kessel event. gRPC connects lazily, so the channel existing is not yet a connection — see [SECURITY_LOGGING.md](SECURITY_LOGGING.md) §3. |

Every event also carries the per-request user and network context bound by the logging
middleware, so an outbound call can be attributed to the caller who caused it — join on
`request_id`.

### What is not logged

- **Query strings.** They carry filter parameters and are the usual place for a token to
  leak into a log. The path is kept; everything after `?` is dropped.
- **Request and response headers or bodies.** The RBAC call forwards the caller's
  `X-RH-Identity`, and the Notifications Gateway response contains customer org IDs.
- **Client certificates and secrets.** The notificator's mTLS key is never read into a
  log field.

### Suggested monitoring

| Alert | Condition |
|---|---|
| Unlisted destination | Any `action="network.egress.denied"`. Should never fire. One occurrence means either a new dependency landed without review, or something is reaching out that should not be. |
| Allow list changed | `egress_allow_list` on `action="application.startup"` differs from the previous deployment's. |
| Dependency failure | Sustained `action="network.egress" result="failure"` for one `purpose`. |

---

## 7. Open items

- [ ] **Confirm the Sentry DSN hostname.** Internet (`sentry.io`) or Red Hat hosted?
      This is the single most likely source of genuine internet egress.
- [ ] **Confirm the Notifications Gateway hostname** behind the
      `notification-backend-url` secret, and whether it resolves internally.
- [ ] **Confirm the Host Inventory read-replica is not publicly accessible**, with
      app-sre.
- [ ] **Request a default-deny egress policy** for `roadmap-prod` and `roadmap-stage`,
      with the Section 3 exceptions, once the two hostnames above are known.
- [ ] **Confirm the cluster resolvers consume the Infosec RBL feeds** (requirement 2).
- [ ] **After a full notificator cycle with no denials**, set
      `ROADMAP_EGRESS_ENFORCE=true`.
- [ ] **Remove `ROADMAP_HOST_INVENTORY_URL`** — dead configuration implying an egress
      dependency that does not exist.

---

## 8. Where this is implemented

| What | Where |
|---|---|
| Allow list, audited transport, client factory | `src/roadmap/egress.py` |
| Event actions | `src/roadmap/audit.py` (`ACTION_EGRESS`, `ACTION_EGRESS_DENIED`) |
| RBAC call | `src/roadmap/common.py` (`query_rbac`) |
| Notifications Gateway call | `src/notificator/subscriptions.py` |
| Kessel gRPC channel and OIDC discovery | `src/roadmap/kessel.py` |
| Allow list recorded at startup | `src/roadmap/main.py` (`lifespan`) |
| Enforcement switch | `deploy/config.yml` (`ROADMAP_EGRESS_ENFORCE`) |
| Tests | `tests/test_egress.py` |
