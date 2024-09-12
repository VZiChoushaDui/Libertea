#!/bin/bash

set -e

version=`cat version.txt`

# build {image} and push it to libertea:{image}:version on docker hub

# ./haproxy
echo " *** Building and pushing libertea/haproxy:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/haproxy:$version ./haproxy --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/haproxy:latest ./haproxy --push

# ./syslog
echo " *** Building and pushing libertea/syslog:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/syslog:$version ./syslog --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/syslog:latest ./syslog --push

# ./log-parser
echo " *** Building and pushing libertea/log-parser:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/log-parser:$version ./log-parser --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/log-parser:latest ./log-parser --push

# providers/trojan-ws
echo " *** Building and pushing libertea/provider-trojan-ws:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-trojan-ws:$version ./providers/trojan-ws --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-trojan-ws:latest ./providers/trojan-ws --push

# providers/trojan-grpc
echo " *** Building and pushing libertea/provider-trojan-grpc:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-trojan-grpc:$version ./providers/trojan-grpc --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-trojan-grpc:latest ./providers/trojan-grpc --push

# providers/vless-ws
echo " *** Building and pushing libertea/provider-vless-ws:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-vless-ws:$version ./providers/vless-ws --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-vless-ws:latest ./providers/vless-ws --push

# providers/vless-grpc
echo " *** Building and pushing libertea/provider-vless-grpc:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-vless-grpc:$version ./providers/vless-grpc --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-vless-grpc:latest ./providers/vless-grpc --push

# providers/vmess-grpc
echo " *** Building and pushing libertea/provider-vmess-grpc:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-vmess-grpc:$version ./providers/vmess-grpc --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-vmess-grpc:latest ./providers/vmess-grpc --push

# providers/shadowsocks-v2ray
echo " *** Building and pushing libertea/provider-shadowsocks-v2ray:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-shadowsocks-v2ray:$version ./providers/shadowsocks-v2ray --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-shadowsocks-v2ray:latest ./providers/shadowsocks-v2ray --push

# providers/provider-outbound-warp
echo " *** Building and pushing libertea/provider-outbound-warp:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-outbound-warp:$version ./providers/outbound-warp --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-outbound-warp:latest ./providers/outbound-warp --push

# providers/provider-outbound-direct
echo " *** Building and pushing libertea/provider-outbound-direct:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-outbound-direct:$version ./providers/outbound-direct --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-outbound-direct:latest ./providers/outbound-direct --push

# ./proxy-register
echo " *** Building and pushing libertea/proxy-register:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/proxy-register:$version ./proxy-register --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/proxy-register:latest ./proxy-register --push

# ./proxy-haproxy
echo " *** Building and pushing libertea/proxy-haproxy:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/proxy-haproxy:$version ./proxy-haproxy --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/proxy-haproxy:latest ./proxy-haproxy --push

# ./proxy-fake-traffic
echo " *** Building and pushing libertea/proxy-fake-traffic:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/proxy-fake-traffic:$version ./proxy-fake-traffic --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/proxy-fake-traffic:latest ./proxy-fake-traffic --push
