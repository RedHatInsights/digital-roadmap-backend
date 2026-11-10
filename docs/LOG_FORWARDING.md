# Digital Roadmap — Log Forwarding

How the security log records described in [SECURITY_LOGGING.md](SECURITY_LOGGING.md)
get off the pods and into the central log store, and what is still needed to finish it.

This replaces the earlier Splunk onboarding plan. Two things changed: the collector is
**Vector** under OpenShift Logging 6 rather than Fluentd, and the data now reaches
Sumo Logic by way of a **Cribl Stream** HTTP Event Collector source rather than going
to Splunk directly. The application emits exactly the same records either way — nothing
in the log dictionary changes — but the transport and the onboarding process are
different enough that the old ServiceNow "Add data to Splunk" request no longer applies.

The forwarder configuration is **not in this repository**. It is an app-interface
change against the cluster-wide forwarder — see [Who applies this](#who-applies-this).
What follows is the specification for that change: the pipeline it has to produce, the
endpoint and token it needs, and how to verify it once applied.

---

## 1. The pipeline

```
roadmap-api / notificator pod
  └─ stdout: one JSON object per line     (ROADMAP_JSON_LOGGING=true)
       └─ Vector collector DaemonSet       (OpenShift Logging 6)
            ├─ parse filter  → JSON lifted out of `message` into `structured`
            ├─ prune filter  → pod annotations dropped
            └─ splunk output → HEC POST to Cribl Stream
                 └─ Cribl routes to Sumo Logic, under index rh_DRM-001
```

| | |
|---|---|
| Data source | Container **stdout**. No file on disk, no syslog, no agent in the pod. |
| Format on the wire | Splunk HEC envelope, gzip-compressed, batched under 1 MB |
| Collector | Vector, via `ClusterLogForwarder` (`observability.openshift.io/v1`) |
| Transport | Cribl Stream HEC source |
| Destination | Sumo Logic, via Cribl's routing |
| Production | Cluster `crcp01ue1`, namespace `roadmap-prod` |
| Stage | Cluster `crcs02ue1`, namespace `roadmap-stage` |

Production is the environment that has to be onboarded for the control. Stage is worth
doing first — it carries the same classes of data, so it is a real rehearsal, and it
lets the field extractions be validated before production data lands.

### Who applies this

Not this team. A `ClusterLogForwarder` runs a collector DaemonSet and requires a
`ClusterRoleBinding` to the cluster-scoped `collect-application-logs` role, so it is
owned by **app-sre**.

There is no second forwarder to stand up. `crcp01ue1` already runs a cluster-wide
`ClusterLogForwarder` in the `openshift-logging` namespace, rendered from
`/setup/cluster-logging/clusterlogforwarder.yaml.j2` in app-interface. Onboarding this
service is an entry in that template's `SPLUNK_OUTPUTS` list plus the matching pipeline
— an app-interface MR, raised separately from this repository.

The input for that pipeline must keep `includes: [{namespace: roadmap-prod}]`, so it
stays scoped to this application and does not pick up neighbouring namespaces.

---

## 2. Why the output type is `splunk`

Worth stating, because Splunk is not in the path and the type name is misleading.

Cribl Stream exposes a **Splunk HEC source**: it speaks the HEC wire protocol, accepts
the `Authorization: Splunk <token>` header, and reads the HEC event envelope with its
`index`, `source` and `sourcetype` metadata. It then routes onward to Sumo Logic.

So `type: splunk` is correct here. It describes the protocol being spoken to the next
hop, not the final destination. Three of its settings are load-bearing:

| Setting | Why |
|---|---|
| `index`, `source`, `sourceType` | Mirror the provisioned token definition exactly. Cribl routes on these — they are not cosmetic labels. |
| `tuning.maxWrite: 1Mi` | Keeps individual POSTs to a size HEC receivers reliably accept. The collector's default batch is larger. |
| `tuning.deliveryMode: AtLeastOnce` | This is an audit trail. Buffered records should survive a collector restart rather than being dropped in favour of latency. Duplicates are acceptable here; gaps are not. |

Note `tuning.compression` for this output type accepts only `none` or `gzip` — unlike
the generic `http` output, `snappy` and `zlib` are not valid.

### What was ruled out

Sending to **Sumo Logic directly** with a `type: http` output does not work with these
credentials. Sumo Logic has no HEC-compatible endpoint — ingest is a plain POST of
newline-delimited records to an HTTP Logs and Metrics Source, authenticated by a
presigned URL or an `x-sumo-token` header. A HEC token posted to Sumo's receiver
returns `401 Failed to authenticate`. That path is only relevant if Cribl is ever
removed from the chain.

---

## 3. The token

Provisioned as `Int_DRM-001`:

| Field | Value |
|---|---|
| `index` | `rh_DRM-001` |
| `source` | `http:rh_DRM-001` |
| `sourcetype` | `fluentd` |
| `token` | `crblhecint-…` (in vault; never in this repository) |

The forwarder reads the token from a Secret via
`splunk.authentication.token.{secretName,key}`. Note this is a different shape from the
generic `http` output's `authentication.token`, which takes `{from, secret}` — the
Splunk output takes `secretName` and `key` directly.

### The sourcetype cannot be set to `fluentd`

Worth knowing before anyone tries: **the forwarder's `sourceType` field is inert unless
`payloadKey` is also set.** In the operator's generator
(`internal/generator/vector/output/splunk/splunk.go`) the configured sourceType is only
emitted on the branch where `payloadKey` is non-empty; otherwise it hardcodes
`sourcetype = "_json"`. The operator's own test fixtures corroborate this — every
fixture with a custom sourcetype also has a payloadKey, and the plain ones all show
`_json`.

So Cribl will receive `sourcetype=_json`, not `fluentd`, whatever the token definition
says. HEC lets the sender override the token default, so `_json` wins.

This is fine if Cribl routes on the token or the index, which is the usual arrangement.
**Confirm that it does.** If routing genuinely keys off `sourcetype == "fluentd"`, the
only way to force it is to also set `payloadKey: .structured`, which changes what gets
sent (§5) — raise it rather than doing it silently.

Setting `sourceType: fluentd` in the manifest and assuming it works is the trap here, so
the field is deliberately absent with a comment in its place.

### Two more things to query with whoever issued the token

**`fluentd` is the wrong label regardless.** Fluentd is removed in OpenShift Logging 6;
the collector is Vector. Worth asking for the token's sourcetype to be renamed to
something accurate now that `_json` is what actually arrives.

**`Int_` suggests this is the integration/stage token.** Production almost certainly
needs its own token and index. Confirm before wiring this into `roadmap-prod` — the
manifest currently targets the prod namespace with what may be a non-prod credential.

---

## 4. The endpoints

Two exist. Both answer on `:8088` and `:443`, and both return
`{"text":"HEC is healthy","code":17}` from `/services/collector/health`.

| Host | ALB | Certificate | CA bundle needed? |
|---|---|---|---|
| `splunk-hec.redhat.com` | Public (`splunk-hec-external-*`) | DigiCert Global G2, `CN=splunk-hec.redhat.com` | **No** — chains to a public root |
| `splunk-hec.corp.redhat.com` | Internal, `10.31.20.x` (`internal-Splunk-HEC-*`) | `CN=splunk-hf.corp.redhat.com`, issued by `2023 Certificate Authority RHCSv2` | **Yes** — internal Red Hat CA |

### Ingest is internal-only, by design

Verified 2026-10-21 with the `Int_DRM-001` token:

| Endpoint | Result |
|---|---|
| `corp:8088` | **`{"text":"Success","code":0}`** — 30/30 requests returned 200, no 502s |
| `corp:443` | **Success** — 8/8 |
| `public:8088` / `public:443` | `403 Invalid token`, plus intermittent 502s |

The Cribl team has confirmed the internal-only scope is **intentional**, not a partial
rollout. `splunk-hec.redhat.com` is therefore not a fallback and should not be
configured as one — pointing at it to work around a network problem will fail closed.

Two consequences:

**Cluster reachability to `10.31.20.0/24` is a hard prerequisite with no plan B.**
Working assumption is that it is available. If it turns out not to be, this approach is
blocked outright and the alternatives are a network exception or the Clowder/CloudWatch
path the rest of the Insights platform uses (see §2 on what was ruled out).

**TLS verification needs the internal CA.** The certificate is issued by
`2023 Certificate Authority RHCSv2`, which is not in the collector's default trust
store, so `tls.ca` is mandatory and `insecureSkipVerify` is not an acceptable
substitute for a Restricted (+PII) stream.

Rather than pin a CA certificate in git — where it would silently expire — the manifest
creates a ConfigMap labelled `config.openshift.io/inject-trusted-cabundle: "true"`.
OpenShift's Cluster Network Operator populates `ca-bundle.crt` with the cluster's
trusted CAs and keeps it current, so this needs nothing from app-sre.

That works only if the cluster's trust bundle actually carries the internal CA. Verify
once the ConfigMap exists:

```sh
oc -n roadmap-prod get cm roadmap-trusted-ca \
  -o jsonpath='{.data.ca-bundle\.crt}' \
  | openssl crl2pkcs7 -nocrl -certfile /dev/stdin \
  | openssl pkcs7 -print_certs -noout | grep -i RHCSv2
```

If that returns nothing, ask app-sre either to add the internal CA to the cluster trust
bundle or for an existing ConfigMap that has it, and repoint `tls.ca`.

**The `splunk` in both hostnames is legacy naming.** The load balancers' target group
members are Cribl nodes — a 22-host worker group that takes the OpenShift traffic. The
corp certificate's CN of `splunk-hf.corp.redhat.com` ("heavy forwarder") is a leftover
from the same era. Nothing Splunk is actually in the path; do not go looking for a
separate Cribl endpoint, these are it.

### Probe

```sh
curl -i -X POST \
  -H "Authorization: Splunk ${HEC_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data '{"event":{"probe":"roadmap-forwarding-test"},
           "index":"rh_DRM-001",
           "source":"http:rh_DRM-001"}' \
  https://splunk-hec.redhat.com:8088/services/collector/event
```

`{"text":"Success","code":0}` is what you want. `{"text":"Invalid token","code":4}`
means the endpoint is healthy but does not recognise the token.

A 200 means accepted at this hop, not that it reached Sumo Logic. Search for
`roadmap-forwarding-test` on the far side to confirm the routing rule fires.

---

## 5. Where the fields end up

After the `parse` filter, the application's JSON is under `structured` on each record,
alongside Kubernetes metadata the collector adds:

| | |
|---|---|
| `structured.action`, `structured.user`, `structured.org_id`, … | Every field in [SECURITY_LOGGING.md](SECURITY_LOGGING.md) §3 |
| `kubernetes.namespace_name` | `roadmap-prod` / `roadmap-stage` |
| `kubernetes.labels.app` | `roadmap-api` or `notificator` |
| `message` | The raw line, retained |

The whole record goes into the HEC `event` field. Setting `payloadKey: .structured` on
the output would send only the application's own JSON object instead — smaller, and
trivial to extract from — but it drops the pod and namespace metadata. Only worth doing
if Cribl re-enriches with that metadata itself.

**This all depends on the records being JSON.** `json_logging` defaults to `False` in
code, so a pod with the variable unset emits plain text and the `parse` filter has
nothing to parse. `ROADMAP_JSON_LOGGING=true` is set for both workloads in
`deploy/config.yml`, which is what makes every deployed environment safe to parse.

---

## 6. What is in the data

The service **processes and transmits** data classified **Red Hat Internal** and **Red
Hat Restricted (+PII)** — customer system inventory from the Host Inventory
read-replica, and caller identity from Red Hat SSO. It stores none of it.

The logs contain **identity and access metadata, not customer system data**:

| Classification | Fields | Notes |
|---|---|---|
| **Red Hat Restricted (+PII)** | `user`, `user_id` | Username of a Red Hat associate or a customer user |
| **Red Hat Restricted (+PII)** | `src_ip`, `true_client_ip`, `x_forwarded_for` | The end user's IP address |
| **Red Hat Internal** | `org_id`, `account_number` | Identifies the customer organisation whose data was accessed |
| **Red Hat Internal** | `is_internal`, `is_org_admin`, `auth_type`, `identity_type` | Caller's role and authentication method |

Together these reveal **which Red Hat associate or customer user accessed which customer
organisation's inventory, from where, and when**. That is the point of the audit trail,
and it is what access should be scoped against.

Deliberately excluded by the application before anything is written: email address,
first and last name, host inventory contents (hostnames, packages, dnf modules,
subscription products), caller-supplied search terms, and all credentials including the
raw `x-rh-identity` header. No payment-card, health or government-identifier data is
involved at any point.

Full detail in [SECURITY_LOGGING.md](SECURITY_LOGGING.md) §6.

Because `rh_DRM-001` is a dedicated index, access can be scoped to it and nothing else.
That is worth preserving — it is an index-level decision that cannot be walked back once
the data is mixed into a shared index.

---

## 7. Volume

**Measured record sizes** (actual application output):

| Record | Size |
|---|---|
| `data.access` security event | ~929 bytes |
| `api.access` HTTP access log | ~1,015 bytes |
| `authorization` failure event | ~887 bytes |
| `network.egress` event (SEC-NET-REQ-5) | ~807 bytes |

A request that reads host inventory produces three records — access log, data-access
event, and one egress event for the RBAC call — totalling ~2.8 KB. A request that does
not touch inventory produces only the access log (~1.0 KB).

The collector adds Kubernetes metadata and the HEC envelope on top. The `prune` filter
drops pod annotations and namespace labels, which are static per pod and repeat on every
record; what remains is roughly **300–400 bytes per record**. Budget on **~3.5 KB per
inventory-reading request**.

| Rate | Volume/day (at 3.5 KB/req) |
|---|---|
| 1 req/s | ~0.3 GB |
| 5 req/s | ~1.5 GB |
| 10 req/s | ~3.0 GB |
| 25 req/s | ~7.6 GB |

### Get the real number

Sumo Logic contracts are priced on ingest, so this figure matters. Run against the
`crcp01ue1-prometheus` datasource in Grafana:

```promql
sum(increase(roadmap_http_requests_total{
  namespace="roadmap-prod",
  job="roadmap-api",
  handler!="/api/roadmap/v1/ping"
}[24h]))
```

Then **daily volume ≈ requests/day × 3.5 KB**, with 1.4 KB as the lower bound.

Excluding `/api/roadmap/v1/ping` matters: liveness and readiness probes hit it every 15
seconds on every replica. Those are already dropped from the logs by the application and
must be dropped from the estimate too. `/metrics` is likewise not logged.

The monthly `notificator` job adds a negligible amount.

---

## 8. Who needs access

| Who | Why |
|---|---|
| **Digital Roadmap engineering team** | Service owners; incident response, debugging, and verifying the data source stays healthy. Current code owners: `@pr-watson`, `@hosekadam`, `@SerCantus`, `@DnsZhou`. |
| **Information Risk and Security / Infosec** | Audit and incident handling — the reason for the control. |
| **Red Hat Audit** | Periodic compliance review. |

Grant this through a Sumo Logic role scoped to the `rh_DRM-001` data, mapped to a
Rover/LDAP group rather than to individuals. Given §6, the group needs confirming before
access is granted.

---

## 9. Verifying it works end to end

Once app-sre has applied the forwarder:

```sh
# Forwarder accepted the config and is Managed
oc -n roadmap-prod get clusterlogforwarder roadmap -o yaml | yq '.status.conditions'

# Collector pods are up
oc -n roadmap-prod get pods -l app.kubernetes.io/component=collector

# The generated Vector config — confirms index/source/sourcetype actually
# rendered the way the CR intended
oc -n roadmap-prod extract secret/collector-config --to=- 2>/dev/null | grep -A 15 'sinks.output_cribl_hec'
```

Then, against the collector's metrics endpoint:

```promql
# Events reaching the HEC sink
sum by (component_id) (rate(vector_component_sent_events_total{component_type="splunk_hec_logs"}[5m]))

# Events being dropped rather than delivered — should be flat at zero
sum by (component_id) (rate(vector_component_discarded_events_total{component_type="splunk_hec_logs"}[5m]))
sum by (component_id, error_type) (rate(vector_component_errors_total{component_type="splunk_hec_logs"}[5m]))
```

`splunk_hec_logs` is the Vector sink type the operator generates for a `type: splunk`
output — querying on `component_type="splunk"` silently returns nothing.

Then search Sumo Logic for the `rh_DRM-001` data; records should appear within a minute
or two. Check specifically that `structured.action` is populated — if records arrive but
that field is empty, the application is emitting plain text and `ROADMAP_JSON_LOGGING`
has not taken effect.

### Monitoring to set up afterwards

Carried over from [SECURITY_LOGGING.md](SECURITY_LOGGING.md) §7. The first one is
required by the control:

| Alert | Condition |
|---|---|
| **Data source gap** | No `roadmap` records for 15 minutes while the service is running. The control requires detecting loss of log delivery. |
| Admin route abuse | Any `action="authentication" result="failure"`, or `action="authorization" reason="not-internal"`. |
| Authorization denial spike | Sustained rise in `action="authorization" error_code=403` for one `user` or `src_ip`. |
| Authorization service failure | Any `action="authorization" level="error"`. |
| Broad data access | One `user` raising `data.access` across an unusual number of distinct `org_id` values. |

Cribl sits between the collector and Sumo Logic, so the gap alert covers two hops at
once: a Cribl routing rule that stops matching looks identical to a collector that has
stopped sending. Worth knowing when one fires.

---

## 10. Open items

- [x] **Ingest credential** — `Int_DRM-001` token received and **verified working**
      against `splunk-hec.corp.redhat.com` on 2026-10-21.
- [x] **Identify the protocol** — Cribl HEC, not Sumo Logic's native HTTP source.
- [x] **Confirm the endpoint** — `https://splunk-hec.corp.redhat.com:8088`. Internal
      only, by design; the public LB is not a fallback.
- [x] **Resolve the CA bundle** — operator-injected via the `roadmap-trusted-ca`
      ConfigMap, so it needs nothing from app-sre (§4).
- [ ] **Confirm the probe landed in Sumo Logic.** A 200 from Cribl means accepted at
      that hop, not delivered. Search for marker `roadmap-hec-verify-1792609226`.
- [x] **Ship `ROADMAP_JSON_LOGGING`** in `deploy/config.yml` — set to `"true"` for both
      workloads. A hard prerequisite: without it the `parse` filter has nothing to
      parse (§5).
- [ ] **Verify the injected trust bundle carries the internal CA** once the ConfigMap
      exists — command in §4.
- [ ] **Confirm whether a production token exists.** `Int_` suggests `Int_DRM-001` is
      integration/stage only (§3).
- [ ] **Confirm Cribl does not route on `sourcetype`.** It will receive `_json`, not
      the `fluentd` the token was provisioned with, and that cannot be changed without
      also setting `payloadKey` (§3).
- [ ] **Confirm Cribl's routing rule** for `rh_DRM-001` actually delivers to Sumo Logic,
      and what retention it lands under.
- [ ] **Raise the app-interface MR** adding this service's output and pipeline to
      `/setup/cluster-logging/clusterlogforwarder.yaml.j2` on `crcp01ue1` (§1).
- [ ] **Measure production request rate** for the ingest estimate (§7).
- [ ] **Confirm the Rover/LDAP group** that should receive access (§8).
- [ ] **Set up the data source gap alert** (§9) — this is what satisfies the control's
      loss-of-delivery requirement.

---

## 11. References

| | |
|---|---|
| `ClusterLogForwarder` API | [`api/observability/v1`](https://github.com/openshift/cluster-logging-operator/tree/master/api/observability/v1) and the shipped [CRD schema](https://github.com/openshift/cluster-logging-operator/blob/master/bundle/manifests/observability.openshift.io_clusterlogforwarders.yaml) — authoritative; the docs lag it |
| Splunk output behaviour | [`internal/generator/vector/output/splunk/`](https://github.com/openshift/cluster-logging-operator/tree/master/internal/generator/vector/output/splunk) — the `.toml` fixtures show exactly what Vector config each CR produces |
| Red Hat docs | [Configuring log forwarding, Logging 6.x](https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.2/html/configuring_logging/configuring-log-forwarding) |
| Third-party CLF 6.0 examples | `gitlab.cee.redhat.com/aosqe/aosqe-tools/-/tree/master/logging/log_doc/clf-6.0-examples` (Red Hat internal) — most likely place to find a vetted HEC example |
| Tuning payloads and delivery | [KCS 7074148](https://access.redhat.com/solutions/7074148) |
| Vector troubleshooting | [KCS 7089751](https://access.redhat.com/articles/7089751) |
| Logging 5 → 6 migration | [KCS 7089860](https://access.redhat.com/articles/7089860) |
