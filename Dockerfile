# syntax=docker/dockerfile:1
FROM python:3.12-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
SHELL ["/bin/bash", "-c"]

WORKDIR /home/app/app

RUN groupadd -r app && useradd -r -g app app
RUN chown -R app:app /home/app
USER app
ENV PATH="/home/app/app/.venv/bin:$PATH"

ADD . .
RUN uv venv

RUN uv pip install -r requirements/prod.txt --no-deps && uv pip install -e . --no-deps


