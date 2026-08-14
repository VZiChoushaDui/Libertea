ARG DOCKER_REGISTRY=
FROM ${DOCKER_REGISTRY}ubuntu:22.04
ARG ALPINE_MIRROR=
ARG UBUNTU_MIRROR=
RUN if [ -n "$UBUNTU_MIRROR" ]; then \
      find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -print0 2>/dev/null \
        | xargs -0 -r sed -i \
          -e "s|https://[a-zA-Z0-9.-]*\\.ubuntu\\.com/ubuntu|${UBUNTU_MIRROR}|g" \
          -e "s|http://[a-zA-Z0-9.-]*\\.ubuntu\\.com/ubuntu|${UBUNTU_MIRROR}|g"; \
    fi
RUN apt-get update && apt-get install rsyslog -y
RUN echo '$ModLoad imudp \n\
$UDPServerRun 514 \n\
$ModLoad imtcp \n\
$InputTCPServerRun 514 \n\
$template RemoteStore, "/var/log/log/event.log-%$year%%$Month%%$Day%-%$Hour%.log" \n\
:source, !isequal, "localhost" -?RemoteStore \n\
:source, isequal, "last" ~ ' > /etc/rsyslog.conf

ENTRYPOINT ["rsyslogd", "-n"]
