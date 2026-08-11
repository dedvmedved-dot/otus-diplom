#!/bin/bash
# local-auto-rollback.sh — watchdog на узле ПАК (v2 — systemd + profile restore)
# Запускается ДО изменения bond0.
# Если валидация не подтверждена — автоматический откат через systemd timer.
#
# Использование:
#   ARM:    /usr/local/bin/local-auto-rollback.sh arm
#   VERIFY: /usr/local/bin/local-auto-rollback.sh verify
#   CANCEL: /usr/local/bin/local-auto-rollback.sh cancel
#   STATUS: /usr/local/bin/local-auto-rollback.sh status

BACKUP_DIR="/var/backups/pak-p1-network/rollback"
TIMER_NAME="pak-p1-rollback.timer"
SERVICE_NAME="pak-p1-rollback.service"
WATCHDOG_SECONDS=120

log() { echo "[$(date -u +%T)] $*" | tee -a "$BACKUP_DIR/rollback.log"; }

arm_rollback() {
    mkdir -p "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR"

    # Сохраняем ИСХОДНЫЕ NM profile-файлы ДО изменения
    cp -a /etc/NetworkManager/system-connections/ "$BACKUP_DIR/nm-original/"
    chmod 700 "$BACKUP_DIR/nm-original"
    find "$BACKUP_DIR/nm-original" -type f -exec chmod 600 {} \;

    # Сохраняем состояние
    cat /proc/net/bonding/bond0 > "$BACKUP_DIR/bond0-state.txt" 2>/dev/null
    ip -br addr show > "$BACKUP_DIR/ip-addr.txt"
    ip route show > "$BACKUP_DIR/ip-route.txt"
    nmcli -t -f NAME,UUID con show --active > "$BACKUP_DIR/active-connections.txt"

    # Создаём systemd transient timer (независим от SSH)
    systemd-run --unit="$SERVICE_NAME" --on-active="${WATCHDOG_SECONDS}s" \
        --description="PAK P1 auto-rollback watchdog" \
        /bin/bash -c "
            if [ -f /var/backups/pak-p1-network/rollback/armed ]; then
                logger -t pak-p1-rollback 'WATCHDOG TIMEOUT — auto-rollback triggered'
                /usr/local/bin/local-auto-rollback.sh do_rollback
            fi
        " 2>/dev/null

    echo "armed $(date -u)" > "$BACKUP_DIR/armed"
    log "ROLLBACK ARMED — timer ${WATCHDOG_SECONDS}s"
}

do_rollback() {
    log "ROLLBACK START"

    # Deactivate failed config
    nmcli con down 'VLAN 140 Management' 2>/dev/null; true
    nmcli con down 'VLAN 141 DRBD' 2>/dev/null; true
    nmcli con down 'bond1 DRBD' 2>/dev/null; true
    nmcli con down 'Агрегированное соединение (bond) 1' 2>/dev/null; true

    # Restore original NM profiles
    if [ -d "$BACKUP_DIR/nm-original" ]; then
        rm -f /etc/NetworkManager/system-connections/bond*
        cp "$BACKUP_DIR/nm-original"/* /etc/NetworkManager/system-connections/ 2>/dev/null
        chown root:root /etc/NetworkManager/system-connections/*
        chmod 600 /etc/NetworkManager/system-connections/*
        nmcli connection reload
        log "Original NM profiles restored"
    fi

    # Activate original bond0
    nmcli con up 'Агрегированное соединение (bond) 1' 2>/dev/null
    sleep 2

    # Activate original VLAN700
    nmcli con up 'Соединение VLAN 1' 2>/dev/null

    rm -f "$BACKUP_DIR/armed"
    log "ROLLBACK COMPLETE"
}

verify_and_disarm() {
    local fails=0

    # Each check is a standalone condition, no piped command strings.

    if ip link show bond0 2>/dev/null | grep -q "state UP"; then
        log "VERIFY PASS: bond0 UP"
    else
        log "VERIFY FAIL: bond0 UP"
        fails=$((fails + 1))
    fi

    local slave_count
    slave_count=$(grep -c 'Slave Interface:' /proc/net/bonding/bond0 2>/dev/null || echo 0)
    local slaves_up
    slaves_up=$(grep -c 'MII Status: up' /proc/net/bonding/bond0 2>/dev/null || echo 0)
    if [ "$slave_count" -eq 2 ] && [ "$slaves_up" -eq 2 ]; then
        log "VERIFY PASS: bond0 slaves 2/2 UP"
    else
        log "VERIFY FAIL: bond0 slaves ${slave_count} total, ${slaves_up} UP"
        fails=$((fails + 1))
    fi

    if grep -q '802.3ad' /proc/net/bonding/bond0 2>/dev/null; then
        log "VERIFY PASS: bond0 802.3ad"
    else
        log "VERIFY FAIL: bond0 802.3ad"
        fails=$((fails + 1))
    fi

    local lacp_partner
    lacp_partner=$(grep -c 'Partner Churn State: monitoring' /proc/net/bonding/bond0 2>/dev/null || echo 0)
    if [ "$lacp_partner" -ge 1 ]; then
        log "VERIFY PASS: bond0 LACP partner present"
    else
        log "VERIFY FAIL: bond0 LACP partner missing"
        fails=$((fails + 1))
    fi

    if ip -br addr show bond0.700 2>/dev/null | grep -q "192.168.194"; then
        log "VERIFY PASS: VLAN700 IP present"
    else
        log "VERIFY FAIL: VLAN700 IP missing"
        fails=$((fails + 1))
    fi

    if ping -c1 -W2 192.168.194.1 >/dev/null 2>&1; then
        log "VERIFY PASS: VLAN700 gateway reachable"
    else
        log "VERIFY FAIL: VLAN700 gateway unreachable"
        fails=$((fails + 1))
    fi

    if ip -br addr show bond0.140 2>/dev/null | grep -q "172.30.140"; then
        log "VERIFY PASS: VLAN140 IP present"
    else
        log "VERIFY FAIL: VLAN140 IP missing"
        fails=$((fails + 1))
    fi

    if ip route show default 2>/dev/null | grep -q "192.168.194.1"; then
        log "VERIFY PASS: default route preserved"
    else
        log "VERIFY FAIL: default route missing"
        fails=$((fails + 1))
    fi

    if [ "$fails" -eq 0 ]; then
        rm -f "$BACKUP_DIR/armed"
        systemctl stop "$TIMER_NAME" "$SERVICE_NAME" 2>/dev/null || true
        log "ALL CHECKS PASS — rollback DISARMED"
    else
        log "$fails CHECKS FAILED — rolling back"
        do_rollback
        exit 1
    fi
}

cancel_rollback() {
    rm -f "$BACKUP_DIR/armed"
    systemctl stop "$TIMER_NAME" "$SERVICE_NAME" 2>/dev/null || true
    log "rollback cancelled"
}

case "${1:-}" in
    arm)        arm_rollback ;;
    verify)     verify_and_disarm ;;
    do_rollback) do_rollback ;;
    cancel)     cancel_rollback ;;
    status)
        if [ -f "$BACKUP_DIR/armed" ]; then
            echo "AUTO-ROLLBACK ARMED: YES"
            echo "Armed at: $(cat "$BACKUP_DIR/armed")"
        else
            echo "AUTO-ROLLBACK ARMED: NO"
        fi ;;
    *) echo "Usage: $0 {arm|verify|cancel|status}" >&2; exit 1 ;;
esac
