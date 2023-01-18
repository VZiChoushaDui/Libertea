FROM mazy/ss-xray:latest

USER root

RUN apk update && apk add iptables

COPY entrypoint.sh /entrypoint.sh
COPY config.env /config.env

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
