#!/system/bin/sh
# Termux MCP 公共函数
TMCP_MODDIR="${TMCP_MODDIR:-${0%/*}}"
TMCP_INTERNAL_DIR="/data/adb/termux-mcp"
TMCP_RUN_DIR="$TMCP_INTERNAL_DIR/run"
TMCP_LOG_DIR="$TMCP_INTERNAL_DIR/logs"
TMCP_PID_FILE="$TMCP_RUN_DIR/server.pid"
TMCP_PORT="5323"
TMCP_ADDRESS_FILE="$TMCP_INTERNAL_DIR/MCP地址.txt"
TMCP_PY="/data/data/com.termux/files/usr/bin/python3"

PATH="/data/adb/magisk:/data/adb/ksu/bin:/data/adb/ap/bin:/system/bin:/system/xbin:/vendor/bin:$PATH"
export PATH

tmcp_print() { printf '%s\n' "$*"; }

tmcp_prepare() {
  umask 077
  mkdir -p "$TMCP_INTERNAL_DIR" "$TMCP_RUN_DIR" "$TMCP_LOG_DIR" 2>/dev/null || return 1
  chown 0:0 "$TMCP_LOG_DIR" 2>/dev/null || true
  chmod 0700 "$TMCP_INTERNAL_DIR" "$TMCP_RUN_DIR" "$TMCP_LOG_DIR" 2>/dev/null || true
}

tmcp_write_address() {
  tmcp_prepare || return 1
  tmp="$TMCP_ADDRESS_FILE.tmp.$$"
  umask 022
  printf '本机地址：http://127.0.0.1:%s/mcp\n' "$TMCP_PORT" > "$tmp" || return 1
  chmod 0644 "$tmp" 2>/dev/null || true
  mv -f "$tmp" "$TMCP_ADDRESS_FILE"
}

tmcp_read_pid() {
  [ -r "$TMCP_PID_FILE" ] || return 1
  IFS= read -r p < "$TMCP_PID_FILE" || return 1
  case "$p" in ''|*[!0-9]*|0) return 1;; esac
  tmcp_print "$p"
}

tmcp_running() {
  p="$(tmcp_read_pid 2>/dev/null)"
  [ -n "$p" ] || return 1
  kill -0 "$p" 2>/dev/null
}


tmcp_start() {
  tmcp_prepare || { tmcp_print "无法创建运行目录"; return 1; }
  [ -x "$TMCP_PY" ] || { tmcp_print "Termux Python 不存在：$TMCP_PY"; return 1; }
  if tmcp_running; then
    tmcp_print "服务已运行，PID=$(tmcp_read_pid)"
    return 0
  fi
  rm -f "$TMCP_PID_FILE"
  export TMCP_SERVER_DIR="$TMCP_MODDIR"
  export TMCP_PORT="$TMCP_PORT"
  nohup "$TMCP_PY" "$TMCP_MODDIR/bin/mcp_server.py" \
    >> "$TMCP_LOG_DIR/server.log" 2>&1 < /dev/null &
  pid=$!
  printf '%s\n' "$pid" > "$TMCP_PID_FILE" 2>/dev/null || { kill -TERM "$pid" 2>/dev/null; return 1; }
  chmod 0600 "$TMCP_PID_FILE" 2>/dev/null || true
  tmcp_print "服务启动请求已提交，PID=$pid"
}

tmcp_stop() {
  p="$(tmcp_read_pid 2>/dev/null)"
  if [ -z "$p" ]; then
    rm -f "$TMCP_PID_FILE"
    tmcp_print "服务未运行"
    return 0
  fi
  kill -TERM "$p" 2>/dev/null || true
  n=0
  while [ "$n" -lt 10 ]; do
    kill -0 "$p" 2>/dev/null || { rm -f "$TMCP_PID_FILE"; tmcp_print "服务已停止"; return 0; }
    sleep 1; n=$((n+1))
  done
  kill -KILL "$p" 2>/dev/null || true
  rm -f "$TMCP_PID_FILE"
  tmcp_print "服务已强制停止"
}

tmcp_status() {
  if tmcp_running; then
    tmcp_print "服务状态：运行中（PID=$(tmcp_read_pid)）"
  else
    tmcp_print "服务状态：未运行"
  fi
  tmcp_print "MCP 地址：http://127.0.0.1:$TMCP_PORT/mcp"
}
