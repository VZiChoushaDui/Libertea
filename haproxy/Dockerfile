FROM haproxy:2.7

USER root

RUN apt-get update && apt-get install libcap2-bin -y && apt-get install lua-socket -y && apt-get install psmisc
RUN setcap 'cap_net_bind_service=+ep' /usr/local/sbin/haproxy

# RUN mkdir -p /home/haproxy_stats
# RUN chown -R haproxy:haproxy /home/haproxy_stats

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]