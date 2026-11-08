# Termux MCP

让 AI（RikkaHub / Claude / 任意支持 MCP 的 Agent）直接调用 Termux 里的工具，**无需 Termux 在前台运行**。

以 Magisk / KernelSU / APatch 模块形式刷入，开机自启一个本地 MCP 服务。

## 特性

- **复用 Termux 环境**：直接调用 Termux 的 `$PREFIX/bin` 下所有工具（apktool / jadx / node / gradle / clang / git / python …），无需额外安装
- **模块极小**：仅一个 13KB 的 Python 脚本，复用 Termux 已装的 python，不含重复运行时
- **不依赖无障碍服务**：屏幕操作走 `input` 命令，root 直连
- **开机自启**：`setsid` 脱离进程组，等系统开机完成 + Termux 数据解锁后自动拉起

## 工具列表（9 个）

### Termux 工具

| 工具 | 说明 |
|---|---|
| `termux_exec` | 在 Termux 环境执行任意命令（核心，可调全部工具） |
| `termux_read_file` | 读取文件（自动区分文本/二进制） |
| `termux_write_file` | 写入文件（自动建父目录 + SELinux 修复） |
| `termux_list_dir` | 列目录 |
| `termux_restorecon` | 修复 SELinux 上下文 |

### 屏幕操作（input 直连，不依赖无障碍服务）

| 工具 | 说明 |
|---|---|
| `a11y_tap` | 点击坐标 |
| `a11y_swipe` | 滑动 |
| `a11y_key` | 按键（home/back/enter/…） |
| `a11y_text` | 输入文本（仅 ASCII） |

## 前置要求

- Android 设备已 root（Magisk / KernelSU / APatch）
- 已安装 Termux，并 `pkg install python`（服务用 Termux 的 python 解释器）

## 安装

1. 下载 `termux-mcp-v0.02.zip`
2. 在 root 管理器（Magisk/KernelSU/APatch）中刷入
3. 重启设备

## 连接

MCP 服务监听 `http://127.0.0.1:5323/mcp`（`streamable_http` 协议）。

在 RikkaHub 或任意 MCP 客户端中添加：

- 地址：`http://127.0.0.1:5323/mcp`
- 传输类型：`streamable_http`

地址文件（刷入后生成）：`/data/adb/termux-mcp/MCP地址.txt`

## 路径约定

模块本身**不强制**任何路径约定。调用 `termux_exec` 时：

- 传 `cwd` 参数 → 在指定目录执行
- 不传 → 兜底 `/sdcard/termuxAi`（自动创建）

## 已知限制

- 服务复用 Termux 的 python，开机后需等用户数据解密（CE 存储）才能启动，通常比纯 DE 区模块晚几秒
- 屏幕操作里的 `input text` 仅支持 ASCII，中文输入需走其他通道
- 部分 ROM（如 ColorOS）会强制关闭侧载 app 的无障碍服务，故本模块不依赖无障碍

## License

MIT
