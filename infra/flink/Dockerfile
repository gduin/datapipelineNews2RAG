FROM flink:1.18.1-java17

# Install Python (required for PyFlink UDFs on task managers) and PIP
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Install PyFlink and dependencies so that Python UDFs can execute on this node.
# Version MUST match the Flink cluster version (1.18.1).
COPY infra/flink-job/requirements.txt /opt/flink-job/requirements.txt
RUN pip install --no-cache-dir -r /opt/flink-job/requirements.txt

# Copy the project source so Python UDFs (e.g. ProcessFunction in src.pipeline.flink_job)
# can be unpickled by the Beam SDK harness worker running on this node.
# Without this, cloudpickle.loads() fails with ModuleNotFoundError: No module named 'src'.
COPY src/ /opt/flink-job/src/
ENV PYTHONPATH=/opt/flink-job

# Download Kafka connector JARs
# RUN wget -q https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.0.1-1.18/flink-sql-connector-kafka-3.0.1-1.18.jar -P /opt/flink/lib/ && \
#     wget -q https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.2-1.18/flink-connector-jdbc-3.1.2-1.18.jar -P /opt/flink/lib/ && \
#     wget -q https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.3/postgresql-42.7.3.jar -P /opt/flink/lib/

# 1. Kafka Connector (compatible with Flink 1.18.1)
RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.0.1-1.18/flink-sql-connector-kafka-3.0.1-1.18.jar -P /opt/flink/lib/

# 2. Flink JDBC Connector (compatible with Flink 1.18.1)
RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.2-1.18/flink-connector-jdbc-3.1.2-1.18.jar -P /opt/flink/lib/

# 3. PostgreSQL JDBC Driver
RUN wget https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.3/postgresql-42.7.3.jar -P /opt/flink/lib/

RUN wget https://repo1.maven.org/maven2/com/github/luben/zstd-jni/1.5.5-11/zstd-jni-1.5.5-11.jar -P /opt/flink/lib/
