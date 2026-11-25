FROM python:3.13-slim

ADD . /app
WORKDIR /app
RUN pip install --no-cache-dir "fastapi[standard]==0.143.0"

# Run unprivileged; the app files stay root's, so the app can't change them.
RUN useradd -m app
USER app

EXPOSE 5000

CMD ["fastapi", "run", "app.py", "--port", "5000"]
