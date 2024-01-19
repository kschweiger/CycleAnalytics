FROM --platform=$BUILDPLATFORM python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /usr/src/app

RUN pip install pip -U

COPY requirements.txt /usr/src/app/

RUN pip install -r requirements.txt


RUN groupadd -r app
RUN useradd -r -g app app
RUN chown -R app:app /usr/src/app

USER app

COPY . /usr/src/app/

