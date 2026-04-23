# Insights Planning: Notificator
## Local development
Preparing local env is needed, use:
```
make start-db load-host-inventory
```
Also do not forget set `ROADMAP_DEV=1` for setting local kafka and org_id.

You can run notificator using `make run-notificator`. Kafka server is
needed for receiving messages - use `make start-kafka` (automatically creates expected
topic) or `make stop-kafka`.

To observe notifications on the kafka server, run:
```
podman exec -it roadmap-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic platform.notifications.ingress
```
when this runs you can execute the notificator.

## Local development with fetching data org_ids from notification-backend
- you need to have user certificate, also the user certificate needs to be added into appropriate LDAP group.
- unsetting of `ROADMAP_DEV` env var requires manual configuration of kafka server, topic, path for certificates
```
ROADMAP_SUBSCRIPTIONS_URL=https://mtls.internal.cloud.stage.redhat.com/api/notifications-gw/notifications/subscriptions/rhel
ROADMAP_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
ROADMAP_KAFKA_NOTIFICATIONS_TOPIC=platform.notifications.ingress
ROADMAP_TLS_CERT_PATH=<path-to-user-certificate>
ROADMAP_TLS_KEY_PATH=<path-to-user-key>
make run-notificator
```
