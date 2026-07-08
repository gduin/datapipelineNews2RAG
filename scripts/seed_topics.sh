#!/usr/bin/env bash
set -euo pipefail
BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-localhost:29092}"
for t in news.raw news.embedded news.dlq; do
  docker exec kafka-1 kafka-topics --bootstrap-server "$BOOTSTRAP" \
    --create --if-not-exists --topic "$t" --partitions 12 --replication-factor 3
done
echo "Topics ready."
