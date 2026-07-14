"""Builder pattern for Flink stream topology."""
from __future__ import annotations

from dataclasses import dataclass

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaSink
from pyflink.datastream.formats.json import JsonRowDeserializationSchema
from pyflink.common import Types, WatermarkStrategy


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

    def build(self):
        self._env.set_parallelism(self._config.parallelism)

        source = KafkaSource.builder() \
            .set_bootstrap_servers(self._config.bootstrap) \
            .set_topics(self._config.source_topic) \
            .set_group_id(self._config.group_id) \
            .set_value_only_deserializer(
                JsonRowDeserializationSchema.builder() \
                .type_info(Types.ROW([Types.STRING()])) \
                .build()
            ).build()

        stream = self._env.from_source(
            source, WatermarkStrategy.no_watermarks(), "news-source"
        )

        stream.print("news-stream")
        return stream
