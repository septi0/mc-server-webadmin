ARG APP_DIR=/app

# ---------- Build stage ----------
FROM python:3.11-slim AS builder

ARG APP_DIR

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends python3-venv \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/mc-server-webadmin/

RUN python3 -m venv ${APP_DIR}/.venv && \
    ${APP_DIR}/.venv/bin/pip install --upgrade pip && \
    ${APP_DIR}/.venv/bin/pip install --upgrade /opt/mc-server-webadmin/ && \
    rm -rf /opt/mc-server-webadmin/

# ---------- Java stages ----------
FROM eclipse-temurin:8-jre AS jre8
FROM eclipse-temurin:17-jre AS jre17
FROM eclipse-temurin:21-jre AS jre21

# ---------- Runtime stage ----------
FROM python:3.11-slim AS runtime

ARG APP_DIR
ARG DATA_DIR=/data
ARG UID=1000
ARG GID=1000

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH=${APP_DIR}/.venv/bin:$PATH \
    APP_ENV=docker

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates tini && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY --from=jre8 /opt/java/openjdk/  /opt/java-8/
COPY --from=jre17 /opt/java/openjdk/  /opt/java-17/
COPY --from=jre21 /opt/java/openjdk/ /opt/java-21/

RUN ln -s /opt/java-8/bin/java /usr/local/bin/java-8 && \
    ln -s /opt/java-17/bin/java /usr/local/bin/java-17 && \
    ln -s /opt/java-21/bin/java /usr/local/bin/java-21

RUN addgroup --gid ${GID} mcadmin && \
    adduser --system --shell /bin/false --uid ${UID} --ingroup mcadmin --home ${DATA_DIR} mcadmin

COPY --from=builder --chown=mcadmin:mcadmin ${APP_DIR}/.venv ${APP_DIR}/.venv

USER mcadmin

WORKDIR ${DATA_DIR}

VOLUME ["/data"]

EXPOSE 25565 8000

ENTRYPOINT ["/usr/bin/tini","--","mc-server-webadmin"]

CMD []
