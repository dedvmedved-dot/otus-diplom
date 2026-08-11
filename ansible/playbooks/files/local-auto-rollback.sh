#!/bin/bash
# local-auto-rollback.sh — watchdog на узле ПАК
# Запускается ДО изменения bond0.
# Если валидация не подтверждена в течение WATCHDOG_TIMEOUT — автоматический откат.
#
# Использование:
#   ARM:    /usr/local/bin/local-auto-rollback.sh arm
#   VERIFY: /usr/local/bin/local-auto-rollback.sh verify  (если PASS — снимает watchdog)
#   CANCEL: /usr/local/bin/local-auto-rollback.sh cancel

BACKUP_DIR="/var/backups/pak-p1-network/rollback"
WATCHDOG_FLAG="/var/run/pak-p1-rollback-armed"
WATCHDOG_TIMEOUT=120  # секунд до авто-отката

arm_rollback() {
    mkdir -p "$BACKUP_DIR"
    chmod 700 "$BACKUP_DIR"

    # Сохраняем исходное состояние
    nmcli con show > "$BACKUP_DIR/nmcli-connections.txt"
    nmcli device status > "$BACKUP_DIR/nmcli-devices.txt"
    ip -br addr show > "$BACKUP_DIR/ip-addr.txt"
    ip route show > "$BACKUP_DIR/ip-route.txt"
    cat /proc/net/bonding/bond0 2>/dev/null > "$BACKUP_DIR/bond0-state.txt"

    # Сохраняем profile UUID для bond0, VLAN700
    nmcli -t -f NAME,UUID con show | grep -E "bond 1|Соединение VLAN 1" > "$BACKUP_DIR/critical-uuids.txt"

    echo "ROLLBACK_ARMED at $(date -u)" > "$WATCHDOG_FLAG"
    echo "Local rollback armed. Watchdog: ${WATCHDOG_TIMEOUT}s"

    # Запускаем фоновый watchdog
    (
        sleep "$WATCHDOG_TIMEOUT"
        if [ -f "$WATCHDOG_FLAG" ]; then
            logger -t pak-p1-rollback "WATCHDOG TIMEOUT — auto-rollback triggered"
            do_rollback
        fi
    ) &
}

do_rollback() {
    echo "=== AUTO-ROLLBACK at $(date -u) ===" >> "$BACKUP_DIR/rollback.log"

    # Вернуть bond0
    BOND0_UUID=$(grep "bond 1" "$BACKUP_DIR/critical-uuids.txt" 2>/dev/null | cut -d: -f2)
    VLAN700_UUID=$(grep "Соединение VLAN 1" "$BACKUP_DIR/critical-uuids.txt" 2>/dev/null | cut -d: -f2)

    # Down всё новое
    nmcli con down 'VLAN 140 Management' 2>/dev/null
    nmcli con down 'VLAN 141 DRBD' 2>/dev/null
    nmcli con down 'bond1 DRBD' 2>/dev/null

    # Up исходное
    nmcli con up uuid "$VLAN700_UUID" 2>/dev/null
    nmcli con up uuid "$BOND0_UUID" 2>/dev/null

    rm -f "$WATCHDOG_FLAG"
    echo "ROLLBACK COMPLETE" >> "$BACKUP_DIR/rollback.log"
}

verify_and_disarm() {
    # Проверки: bond0 UP, VLAN700 ping gateway
    if ! ip link show bond0 | grep -q "state UP"; then
        echo "bond0 NOT UP — rolling back"
        do_rollback
        exit 1
    fi
    if ! ping -c1 -W2 192.168.194.1 >/dev/null 2>&1; then
        echo "VLAN700 gateway unreachable — rolling back"
        do_rollback
        exit 1
    fi
    rm -f "$WATCHDOG_FLAG"
    echo "VALIDATION PASS — rollback disarmed"
}

case "${1:-}" in
    arm)    arm_rollback ;;
    verify) verify_and_disarm ;;
    cancel) rm -f "$WATCHDOG_FLAG"; echo "rollback cancelled" ;;
    *)      echo "Usage: $0 {arm|verify|cancel}" >&2; exit 1 ;;
esac
