#!/system/bin/sh
MODDIR=${0%/*}
TMCP_MODDIR="$MODDIR"
. "$MODDIR/common.sh"
[ -e "$MODDIR/disable" ] && exit 0
[ -e "$MODDIR/remove" ] && exit 0

# setsid 完全脱离进程组（APatch 回收 service.sh 时不会连带杀掉）
setsid sh "$MODDIR/boot.sh" >/dev/null 2>&1 < /dev/null &
exit 0
