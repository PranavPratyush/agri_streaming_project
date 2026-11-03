# AgriKafka-Agent: PySpark 3.5.3 Structured Streaming Container
# Reference: docs/decisions/ADR-0001-runtime-spark-python-matrix.md
# Runtime: Python 3.11, OpenJDK 17, Spark 3.5.3 on Linux

FROM apache/spark:3.5.3-python3

USER root

WORKDIR /app

# Copy event contracts and stream processor modules
COPY packages/event-contracts /app/packages/event-contracts
COPY services/stream-processor /app/services/stream-processor

# Install python runtime dependencies
RUN pip install --no-cache-dir "pydantic>=2.7.0" "pandas>=2.0.0" "eval_type_backport"

# Prepare spark user ivy cache directories
RUN mkdir -p /home/spark/.ivy2/cache /home/spark/.ivy2/jars /opt/spark/checkpoints \
    && chown -R spark:spark /home/spark /opt/spark/checkpoints

# Set PYTHONPATH to discover packages
ENV PYTHONPATH="/app/packages/event-contracts/src:/app/services/stream-processor/src:${PYTHONPATH}"

# Revert to non-root spark user for security
USER spark

WORKDIR /opt/spark

ENTRYPOINT ["/opt/spark/bin/spark-submit"]
CMD [ \
    "--master", "local[*]", \
    "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3", \
    "--conf", "spark.sql.session.timeZone=UTC", \
    "/app/services/stream-processor/src/agri_stream_processor/app.py", \
    "--mode", "run", \
    "--bootstrap-servers", "kafka:29092", \
    "--checkpoint-dir", "/opt/spark/checkpoints" \
]
