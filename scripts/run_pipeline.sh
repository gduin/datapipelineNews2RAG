#!/usr/bin/env bash
set -euo pipefail
JOB_NAME="news-rag-pipeline"
ENTRY="src.pipeline.flink_job:main"
docker exec -it flink-jobmanager flink run \
  --python /opt/usr/lib/news_rag_pipeline/src/pipeline/flink_job.py \
  --parallelism 4 || echo "Submit the job jar/pyfile via Flink REST UI at :8082"
