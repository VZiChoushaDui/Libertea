FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    curl \
    netcat \
    bc

COPY ./generate-traffic.sh /generate-traffic.sh

RUN chmod +x /generate-traffic.sh

ENTRYPOINT ["/bin/bash", "/generate-traffic.sh"]
