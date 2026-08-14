ARG DOCKER_REGISTRY=
FROM ${DOCKER_REGISTRY}teddysun/xray:latest
ARG ALPINE_MIRROR=
RUN if [ -n "$ALPINE_MIRROR" ]; then ver=$(cut -d. -f1,2 /etc/alpine-release); printf '%s\n' "${ALPINE_MIRROR}/v${ver}/main" "${ALPINE_MIRROR}/v${ver}/community" > /etc/apk/repositories; fi

RUN apk update && apk add iptables

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
