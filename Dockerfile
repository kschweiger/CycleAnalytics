FROM python:3.10-bullseye

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV GIT_SSH_COMMAND "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"


RUN pip install pip==22.2.2

COPY requirements.txt /usr/src/app/

RUN --mount=type=ssh pip install -r requirements.txt

COPY . /usr/src/app/