"""Entry point: schedules scrapers and produces to Kafka with rate limiting."""
from __future__ import annotations

import argparse
import asyncio
import json
import signal
from dataclasses import asdict
from typing import Any

import yaml

from src.common.config import get_settings
from src.common.logging import configure_logging, get_logger
from src.producers.kafka_producer import NewsKafkaProducer
from src.scrapers.base import SourceConfig
from src.scrapers.factory import NewsSourceFactory

logger = get_logger(__name__)


class NewsScheduler:
    """Manages async polling tasks and rate limiting."""

    def __init__(self, config_path: str) -> None:
        with open(config_path, encoding="utf-8") as fh:
            self.cfg = yaml.safe_load(fh)

        self.sources_cfg = self.cfg["sources"]
        scraping = self.cfg.get("scraping", {})
        self.extra = {
            "timeout": scraping.get("http_timeout", 20),
            "user_agent": scraping.get("user_agent", "NewsRAGBot"),
        }
        
        # Rate limiting semaphore (requests per second across all sources)
        rps = scraping.get("rate_limit_rps", 1)
        self.rate_limiter = asyncio.Semaphore(rps)
        
        # Graceful shutdown event
        self.shutdown_event = asyncio.Event()

    def _handle_signal(self, signum: int, frame: Any) -> None:
        logger.info("shutdown_signal_received", signal=signum)
        self.shutdown_event.set()

    async def poll_source(self, sc: dict, producer: NewsKafkaProducer) -> None:
        """Polls a single source, respects rate limits, and produces to Kafka."""
        config = SourceConfig(
            id=sc["id"],
            type=sc["type"],
            url=sc["url"],
            schedule_cron=sc.get("schedule_cron", "*/5 * * * *"),
            language=sc.get("language", "en"),
            tags=sc.get("tags", []),
            extra=self.extra,
        )
        source = NewsSourceFactory.create(config)

        while not self.shutdown_event.is_set():
            async with self.rate_limiter:
                try:
                    logger.info("fetching_source", source=config.id, url=config.url)
                    items = await source.fetch()
                    
                    produced = 0
                    for item in items:
                        # Use URL as Kafka key for proper partitioning and deduplication
                        payload = json.dumps(asdict(item)).encode("utf-8")
                        key = item.url.encode("utf-8")
                        await producer.send(value=payload, key=key)
                        produced += 1
                        
                    logger.info("produced_items", source=config.id, count=produced)
                except Exception as exc:
                    logger.error("scrape_failed", source=config.id, error=str(exc))

            # Poll every 60 seconds for simplicity in this daemon.
            # In a production app, parse schedule_cron here.
            try:
                await asyncio.wait_for(self.shutdown_event.wait(), timeout=60.0)
            except asyncio.TimeoutError:
                pass # Timeout means it's time to poll again

        if hasattr(source, "close"):
            await source.close()

    async def run(self) -> None:
        settings = get_settings()
        configure_logging(settings.log_level)

        # Register signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_signal, sig, None)

        producer = NewsKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            topic=settings.kafka_news_topic,
        )
        await producer.start()

        tasks = [
            asyncio.create_task(self.poll_source(sc, producer))
            for sc in self.sources_cfg
        ]

        logger.info("scheduler_started", sources_count=len(tasks))
        await self.shutdown_event.wait()

        logger.info("waiting_for_tasks_to_cancel")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        await producer.stop()
        logger.info("scheduler_stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the News Scraping Producer")
    parser.add_argument("--config", default="configs/scrapers/sources.yaml")
    args = parser.parse_args()
    
    scheduler = NewsScheduler(args.config)
    asyncio.run(scheduler.run())


if __name__ == "__main__":
    main()
