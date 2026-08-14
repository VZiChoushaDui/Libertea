#!/bin/bash

set -e

DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
ROOT_DIR="$( cd "$DIR/../.." >/dev/null 2>&1 ; pwd -P )"

# Config format is written for this exact release. Do not float to latest.
SINGBOX_VERSION="1.13.1"
BIN="/usr/local/bin/libertea-sing-box"

case "$(uname -m)" in
    x86_64|amd64) SINGBOX_ARCH="amd64" ;;
    aarch64|arm64) SINGBOX_ARCH="arm64" ;;
    *)
        echo "Unsupported architecture: $(uname -m) (need x86_64 or aarch64)"
        exit 1
        ;;
esac

need_download=1
if [ -x "$BIN" ]; then
    current="$("$BIN" version 2>/dev/null | head -n 1 || true)"
    if echo "$current" | grep -q "sing-box version ${SINGBOX_VERSION}"; then
        echo "    - sing-box ${SINGBOX_VERSION} already installed"
        need_download=0
    fi
fi

install_from_tarball() {
    local archive="$1"
    local tmp
    tmp="$(mktemp -d)"
    tar -xzf "$archive" -C "$tmp"
    install -m 755 "$tmp/sing-box-${SINGBOX_VERSION}-linux-${SINGBOX_ARCH}/sing-box" "$BIN"
    rm -rf "$tmp"
}

if [ "$need_download" = "1" ]; then
    echo "    - Downloading sing-box ${SINGBOX_VERSION} (${SINGBOX_ARCH})..."
    url="https://github.com/SagerNet/sing-box/releases/download/v${SINGBOX_VERSION}/sing-box-${SINGBOX_VERSION}-linux-${SINGBOX_ARCH}.tar.gz"
    tmp_archive="$(mktemp)"
    downloaded=0
    if command -v curl >/dev/null 2>&1; then
        if curl -fsSL "$url" -o "$tmp_archive"; then
            downloaded=1
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -qO "$tmp_archive" "$url"; then
            downloaded=1
        fi
    fi

    if [ "$downloaded" = "1" ]; then
        systemctl stop libertea-outbound-direct.service 2>/dev/null || true
        install_from_tarball "$tmp_archive"
        rm -f "$tmp_archive"
    else
        rm -f "$tmp_archive"
        if [ -x "$DIR/sing-box" ] && "$DIR/sing-box" version 2>/dev/null | grep -q "sing-box version ${SINGBOX_VERSION}"; then
            echo "    - Download failed; using local sing-box ${SINGBOX_VERSION}"
            systemctl stop libertea-outbound-direct.service 2>/dev/null || true
            install -m 755 "$DIR/sing-box" "$BIN"
        else
            echo "Failed to download sing-box ${SINGBOX_VERSION} for ${SINGBOX_ARCH}"
            exit 1
        fi
    fi
fi

mkdir -p "$ROOT_DIR/data"
if [ ! -f "$ROOT_DIR/data/outbound.json" ]; then
    # The panel rewrites this file on startup; it only has to carry traffic until
    # then, and to keep working if the panel never comes up. On a
    # restricted-network install that means following the host resolver instead of
    # a foreign DNS server that cannot be reached. Mirrors _local_dns_server() in
    # panel/panel/outbounds.py.
    if [ -f "$ROOT_DIR/.libertea.iran" ]; then
        bootstrap_dns='{ "type": "local", "tag": "dns-direct" },
      { "type": "local", "tag": "dns-vpn" }'
    else
        bootstrap_dns='{ "type": "udp", "tag": "dns-direct", "server": "8.8.8.8" },
      { "type": "udp", "tag": "dns-vpn", "server": "8.8.8.8" }'
    fi
    cat > "$ROOT_DIR/data/outbound.json" << EOF
{
  "log": { "level": "warn" },
  "dns": {
    "servers": [
      $bootstrap_dns
    ],
    "final": "dns-vpn",
    "strategy": "prefer_ipv4"
  },
  "inbounds": [
    { "type": "socks", "listen": "127.0.0.1", "listen_port": 13000, "tag": "socks-direct" }
  ],
  "outbounds": [
    { "type": "direct", "tag": "direct" },
    { "type": "block", "tag": "block" }
  ],
  "route": {
    "rules": [ { "inbound": ["socks-direct"], "outbound": "direct" } ],
    "final": "direct",
    "default_domain_resolver": "dns-direct"
  }
}
EOF
fi

echo "    - Installing systemd service..."
sed "s|{rootpath}|$ROOT_DIR|g" "$DIR/libertea-outbound-direct.service" > /etc/systemd/system/libertea-outbound-direct.service
systemctl daemon-reload
systemctl enable libertea-outbound-direct.service
systemctl restart libertea-outbound-direct.service
