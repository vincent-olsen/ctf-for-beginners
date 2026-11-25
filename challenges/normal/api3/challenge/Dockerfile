FROM python:3.13-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

ADD . /app
WORKDIR /app
RUN uv sync --locked

# Run unprivileged; the app files stay root's, so the app can't change them.
RUN useradd -m app
USER app

EXPOSE 5000

CMD ["uv", "run", "fastapi", "run", "app.py", "--port", "5000"]
