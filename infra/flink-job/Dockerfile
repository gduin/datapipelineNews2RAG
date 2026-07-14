
FROM flink:1.17.1-scala_2.12

# Install Python 3 and pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Create a symlink so 'python' points to 'python3'
RUN ln -s /usr/bin/python3 /usr/bin/python

# Install PyFlink, kafka-python, and new architectural dependencies
RUN pip3 install --no-cache-dir \
    apache-flink==1.17.1 \
    kafka-python \
    pydantic-settings \
    pydantic \
    structlog \
    pyyaml \
    pydantic-settings \
    beautifulsoup4 \
    lxml \
    feedparser \
    tenacity \
    qdrant-client \
    openai \
    pyyaml \
    structlog \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-exporter-otlp

# 1. Kafka Connector
RUN wget https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/1.17.1/flink-sql-connector-kafka-1.17.1.jar -P /opt/flink/lib/

# 2. Flink JDBC Connector
RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.2-1.17/flink-connector-jdbc-3.1.2-1.17.jar -P /opt/flink/lib/

# 3. PostgreSQL JDBC Driver
RUN wget https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.3/postgresql-42.7.3.jar -P /opt/flink/lib/



# FROM python:3.11-slim

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     default-jdk \
#     wget \
#     ca-certificates \
#     && rm -rf /var/lib/apt/lists/* \
#     && wget -q https://archive.apache.org/dist/flink/flink-1.18.1/flink-1.18.1-bin-scala_2.12.tgz -O /tmp/flink.tgz \
#     && tar -xzf /tmp/flink.tgz -C /opt \
#     && ln -s /opt/flink-1.18.1 /opt/flink \
#     && pip install --no-cache-dir \
#         sentence-transformers \
#     && wget -q https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/3.0.1-1.18/flink-connector-kafka-3.0.1-1.18.jar -O /opt/flink/lib/flink-connector-kafka.jar \
#     && wget -q https://repo1.maven.org/maven2/org/apache/flink/flink-clients_2.12/1.18.1/flink-clients_2.12-1.18.1.jar -O /opt/flink/lib/flink-clients.jar

ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="/opt/flink/bin:${PATH}"
ENV PYTHONPATH="/opt/flink-job:${PYTHONPATH}"

COPY src ./src
COPY configs ./configs
COPY pyproject.toml ./

CMD ["flink", "--help"]
