#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh"
tmcp_prepare >/dev/null 2>&1 || true
tmcp_write_address >/dev/null 2>&1 || true
echo "Termux MCP"
echo "端口：5323"
echo "地址：http://127.0.0.1:5323/mcp"
tmcp_status
exit 0
