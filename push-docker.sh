#!/bin/bash

set -e

version=`cat version.txt`

# build {image} and push it to libertea:{image}:version on docker hub

# ./haproxy
echo " *** Building and pushing liberteamarron/haproxy:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/haproxy:$version ./haproxy --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/haproxy:latest ./haproxy --push

# ./syslog
echo " *** Building and pushing liberteamarron/syslog:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/syslog:$version ./syslog --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/syslog:latest ./syslog --push

# ./log-parser
echo " *** Building and pushing liberteamarron/log-parser:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/log-parser:$version ./log-parser --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/log-parser:latest ./log-parser --push

# providers/trojan-ws
echo " *** Building and pushing liberteamarron/provider-trojan-ws:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-trojan-ws:$version ./providers/trojan-ws --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-trojan-ws:latest ./providers/trojan-ws --push

# providers/trojan-grpc
echo " *** Building and pushing liberteamarron/provider-trojan-grpc:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-trojan-grpc:$version ./providers/trojan-grpc --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-trojan-grpc:latest ./providers/trojan-grpc --push

# providers/vless-ws
echo " *** Building and pushing liberteamarron/provider-vless-ws:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-vless-ws:$version ./providers/vless-ws --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-vless-ws:latest ./providers/vless-ws --push

# providers/vless-grpc
echo " *** Building and pushing liberteamarron/provider-vless-grpc:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-vless-grpc:$version ./providers/vless-grpc --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-vless-grpc:latest ./providers/vless-grpc --push

# providers/vmess-ws
echo " *** Building and pushing liberteamarron/provider-vmess-ws:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-vmess-ws:$version ./providers/vmess-ws --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-vmess-ws:latest ./providers/vmess-ws --push

# providers/vmess-grpc
echo " *** Building and pushing liberteamarron/provider-vmess-grpc:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-vmess-grpc:$version ./providers/vmess-grpc --push
docker buildx build --platform linux/amd64,linux/arm64 -t libertea/provider-vmess-grpc:latest ./providers/vmess-grpc --push

# providers/shadowsocks-v2ray
echo " *** Building and pushing liberteamarron/provider-shadowsocks-v2ray:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-shadowsocks-v2ray:$version ./providers/shadowsocks-v2ray --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/provider-shadowsocks-v2ray:latest ./providers/shadowsocks-v2ray --push

# ./proxy-register
echo " *** Building and pushing liberteamarron/proxy-register:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/proxy-register:$version ./proxy-register --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/proxy-register:latest ./proxy-register --push

# ./proxy-haproxy
echo " *** Building and pushing liberteamarron/proxy-haproxy:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/proxy-haproxy:$version ./proxy-haproxy --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/proxy-haproxy:latest ./proxy-haproxy --push

# ./proxy-fake-traffic
echo " *** Building and pushing liberteamarron/proxy-fake-traffic:$version *** "
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/proxy-fake-traffic:$version ./proxy-fake-traffic --push
docker buildx build --platform linux/amd64,linux/arm64 -t liberteamarron/proxy-fake-traffic:latest ./proxy-fake-traffic --push
