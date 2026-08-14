ARG DOCKER_REGISTRY=
FROM ${DOCKER_REGISTRY}python:3.10-alpine
ARG ALPINE_MIRROR=
RUN if [ -n "$ALPINE_MIRROR" ]; then ver=$(cut -d. -f1,2 /etc/alpine-release); printf '%s\n' "${ALPINE_MIRROR}/v${ver}/main" "${ALPINE_MIRROR}/v${ver}/community" > /etc/apk/repositories; fi

RUN apk add --no-cache bash

WORKDIR /app
COPY . .

ENTRYPOINT ["bash", "run.sh"]
