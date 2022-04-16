FROM haproxy:2.7

USER root

RUN apt-get update
RUN apt-get install libcap2-bin -y
RUN setcap 'cap_net_bind_service=+ep' /usr/local/sbin/haproxy

# RUN mkdir -p /home/haproxy_stats
# RUN chown -R haproxy:haproxy /home/haproxy_stats
