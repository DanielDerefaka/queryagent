FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY queryagent/ queryagent/
RUN pip install --no-cache-dir -e .

COPY . .

# Default: run miner (override with docker-compose or CLI)
ENTRYPOINT ["python", "-m", "neurons.miner"]
