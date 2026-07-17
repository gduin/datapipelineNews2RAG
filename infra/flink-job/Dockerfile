# Example Dockerfile for your flink-job container
FROM flink:1.18.1-java17

# 1. Install python3, pip, and create python symlink
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

# 2. Download Kafka connector JARs
# RUN cd /opt/flink/lib && \
#     wget -q https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/1.17.1/flink-connector-kafka-1.17.1.jar && \
#     wget -q https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar

# 2.1. Kafka Connector (compatible with Flink 1.18.1)
RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.0.1-1.18/flink-sql-connector-kafka-3.0.1-1.18.jar -P /opt/flink/lib/

# 2.2. Flink JDBC Connector (compatible with Flink 1.18.1)
RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.2-1.18/flink-connector-jdbc-3.1.2-1.18.jar -P /opt/flink/lib/

# 2.3. PostgreSQL JDBC Driver
RUN wget https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.3/postgresql-42.7.3.jar -P /opt/flink/lib/

# 2.4. Create archive with connector JARs for upload to Flink cluster
RUN mkdir -p /opt/flink-job && python3 -c "import zipfile; z=zipfile.ZipFile('/opt/flink-job/connectors.jar', 'w'); import glob; [z.write(f) for f in glob.glob('/opt/flink/lib/flink-sql-connector-kafka-3.0.1-1.18.jar') + glob.glob('/opt/flink/lib/flink-connector-jdbc-3.1.2-1.18.jar') + glob.glob('/opt/flink/lib/postgresql-42.7.3.jar')]"


RUN wget https://repo1.maven.org/maven2/com/github/luben/zstd-jni/1.5.5-11/zstd-jni-1.5.5-11.jar -P /opt/flink/lib/

# 3. Copy your requirements file from your project root
COPY infra/flink-job/requirements.txt /opt/flink-job/requirements.txt

# 4. Install your Python dependencies globally inside the container
RUN pip install --no-cache-dir -r /opt/flink-job/requirements.txt

# 5. Copy your source code
COPY src/ /opt/flink-job/src/

# Set working directory
WORKDIR /opt/flink-job

# FROM flink:1.17.1-scala_2.12

# # Download the pure Java Kafka connector (no _2.12 in the name!)
# RUN cd /opt/flink/lib && \
#     wget -q https://repo1.maven.org/maven2/org/apache/flink/flink-connector-kafka/1.17.1/flink-connector-kafka-1.17.1.jar && \
#     wget -q https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar


# # Optional: Install Python dependencies if your flink job needs them
# RUN apt-get update && \
#     apt-get install -y python3 python3-pip && \
#     ln -s /usr/bin/python3 /usr/bin/python && \
#     rm -rf /var/lib/apt/lists/*

# WORKDIR /opt/flink/usrlib


# # Create a symlink so 'python' points to 'python3'
# RUN ln -s /usr/bin/python3 /usr/bin/python

# # Install PyFlink, kafka-python, and new architectural dependencies
# RUN pip3 install --no-cache-dir \
#     apache-flink==1.17.1 \
#     kafka-python \
#     pydantic-settings \
#     pydantic \
#     structlog \
#     pyyaml \
#     pydantic-settings \
#     beautifulsoup4 \
#     lxml \
#     feedparser \
#     tenacity \
#     qdrant-client \
#     openai \
#     pyyaml \
#     structlog \
#     opentelemetry-api \
#     opentelemetry-sdk \
#     opentelemetry-exporter-otlp

# # 1. Kafka Connector (new API with KafkaSource)
# RUN wget https://repo.maven.apache.org/maven2/org/apache/flink/flink-connector-kafka/3.0.1-1.17/flink-connector-kafka-3.0.1-1.17.jar -P /opt/flink/lib/ \
#     && wget https://repo.maven.apache.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar -P /opt/flink/lib/

# # 2. Flink JDBC Connector
# RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.2-1.17/flink-connector-jdbc-3.1.2-1.17.jar -P /opt/flink/lib/

# # 3. PostgreSQL JDBC Driver
# RUN wget https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.3/postgresql-42.7.3.jar -P /opt/flink/lib/



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

# COPY src ./src
# COPY configs ./configs
# COPY pyproject.toml ./

# CMD ["flink", "--help"]
# CMD ["bash"]