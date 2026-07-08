"""Entry point: schedules scrapers and produces to Kafka."""
from __future__ import annotations

import argparse
import asyncio
import json
import yaml
from dataclasses import asdict

from src.common.config import get_settings
from src.common.logging import configure_logging, get_logger
from src.producers.kafka_producer import NewsKafkaProducer
from src.scrapers.base import SourceConfig
from src.scrapers.factory import NewsSourceFactory


async def run(config_path: str, once: bool = True) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger(__name__)

    with open(config_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    sources_cfg = cfg["sources"]
    scraping = cfg.get("scraping", {})
    extra = {
        "timeout": scraping.get("http_timeout", 30),
        "user_agent": scraping.get("user_agent", "NewsRAGBot"),
    }

    producer = NewsKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topic=settings.kafka_news_topic,
    )
    await producer.start()

    async def poll_source(sc: dict) -> None:
        config = SourceConfig(
            id=sc["id"], type=sc["type"], url=sc["url"],
            schedule_cron=sc.get("schedule_cron", "*/5 * * * *"),
            language=sc.get("language", "en"), tags=sc.get("tags", []),
            extra=extra,
        )
        source = NewsSourceFactory.create(config)
        items = await source.fetch()
        for item in items:
            await producer.send(json.dumps(asdict(item)).encode("utf-8"),
                                key=item.url.encode("utf-8"))
        logger.info("produced", source=config.id, count=len(items))

    try:
        if once:
            await asyncio.gather(*(poll_source(sc) for sc in sources_cfg))
        else:
            while True:
                await asyncio.gather(*(poll_source(sc) for sc in sources_cfg))
                await asyncio.sleep(60)
    finally:
        await producer.stop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/scrapers/sources.yaml")
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.config, once=not args.loop))


if __name__ == "__main__":
    main()
