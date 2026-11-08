#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh"
tmcp_stop >/dev/null 2>&1 || true
rm -rf /data/adb/termux-mcp
echo "已停止 Termux MCP 服务并清理状态"
exit 0
