FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/

ENV MCP_TRANSPORT=httpStream
ENV PORT=3000
EXPOSE 3000

CMD ["uv", "run", "--no-dev", "python", "-m", "src"]
