"""Builder pattern for Flink stream topology."""
from __future__ import annotations

import json
from dataclasses import dataclass

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.connectors.kafka import KafkaSource
from pyflink.common import WatermarkStrategy

from src.common.logging import get_logger


@dataclass
class PipelineConfig:
    source_topic: str
    sink_topic: str
    group_id: str
    bootstrap: str
    parallelism: int = 4


class PipelineBuilder:
    """Builds the Flink DataStream pipeline."""

    def __init__(self, env: StreamExecutionEnvironment, config: PipelineConfig) -> None:
        self._env = env
        self._config = config
        self._logger = get_logger(__name__)

    def build(self):
        self._logger.info(
            "building_pipeline",
            source_topic=self._config.source_topic,
            bootstrap=self._config.bootstrap,
            parallelism=self._config.parallelism,
        )
        try:
            self._env.set_parallelism(self._config.parallelism)

            source = KafkaSource.builder() \
                .set_bootstrap_servers(self._config.bootstrap) \
                .set_topics(self._config.source_topic) \
                .set_group_id(self._config.group_id) \
                .set_value_only_deserializer(SimpleStringSchema()) \
                .build()
                #.set_value_only_deserializer(
                #     lambda bytes_: bytes_.decode('utf-8')
                #)

            stream = self._env.from_source(
                source, WatermarkStrategy.no_watermarks(), "news-source"
            )
            stream = self._env.from_source(
                source,
                WatermarkStrategy.no_watermarks(),
                "news-source",
            )

            parsed = stream.map(json.loads)
            stream.print("news-stream")
        except Exception:
            self._logger.critical("pipeline_build_failed", exc_info=True)
            raise

        self._logger.info(
            "pipeline_built",
            source_topic=self._config.source_topic,
        )
        return stream
