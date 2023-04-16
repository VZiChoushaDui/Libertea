FROM teddysun/xray:latest

RUN apk update && apk add iptables

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
