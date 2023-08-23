#!/bin/bash

set -e

version=`cat version.txt`

# build {image} and push it to libertea:{image}:version on docker hub

# ./haproxy
echo " *** Building and pushing libertea-marron/haproxy:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/haproxy:$version ./haproxy --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/haproxy:latest ./haproxy --push

# ./syslog
echo " *** Building and pushing libertea-marron/syslog:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/syslog:$version ./syslog --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/syslog:latest ./syslog --push

# ./log-parser
echo " *** Building and pushing libertea-marron/log-parser:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/log-parser:$version ./log-parser --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/log-parser:latest ./log-parser --push

# providers/trojan-ws
echo " *** Building and pushing libertea-marron/provider-trojan-ws:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-trojan-ws:$version ./providers/trojan-ws --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-trojan-ws:latest ./providers/trojan-ws --push

# providers/trojan-grpc
echo " *** Building and pushing libertea-marron/provider-trojan-grpc:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-trojan-grpc:$version ./providers/trojan-grpc --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-trojan-grpc:latest ./providers/trojan-grpc --push

# providers/vless-ws
echo " *** Building and pushing libertea-marron/provider-vless-ws:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-vless-ws:$version ./providers/vless-ws --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-vless-ws:latest ./providers/vless-ws --push

# providers/vless-grpc
echo " *** Building and pushing libertea-marron/provider-vless-grpc:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-vless-grpc:$version ./providers/vless-grpc --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-vless-grpc:latest ./providers/vless-grpc --push

# providers/vmess-ws
echo " *** Building and pushing libertea-marron/provider-vmess-ws:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-vmess-ws:$version ./providers/vmess-ws --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-vmess-ws:latest ./providers/vmess-ws --push

# providers/vmess-grpc
echo " *** Building and pushing libertea-marron/provider-vmess-grpc:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-vmess-grpc:$version ./providers/vmess-grpc --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-vmess-grpc:latest ./providers/vmess-grpc --push

# providers/shadowsocks-v2ray
echo " *** Building and pushing libertea-marron/provider-shadowsocks-v2ray:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-shadowsocks-v2ray:$version ./providers/shadowsocks-v2ray --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/provider-shadowsocks-v2ray:latest ./providers/shadowsocks-v2ray --push

# ./proxy-register
echo " *** Building and pushing libertea-marron/proxy-register:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/proxy-register:$version ./proxy-register --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/proxy-register:latest ./proxy-register --push

# ./proxy-haproxy
echo " *** Building and pushing libertea-marron/proxy-haproxy:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/proxy-haproxy:$version ./proxy-haproxy --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/proxy-haproxy:latest ./proxy-haproxy --push

# ./proxy-fake-traffic
echo " *** Building and pushing libertea-marron/proxy-fake-traffic:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/proxy-fake-traffic:$version ./proxy-fake-traffic --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea-marron/proxy-fake-traffic:latest ./proxy-fake-traffic --push
