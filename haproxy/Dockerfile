FROM haproxy:2.5

USER root

RUN apt-get update && apt-get install libcap2-bin -y && apt-get install lua-socket -y
RUN setcap 'cap_net_bind_service=+ep' /usr/local/sbin/haproxy

# RUN mkdir -p /home/haproxy_stats
# RUN chown -R haproxy:haproxy /home/haproxy_stats
