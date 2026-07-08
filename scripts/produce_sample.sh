#!/usr/bin/env bash
set -euo pipefail
BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-localhost:29092}"
docker exec -i kafka-1 kafka-console-producer --bootstrap-server "$BOOTSTRAP" \
  --topic news.raw <<JSON
{"source_id":"manual","url":"https://example.com/news/1","title":"Breaking","summary":"A big thing happened.","content":"Today something important occurred. Officials commented.","fetched_at":1700000000}
JSON
