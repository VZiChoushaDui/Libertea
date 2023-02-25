#!/bin/bash

version=`cat version.txt`

# build {image} and push it to libertea:{image}:version on docker hub

# ./haproxy
echo " *** Building and pushing libertea/haproxy:$version *** "
docker build -t libertea/haproxy:$version ./haproxy
docker push libertea/haproxy:$version

# ./syslog
echo " *** Building and pushing libertea/syslog:$version *** "
docker build -t libertea/syslog:$version ./syslog
docker push libertea/syslog:$version

# ./log-parser
echo " *** Building and pushing libertea/log-parser:$version *** "
docker build -t libertea/log-parser:$version ./log-parser
docker push libertea/log-parser:$version

# providers/trojan-ws
echo " *** Building and pushing libertea/provider-trojan-ws:$version *** "
docker build -t libertea/provider-trojan-ws:$version ./providers/trojan-ws
docker push libertea/provider-trojan-ws:$version

# providers/vless-ws
echo " *** Building and pushing libertea/provider-vless-ws:$version *** "
docker build -t libertea/provider-vless-ws:$version ./providers/vless-ws
docker push libertea/provider-vless-ws:$version

# providers/vmess-ws
echo " *** Building and pushing libertea/provider-vmess-ws:$version *** "
docker build -t libertea/provider-vmess-ws:$version ./providers/vmess-ws
docker push libertea/provider-vmess-ws:$version

# providers/shadowsocks-v2ray
echo " *** Building and pushing libertea/provider-shadowsocks-v2ray:$version *** "
docker build -t libertea/provider-shadowsocks-v2ray:$version ./providers/shadowsocks-v2ray
docker push libertea/provider-shadowsocks-v2ray:$version

# ./proxy-register
echo " *** Building and pushing libertea/proxy-register:$version *** "
docker build -t libertea/proxy-register:$version ./proxy-register
docker push libertea/proxy-register:$version

# ./proxy-haproxy
echo " *** Building and pushing libertea/proxy-haproxy:$version *** "
docker build -t libertea/proxy-haproxy:$version ./proxy-haproxy
docker push libertea/proxy-haproxy:$version

# ./proxy-fake-traffic
echo " *** Building and pushing libertea/proxy-fake-traffic:$version *** "
docker build -t libertea/proxy-fake-traffic:$version ./proxy-fake-traffic
docker push libertea/proxy-fake-traffic:$version

# add latest tag to all images
docker tag libertea/haproxy:$version libertea/haproxy:latest
docker tag libertea/syslog:$version libertea/syslog:latest
docker tag libertea/log-parser:$version libertea/log-parser:latest
docker tag libertea/provider-trojan-ws:$version libertea/provider-trojan-ws:latest
docker tag libertea/provider-vless-ws:$version libertea/provider-vless-ws:latest
docker tag libertea/provider-vmess-ws:$version libertea/provider-vmess-ws:latest
docker tag libertea/provider-shadowsocks-v2ray:$version libertea/provider-shadowsocks-v2ray:latest
docker tag libertea/proxy-register:$version libertea/proxy-register:latest
docker tag libertea/proxy-haproxy:$version libertea/proxy-haproxy:latest
docker tag libertea/proxy-fake-traffic:$version libertea/proxy-fake-traffic:latest

docker push libertea/haproxy:latest
docker push libertea/syslog:latest
docker push libertea/log-parser:latest
docker push libertea/provider-trojan-ws:latest
docker push libertea/provider-vless-ws:latest
docker push libertea/provider-vmess-ws:latest
docker push libertea/provider-shadowsocks-v2ray:latest
docker push libertea/proxy-register:latest
docker push libertea/proxy-haproxy:latest
docker push libertea/proxy-fake-traffic:latest

