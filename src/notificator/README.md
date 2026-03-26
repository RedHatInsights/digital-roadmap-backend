# Insights Planning: Notificator
## Local development
You can run notificator using `make run-notificator`. Kafka server is
needed for receiving messages - use `make start-kafka` (automatically creates expected
topic) or `make stop-kafka`.

To observe notifications on the kafka server, run:
```
podman exec -it roadmap-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic platform.notifications.ingress
```
when this runs you can run the notificator.
