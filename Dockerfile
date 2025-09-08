FROM eclipse-temurin:21-jre-jammy

ARG APP_DIR=/app
ARG UID=1000
ARG GID=1000

ENV APP_DIR=${APP_DIR} \
    PATH=${APP_DIR}/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --gid ${GID} mcadmin \
    && adduser --system --shell /bin/false --uid ${UID} --ingroup mcadmin --home /data mcadmin \
    && chown -R mcadmin:mcadmin /data

WORKDIR ${APP_DIR}

COPY --chown=mcadmin:mcadmin mcadmin ./mcadmin
COPY --chown=mcadmin:mcadmin README.md requirements.txt setup.py ./

RUN python3 -m venv .venv \
    && .venv/bin/pip install --upgrade pip \
    && .venv/bin/pip install --upgrade . \
    && chown -R mcadmin:mcadmin ${APP_DIR}

VOLUME ["/data"]

USER mcadmin

EXPOSE 25565 8000

ENTRYPOINT ["/usr/bin/tini","--","mc-server-webadmin","--data","/data"]
CMD []
