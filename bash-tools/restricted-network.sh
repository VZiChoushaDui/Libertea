#!/bin/bash
# Iran / restricted-network helpers. Sourced by init.sh and init-proxy.sh.
# Do not run this file directly.

LIBERTEA_RESTRICTED_DNS_DROPIN="/etc/systemd/resolved.conf.d/libertea-restricted-dns.conf"
LIBERTEA_RESTRICTED_APT_BACKUP="/var/lib/libertea/apt-backup"
LIBERTEA_RESTRICTED_MARKER=".libertea.iran"

LIBERTEA_IR_DNS="78.157.42.101 217.218.155.155 217.218.127.127"
LIBERTEA_IR_APT_HOST="ir.archive.ubuntu.com"
LIBERTEA_IR_PIP_INDEX="https://package-mirror.liara.ir/repository/pypi/simple/"
LIBERTEA_IR_PIP_HOST="package-mirror.liara.ir"
LIBERTEA_IR_DOCKER_REGISTRY="docker.arvancloud.ir/"
LIBERTEA_IR_ALPINE_MIRROR="https://mirror.arvancloud.ir/alpine"
LIBERTEA_IR_UBUNTU_MIRROR="http://ir.archive.ubuntu.com/ubuntu"
LIBERTEA_IR_DEBIAN_MIRROR="https://mirror.arvancloud.ir/debian"

libertea_restricted_probe() {
    local url="$1"
    if command -v curl >/dev/null 2>&1; then
        curl -fsS --max-time 5 -o /dev/null "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget -q --timeout=5 --spider "$url"
    else
        return 1
    fi
}

# Ask the operator to confirm auto-detected Iran blackout mode.
# Returns 0 only if they type "iran". Reads /dev/tty so curl|bash still works.
libertea_restricted_prompt_autodetect() {
    echo " ** Public registries (GitHub / PyPI / Ubuntu) look unreachable."
    echo "    This may be an Iran / restricted-network environment."
    echo "    Type 'iran' to use Iran blackout install mode, or press Enter to skip."
    local reply=""
    if [ -r /dev/tty ]; then
        read -r reply < /dev/tty || true
    else
        read -r reply || true
    fi
    case "$reply" in
        iran|IRAN|Iran) return 0 ;;
        *)
            echo "    Skipping Iran blackout mode. Re-run with --iran-blackout if you need it."
            return 1
            ;;
    esac
}

libertea_restricted_singbox_ok() {
    local path="$1"
    [ -f "$path" ] || return 1
    chmod +x "$path" 2>/dev/null || true
    [ -x "$path" ] && "$path" version 2>/dev/null | grep -q "sing-box version 1.13.1"
}

# Refuse Iran blackout install when files that cannot be fetched from GitHub are missing.
# role: main (panel) or proxy. Proxy has no extra local binaries.
libertea_restricted_require_files() {
    local role="${1:-main}"
    if [ "$role" != "main" ]; then
        return 0
    fi
    local local_bin="${DIR:-.}/providers/outbound-direct/sing-box"
    local installed="/usr/local/bin/libertea-sing-box"
    if libertea_restricted_singbox_ok "$installed" || libertea_restricted_singbox_ok "$local_bin"; then
        return 0
    fi
    echo ""
    echo "ERROR: Iran blackout mode cannot download files from GitHub / PyPI."
    echo "Place the required files, then re-run with --iran-blackout:"
    echo ""
    echo "  Required:"
    echo "    ${DIR:-.}/providers/outbound-direct/sing-box"
    echo "      sing-box 1.13.1 for this CPU (x86_64/amd64 or aarch64/arm64)."
    echo "      GitHub: https://github.com/SagerNet/sing-box/releases/tag/v1.13.1"
    echo ""
    echo "  Optional:"
    echo "    ${DIR:-.}/certs/<domain>.pem"
    echo "      Combined PEM (full chain + private key) if Let's Encrypt is unreachable."
    echo ""
    exit 1
}

# True when public registries look dead. ir.archive is probed if possible, but a
# blackout often cannot resolve it until Iranian DNS is applied, so public-dead
# is enough to ask the operator (they can skip).
libertea_restricted_detect() {
    if libertea_restricted_probe "https://github.com" \
        || libertea_restricted_probe "https://pypi.org" \
        || libertea_restricted_probe "http://archive.ubuntu.com"; then
        return 1
    fi
    return 0
}

