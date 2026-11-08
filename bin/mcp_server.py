#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Termux MCP 服务端
纯标准库实现 MCP streamable_http（SSE 响应），以 root 运行。
工具：Termux 命令执行、文件操作、屏幕操作（input/uiautomator）。
"""
import json, os, re, subprocess, threading, uuid, time, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("TMCP_PORT", "5323"))
HOST = "127.0.0.1"

TERMUX_PREFIX = "/data/data/com.termux/files/usr"
TERMUX_HOME = "/data/data/com.termux/files/home"
# 仅当调用方不传 cwd 时的中性兜底；模块本身不规定任何路径约定
DEFAULT_WORKDIR = "/sdcard/termuxAi"

# ---------------- 环境 ----------------
def termux_env(cwd=None):
    e = {
        "PATH": TERMUX_PREFIX + "/bin:" + TERMUX_PREFIX + "/bin/applets:/system/bin:/system/xbin:/sbin:/vendor/bin",
        "PREFIX": TERMUX_PREFIX,
        "HOME": TERMUX_HOME,
        "TMPDIR": TERMUX_PREFIX + "/tmp",
        "LD_LIBRARY_PATH": TERMUX_PREFIX + "/lib",
        "LD_PRELOAD": TERMUX_PREFIX + "/lib/libtermux-exec.so",
        "LANG": "en_US.UTF-8",
        "TERM": "xterm-256color",
    }
    if cwd:
        e["PWD"] = cwd
    return e

def run(cmd, cwd=None, timeout=300, shell=True):
    try:
        p = subprocess.run(cmd, shell=shell, cwd=cwd, env=termux_env(cwd),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, text=True, errors="replace")
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "命令超时（%ds）" % timeout
    except Exception as ex:
        return 127, "", "执行异常: %s" % ex

def run_root(cmd, timeout=60):
    return run(cmd, cwd="/data/local/tmp", timeout=timeout)

def trunc(s, n=200000):
    s = s or ""
    return s if len(s) <= n else s[:n] + "\n...[截断 %d 字符]" % (len(s) - n)

# ---------------- 屏幕操作（input/uiautomator，不依赖无障碍服务）----------------
def a11y_tap(x, y):
    rc, so, se = run_root("input tap %s %s" % (x, y))
    return "tap(%s,%s) rc=%d" % (x, y, rc) + ("" if not se else "\n" + se.strip())

def a11y_swipe(x1, y1, x2, y2, dur=300):
    rc, so, se = run_root("input swipe %s %s %s %s %s" % (x1, y1, x2, y2, dur))
    return "swipe(%s,%s)->(%s,%s) rc=%d" % (x1, y1, x2, y2, rc) + ("" if not se else "\n" + se.strip())

def a11y_key(keycode):
    if re.fullmatch(r"\d+", str(keycode)):
        k = str(keycode)
    else:
        m = {"home":3,"back":4,"power":26,"menu":82,"recents":187,"enter":66,"esc":111,"tab":61,"del":67,
             "space":62,"up":19,"down":20,"left":21,"right":22,"volup":24,"voldown":25}
        k = str(m.get(str(keycode).lower(), 0))
        if k == "0":
            return "未知按键: %s（可用: home/back/power/enter/esc/tab/del/space/up/down/left/right/volup/voldown 或数字keycode）" % keycode
    rc, so, se = run_root("input keyevent %s" % k)
    return "keyevent(%s) rc=%d" % (k, rc) + ("" if not se else "\n" + se.strip())

def a11y_text(text):
    if all(ord(ch) < 128 for ch in text):
        rc, so, se = run_root("input text '%s'" % text.replace("'", "\\'"))
        return "text 已输入 rc=%d" % rc
    return "文本含非 ASCII 字符，input text 仅支持 ASCII；中文输入请走其他通道"


# ---------------- Termux 工具 ----------------
def termux_exec(command, cwd=None, timeout=300):
    rc, so, se = run(command, cwd=(cwd or DEFAULT_WORKDIR), timeout=timeout)
    return "exit=%d\n--- stdout ---\n%s\n--- stderr ---\n%s" % (rc, trunc(so), trunc(se))

def file_read(path, max_bytes=200000):
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes + 1)
        if len(data) > max_bytes:
            return "文件过大（>%d 字节），仅读前 %d 字节\n%s" % (max_bytes, max_bytes, data[:max_bytes].decode("utf-8", "replace"))
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return "二进制文件（%d 字节），hex 前 2048 字节：\n%s" % (len(data), data[:2048].hex())
    except Exception as ex:
        return "读取失败: %s" % ex

def file_write(path, content, append=False):
    try:
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)
        if path.startswith("/data/data/com.termux"):
            subprocess.run(["restorecon", "-R", path], capture_output=True, timeout=30)
        return "已写入 %s（%d 字符）" % (path, len(content))
    except Exception as ex:
        return "写入失败: %s" % ex

def file_list(path, recursive=False):
    out = []
    if recursive:
        for root, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    sz = os.path.getsize(fp)
                except OSError:
                    sz = -1
                out.append("%s\t%d" % (fp, sz))
    else:
        try:
            for n in sorted(os.listdir(path)):
                fp = os.path.join(path, n)
                t = "d" if os.path.isdir(fp) else "f"
                try:
                    sz = os.path.getsize(fp) if t == "f" else -1
                except OSError:
                    sz = -1
                out.append("%s\t%s\t%d" % (n, t, sz))
        except Exception as ex:
            return "列目录失败: %s" % ex
    return "\n".join(out) if out else "(空)"

def termux_restorecon(path):
    rc, so, se = run_root("restorecon -R %s 2>&1" % path)
    return "restorecon -R %s rc=%d\n%s" % (path, rc, (so + se).strip())

# ---------------- 工具定义 ----------------
TOOLS = [
    {"name": "termux_exec", "description": "在 Termux 环境执行任意命令（PATH 指向 Termux prefix，可用 apktool/jadx/python/node/npm/gradle/clang/git 等）。返回 exit 码、stdout、stderr。",
     "inputSchema": {"type": "object", "properties": {
        "command": {"type": "string", "description": "要执行的 shell 命令"},
        "cwd": {"type": "string", "description": "工作目录，默认 /data/local/tmp"},
        "timeout": {"type": "integer", "description": "超时秒数，默认 300"}},
        "required": ["command"]}},
    {"name": "termux_read_file", "description": "读取文件内容（自动区分文本/二进制）。",
     "inputSchema": {"type": "object", "properties": {
        "path": {"type": "string"},
        "max_bytes": {"type": "integer", "description": "最大字节数，默认 200000"}},
        "required": ["path"]}},
    {"name": "termux_write_file", "description": "写入文件（自动创建父目录，写入 termux 私有目录时自动 restorecon 修复 SELinux）。",
     "inputSchema": {"type": "object", "properties": {
        "path": {"type": "string"},
        "content": {"type": "string"},
        "append": {"type": "boolean", "description": "追加模式，默认 false"}},
        "required": ["path", "content"]}},
    {"name": "termux_list_dir", "description": "列目录内容。",
     "inputSchema": {"type": "object", "properties": {
        "path": {"type": "string"},
        "recursive": {"type": "boolean", "description": "递归，默认 false"}},
        "required": ["path"]}},
    {"name": "termux_restorecon", "description": "对路径执行 restorecon -R 修复 SELinux 上下文（root 写 termux 文件后修复 MLS 类别用）。",
     "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "a11y_tap", "description": "点击屏幕坐标（input tap，root 直连，不依赖无障碍服务）。",
     "inputSchema": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]}},
    {"name": "a11y_swipe", "description": "屏幕滑动。",
     "inputSchema": {"type": "object", "properties": {"x1": {"type": "integer"}, "y1": {"type": "integer"}, "x2": {"type": "integer"}, "y2": {"type": "integer"}, "dur": {"type": "integer", "description": "毫秒，默认 300"}}, "required": ["x1", "y1", "x2", "y2"]}},
    {"name": "a11y_key", "description": "发送按键（home/back/power/enter/esc/tab/del/space/up/down/left/right/volup/voldown 或数字 keycode）。",
     "inputSchema": {"type": "object", "properties": {"keycode": {"type": "string"}}, "required": ["keycode"]}},
    {"name": "a11y_text", "description": "输入文本（仅 ASCII）。",
     "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
]

SERVER_INFO = {"name": "termux-mcp", "title": "Termux MCP + 屏幕操作", "version": "0.02"}

def dispatch(method, params):
    if method == "termux_exec":
        return termux_exec(params.get("command",""), params.get("cwd"), int(params.get("timeout",300)))
    if method == "termux_read_file":
        return file_read(params.get("path",""), int(params.get("max_bytes",200000)))
    if method == "termux_write_file":
        return file_write(params.get("path",""), params.get("content",""), bool(params.get("append",False)))
    if method == "termux_list_dir":
        return file_list(params.get("path",""), bool(params.get("recursive",False)))
    if method == "termux_restorecon":
        return termux_restorecon(params.get("path",""))
    if method == "a11y_tap":
        return a11y_tap(int(params["x"]), int(params["y"]))
    if method == "a11y_swipe":
        return a11y_swipe(int(params["x1"]), int(params["y1"]), int(params["x2"]), int(params["y2"]), int(params.get("dur",300)))
    if method == "a11y_key":
        return a11y_key(params.get("keycode",""))
    if method == "a11y_text":
        return a11y_text(params.get("text",""))
    return "未知工具: %s" % method

# ---------------- MCP 协议处理 ----------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass

    def _sse(self, obj):
        body = ("event: message\ndata: %s\n\n" % json.dumps(obj, ensure_ascii=False)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Mcp-Session-Id", uuid.uuid4().hex[:32].upper())
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") == "/mcp":
            self.send_response(405); self.send_header("Content-Length", "0"); self.end_headers()
        else:
            self.send_response(404); self.send_header("Content-Length","0"); self.end_headers()

    def do_POST(self):
        if self.path.rstrip("/") != "/mcp":
            self.send_response(404); self.send_header("Content-Length","0"); self.end_headers(); return
        ln = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(ln) if ln else b""
        try:
            req = json.loads(raw.decode("utf-8"))
        except Exception:
            self._sse({"jsonrpc":"2.0","id":None,"error":{"code":-32700,"message":"Parse error"}})
            return
        rid = req.get("id")
        method = req.get("method")
        if method == "initialize":
            result = {
                "protocolVersion": req.get("params",{}).get("protocolVersion","2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
                "instructions": "Termux 工具 + 屏幕操作。执行命令用 termux_exec；操作屏幕用 a11y_tap/swipe/key/text。路径由调用方自行决定。破坏性操作前先确认。",
            }
            self._sse({"jsonrpc":"2.0","id":rid,"result":result})
        elif method == "notifications/initialized":
            self.send_response(202); self.send_header("Content-Length","0"); self.end_headers()
        elif method == "tools/list":
            self._sse({"jsonrpc":"2.0","id":rid,"result":{"tools":TOOLS}})
        elif method == "tools/call":
            name = req.get("params",{}).get("name")
            args = req.get("params",{}).get("arguments",{}) or {}
            try:
                txt = dispatch(name, args)
                self._sse({"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":txt}],"isError":False}})
            except Exception as ex:
                self._sse({"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":"工具执行异常: %s" % ex}],"isError":True}})
        elif method == "ping":
            self._sse({"jsonrpc":"2.0","id":rid,"result":{}})
        else:
            self._sse({"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":"Method not found: %s" % method}})

def main():
    try:
        if not os.path.isdir(DEFAULT_WORKDIR):
            os.makedirs(DEFAULT_WORKDIR, exist_ok=True)
    except Exception:
        pass
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    sys.stderr.write("Termux MCP listening on http://%s:%s/mcp\n" % (HOST, PORT))
    srv.serve_forever()

if __name__ == "__main__":
    main()
