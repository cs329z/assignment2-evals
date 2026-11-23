# Starting environment for the ci-failure-chain task.
FROM python:3.12.16-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337

WORKDIR /app
COPY app/ /app/
RUN chmod +x /app/ci.sh
