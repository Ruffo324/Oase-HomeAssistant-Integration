ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.24
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-aiohttp
COPY run.py /run.py
# s6 exports SUPERVISOR_TOKEN only through with-contenv.
CMD ["/usr/bin/with-contenv", "python3", "/run.py"]
