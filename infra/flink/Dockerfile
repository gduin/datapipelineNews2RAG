FROM flink:1.18.1-java17

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
