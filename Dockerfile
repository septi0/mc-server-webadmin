ARG APP_DIR=/app

# Build stage
FROM ubuntu:jammy AS builder

ARG APP_DIR

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/mc-server-webadmin/

RUN python3 -m venv ${APP_DIR} && \
    ${APP_DIR}/bin/pip install --upgrade pip && \
    ${APP_DIR}/bin/pip install --upgrade /opt/mc-server-webadmin/ && \
    rm -rf /opt/mc-server-webadmin/

# Runtime stage
FROM ubuntu:jammy

ARG APP_DIR
ARG DATA_DIR=/data
ARG UID=1000
ARG GID=1000

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=${APP_DIR}/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=docker

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tini \
    python3 \
    openjdk-8-jre-headless openjdk-17-jre-headless openjdk-21-jre-headless && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN ln -s /usr/lib/jvm/java-8-openjdk-amd64/bin/java /usr/local/bin/java-8 && \
    ln -s /usr/lib/jvm/java-17-openjdk-amd64/bin/java /usr/local/bin/java-17 && \
    ln -s /usr/lib/jvm/java-21-openjdk-amd64/bin/java /usr/local/bin/java-21

RUN addgroup --gid ${GID} mcadmin && \
    adduser --system --shell /bin/false --uid ${UID} --ingroup mcadmin --home ${DATA_DIR} mcadmin

COPY --from=builder --chown=mcadmin:mcadmin ${APP_DIR} ${APP_DIR}

USER mcadmin

WORKDIR ${DATA_DIR}

VOLUME ["/data"]

EXPOSE 25565 8000

ENTRYPOINT ["/usr/bin/tini","--","mc-server-webadmin","--data","/data"]

CMD []
