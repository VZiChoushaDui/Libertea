ARG DOCKER_REGISTRY=
FROM ${DOCKER_REGISTRY}haproxy:2.7
ARG ALPINE_MIRROR=
ARG DEBIAN_MIRROR=
RUN if [ -n "$DEBIAN_MIRROR" ]; then \
      find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -print0 2>/dev/null \
        | xargs -0 -r sed -i \
          -e "s|https://deb.debian.org/debian|${DEBIAN_MIRROR}|g" \
          -e "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" \
          -e "s|https://security.debian.org/debian-security|${DEBIAN_MIRROR}-security|g" \
          -e "s|http://security.debian.org/debian-security|${DEBIAN_MIRROR}-security|g"; \
    fi

USER root

RUN apt-get update && apt-get install libcap2-bin -y && apt-get install lua-socket -y && apt-get install psmisc -y && apt-get install dnsutils -y
RUN setcap 'cap_net_bind_service=+ep' /usr/local/sbin/haproxy

# RUN mkdir -p /home/haproxy_stats
# RUN chown -R haproxy:haproxy /home/haproxy_stats

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