libertea_restricted_apply_apt() {
    mkdir -p "$LIBERTEA_RESTRICTED_APT_BACKUP"
    if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then
        if [ ! -f "$LIBERTEA_RESTRICTED_APT_BACKUP/ubuntu.sources" ]; then
            cp /etc/apt/sources.list.d/ubuntu.sources "$LIBERTEA_RESTRICTED_APT_BACKUP/ubuntu.sources"
        fi
        sed -i "s|http://[a-zA-Z0-9.-]*\\.ubuntu\\.com|http://${LIBERTEA_IR_APT_HOST}|g" /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null || true
        sed -i "s|https://[a-zA-Z0-9.-]*\\.ubuntu\\.com|http://${LIBERTEA_IR_APT_HOST}|g" /etc/apt/sources.list.d/ubuntu.sources 2>/dev/null || true
    fi
    if [ -f /etc/apt/sources.list ]; then
        if [ ! -f "$LIBERTEA_RESTRICTED_APT_BACKUP/sources.list" ]; then
            cp /etc/apt/sources.list "$LIBERTEA_RESTRICTED_APT_BACKUP/sources.list"
        fi
        sed -i "s|http://[a-zA-Z0-9.-]*\\.ubuntu\\.com|http://${LIBERTEA_IR_APT_HOST}|g" /etc/apt/sources.list 2>/dev/null || true
        sed -i "s|https://[a-zA-Z0-9.-]*\\.ubuntu\\.com|http://${LIBERTEA_IR_APT_HOST}|g" /etc/apt/sources.list 2>/dev/null || true
    fi
}

libertea_restricted_restore_apt() {
    if [ -f "$LIBERTEA_RESTRICTED_APT_BACKUP/ubuntu.sources" ] && [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then
        cp "$LIBERTEA_RESTRICTED_APT_BACKUP/ubuntu.sources" /etc/apt/sources.list.d/ubuntu.sources
    fi
    if [ -f "$LIBERTEA_RESTRICTED_APT_BACKUP/sources.list" ] && [ -f /etc/apt/sources.list ]; then
        cp "$LIBERTEA_RESTRICTED_APT_BACKUP/sources.list" /etc/apt/sources.list
    fi
}

libertea_restricted_apply_dns() {
    mkdir -p /etc/systemd/resolved.conf.d
    cat > "$LIBERTEA_RESTRICTED_DNS_DROPIN" << EOF
[Resolve]
DNS=${LIBERTEA_IR_DNS}
EOF
    systemctl restart systemd-resolved 2>/dev/null || true
}

libertea_restricted_restore_dns() {
    if [ -f "$LIBERTEA_RESTRICTED_DNS_DROPIN" ]; then
        rm -f "$LIBERTEA_RESTRICTED_DNS_DROPIN"
        systemctl restart systemd-resolved 2>/dev/null || true
    fi
}

libertea_restricted_apply_pip() {
    export PIP_BREAK_SYSTEM_PACKAGES=1
    export PIP_INDEX_URL="$LIBERTEA_IR_PIP_INDEX"
    export PIP_TRUSTED_HOST="$LIBERTEA_IR_PIP_HOST"
}

# Apply host-side restricted-network settings and export build/compose variables.
libertea_restricted_apply() {
    echo " ** Iran blackout profile (--iran-blackout): using domestic apt, DNS, PyPI, and Docker mirrors"
    libertea_restricted_apply_dns
    libertea_restricted_apply_apt
    libertea_restricted_apply_pip
    export LIBERTEA_DOCKER_REGISTRY="$LIBERTEA_IR_DOCKER_REGISTRY"
    export LIBERTEA_ALPINE_MIRROR="$LIBERTEA_IR_ALPINE_MIRROR"
    export LIBERTEA_UBUNTU_MIRROR="$LIBERTEA_IR_UBUNTU_MIRROR"
    export LIBERTEA_DEBIAN_MIRROR="$LIBERTEA_IR_DEBIAN_MIRROR"
    if [ -n "${DIR:-}" ]; then
        touch "$DIR/$LIBERTEA_RESTRICTED_MARKER"
    fi
}

libertea_restricted_uninstall() {
    echo " ** Removing restricted-network apt/DNS overrides..."
    libertea_restricted_restore_apt
    libertea_restricted_restore_dns
    if [ -n "${DIR:-}" ]; then
        rm -f "$DIR/$LIBERTEA_RESTRICTED_MARKER"
    fi
}
