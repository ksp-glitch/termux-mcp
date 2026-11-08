#!/system/bin/sh
# 开机启动脚本：setsid 完全脱离 service.sh 进程组
MODDIR="${0%/*}"
TMCP_MODDIR="$MODDIR"
. "$MODDIR/common.sh"

# 等系统完全开机（最多 4 分钟）
n=0
while [ "$n" -lt 120 ]; do
  [ "$(getprop sys.boot_completed 2>/dev/null)" = "1" ] && break
  sleep 2
  n=$((n+1))
done

# 等 Termux Python 可用（FBE 数据解锁后才能访问，1 秒轮询尽快拉起服务）
n=0
while [ "$n" -lt 300 ]; do
  [ -x "/data/data/com.termux/files/usr/bin/python3" ] && break
  sleep 1
  n=$((n+1))
done

tmcp_start >/dev/null 2>&1
exit 0
