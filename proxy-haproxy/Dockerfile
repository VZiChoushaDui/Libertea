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

RUN apt-get update
RUN apt-get install libcap2-bin -y
RUN setcap 'cap_net_bind_service=+ep' /usr/local/sbin/haproxy

# RUN mkdir -p /home/haproxy_stats
# RUN chown -R haproxy:haproxy /home/haproxy_stats
