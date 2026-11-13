#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PruneMate 外部主机 TLS 网关（自举版）

首次启动会自动完成此前需要手动执行的两件事：
  - 生成自签 CA 与服务端证书（含本机全部 IPv4 到 SAN 里，客户端用哪个 IP 都能校验通过）
  - 生成 64 位随机访问令牌

之后不会再覆盖，容器重建 / 重启都沿用同一套（状态在 /state 卷里）。

职责：
  1. TLS 承接 PruneMate 的连接
  2. 校验访问令牌（除 /version 外一律要求 X-PruneMate-Token）
  3. 转发给上游 docker-socket-proxy（由它做接口白名单）
  4. 打印访问日志

只依赖 Python 标准库 + openssl 命令行。

用法：
  python gateway.py                 正常启动（首次自举）
  python gateway.py --show          打印当前客户端配置（不改动任何东西）
  python gateway.py --regen-token   重新生成访问令牌
  python gateway.py --regen-certs   重新生成 CA 与服务端证书（含 SAN）
  python gateway.py --regen-all     两者都重来

环境变量：
  UPSTREAM   上游地址，默认 unix:///var/run/docker.sock（也可 http://127.0.0.1:2375）
  ALLOW_VOLUMES 设为 1 才开放数据卷列举与清理，默认关闭
  STATE_DIR  状态目录，默认 /state
  EXTRA_HOSTS 额外要写进证书 SAN 的地址，逗号分隔（可选）
  PUBLIC_DIR 若设置，会把令牌/CA/接入说明写到这个目录，方便在界面上直接查看
  INFO_PORT  只读信息页端口，默认 2377。只暴露 CA（公开证书），不含令牌
  BIND / PORT 监听，默认 0.0.0.0:2376
"""

import fcntl
import http.client
import ipaddress
import os
import re
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

UPSTREAM = os.environ.get("UPSTREAM", "unix:///var/run/docker.sock")
STATE_DIR = os.environ.get("STATE_DIR", "/state")
CERT = os.path.join(STATE_DIR, "server.crt")
KEY = os.path.join(STATE_DIR, "server.key")
CA = os.path.join(STATE_DIR, "ca.crt")
TOKEN_FILE = os.path.join(STATE_DIR, "token")
BIND = os.environ.get("BIND", "0.0.0.0")
PORT = int(os.environ.get("PORT", "2376"))
INFO_PORT = int(os.environ.get("INFO_PORT", "2377"))
EXTRA_HOSTS = [h.strip() for h in (os.environ.get("EXTRA_HOSTS") or "").split(",") if h.strip()]

_u = urlsplit(UPSTREAM)
UNIX_SOCK = _u.path if _u.scheme == "unix" else ""
UP_HOST = _u.hostname or "127.0.0.1"
UP_PORT = _u.port or 80


class UnixHTTPConnection(http.client.HTTPConnection):
    """直连 Docker 的 unix socket，省掉中间的 TCP 代理容器"""

    def __init__(self, sock_path, timeout=120):
        super().__init__("localhost", timeout=timeout)
        self._sock_path = sock_path

    def connect(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        s.connect(self._sock_path)
        self.sock = s

HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}

TOKEN = ""


def log(msg):
    print(msg, flush=True)


def local_ipv4():
    """枚举本机所有 IPv4（容器用 host 网络时即为宿主机地址）"""
    ips = set()
    for _idx, name in socket.if_nameindex():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            packed = fcntl.ioctl(s.fileno(), 0x8915,  # SIOCGIFADDR
                                 struct.pack("256s", name[:15].encode()))
            s.close()
            ips.add(socket.inet_ntoa(packed[20:24]))
        except OSError:
            continue
    return sorted(ips)


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ensure_token():
    if os.path.exists(TOKEN_FILE) and os.path.getsize(TOKEN_FILE) > 0:
        return open(TOKEN_FILE).read().strip()
    tok = subprocess.run(["openssl", "rand", "-hex", "32"], check=True,
                         capture_output=True, text=True).stdout.strip()
    with open(TOKEN_FILE, "w") as f:
        f.write(tok + "\n")
    os.chmod(TOKEN_FILE, 0o600)
    log("已生成访问令牌 -> %s" % TOKEN_FILE)
    return tok


def ensure_certs():
    if os.path.exists(CERT) and os.path.exists(KEY) and os.path.exists(CA):
        return
    os.makedirs(STATE_DIR, exist_ok=True)

    hosts = list(local_ipv4()) + EXTRA_HOSTS
    san = []
    for h in hosts:
        try:
            ipaddress.ip_address(h)
            san.append("IP:" + h)
        except ValueError:
            san.append("DNS:" + h)
    if not san:
        san = ["DNS:localhost"]
    # 回环也带上，方便本机自测
    for extra in ("IP:127.0.0.1", "DNS:localhost"):
        if extra not in san:
            san.append(extra)

    log("首次启动，正在生成自签证书（SAN: %s）" % ", ".join(san))
    ck = os.path.join(STATE_DIR, "ca.key")
    sk = os.path.join(STATE_DIR, "server.key")
    csr = os.path.join(STATE_DIR, "server.csr")
    ext = os.path.join(STATE_DIR, "server.ext")

    run(["openssl", "genrsa", "-out", ck, "4096"])
    run(["openssl", "req", "-x509", "-new", "-nodes", "-key", ck, "-sha256",
         "-days", "3650", "-subj", "/CN=PruneMate Local CA", "-out", CA])
    run(["openssl", "genrsa", "-out", sk, "2048"])
    run(["openssl", "req", "-new", "-key", sk, "-subj", "/CN=prunemate-gateway", "-out", csr])
    with open(ext, "w") as f:
        f.write("subjectAltName = %s\n" % ",".join(san))
        f.write("basicConstraints = CA:FALSE\n")
        f.write("keyUsage = digitalSignature, keyEncipherment\n")
        f.write("extendedKeyUsage = serverAuth\n")
    run(["openssl", "x509", "-req", "-in", csr, "-CA", CA, "-CAkey", ck,
         "-CAcreateserial", "-out", CERT, "-days", "3650", "-sha256", "-extfile", ext])
    for p in (csr, ext):
        try:
            os.remove(p)
        except OSError:
            pass
    os.chmod(ck, 0o600)
    os.chmod(sk, 0o600)
    log("证书已生成 -> %s" % CERT)


# 只放行 PruneMate 实际调用的端点；按「方法 + 路径」限制，
# 刻意不按容器 ID 放行——危险的是 /containers/{id}/* 生命周期动作。
ALLOW_RULES = [
    (("GET",),  r"^(/v[\d\.]+)?/_ping$"),
    (("GET",),  r"^(/v[\d\.]+)?/version$"),
    (("GET",),  r"^(/v[\d\.]+)?/containers/json"),
    (("GET",),  r"^(/v[\d\.]+)?/containers/[^/]+/json$"),   # 部分 docker-py 路径会 inspect
    (("GET",),  r"^(/v[\d\.]+)?/images/json"),
    (("GET",),  r"^(/v[\d\.]+)?/images/[^/]+/json$"),   # docker-py 列镜像时会取详情
    (("GET",),  r"^(/v[\d\.]+)?/networks$"),
    (("GET",),  r"^(/v[\d\.]+)?/system/df$"),
    (("POST",), r"^(/v[\d\.]+)?/containers/prune$"),
    (("POST",), r"^(/v[\d\.]+)?/images/prune$"),
    (("POST",), r"^(/v[\d\.]+)?/networks/prune$"),
    (("POST",), r"^(/v[\d\.]+)?/build/prune$"),
]

# 数据卷清理默认不开放，需要时设 ALLOW_VOLUMES=1
_VOLUME_RULES = [
    (("GET",),  r"^(/v[\d\.]+)?/volumes$"),
    (("POST",), r"^(/v[\d\.]+)?/volumes/prune$"),
]
if (os.environ.get("ALLOW_VOLUMES") or "").strip().lower() in ("1", "true", "yes"):
    ALLOW_RULES = ALLOW_RULES + _VOLUME_RULES


def is_allowed(method, raw_path):
    path = urlsplit(raw_path).path
    for methods, pattern in ALLOW_RULES:
        if method in methods and re.match(pattern, path):
            return True
    return False


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "prunemate-tls-gateway"

    def log_message(self, fmt, *args):
        pass

    def _deny(self, reason="missing or invalid X-PruneMate-Token"):
        msg = ("403 Forbidden: %s\n" % reason).encode()
        self.send_response(403)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)

    def _proxy(self, method):
        path = self.path
        # 版本协商放行：docker 客户端初始化时会先探测，这时还没带上自定义头
        needs_token = not path.rstrip("/").endswith("/version") and path.rstrip("/") != "/version"
        _given = re.sub(r"\s+", "", self.headers.get("X-PruneMate-Token", "") or "")
        if needs_token and _given != TOKEN:
            log("%s %s %s -> 403 令牌无效" % (self.client_address[0], method, path))
            self._deny("missing or invalid X-PruneMate-Token")
            return

        if not is_allowed(method, path):
            log("%s %s %s -> 403 不在白名单" % (self.client_address[0], method, path))
            self._deny("path not allowed: %s %s" % (method, urlsplit(path).path))
            return

        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        headers["X-Forwarded-For"] = self.client_address[0]
        headers["X-Forwarded-Proto"] = "https"

        if UNIX_SOCK:
            conn = UnixHTTPConnection(UNIX_SOCK, timeout=120)
        else:
            conn = http.client.HTTPConnection(UP_HOST, UP_PORT, timeout=120)
        try:
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            self.send_response(resp.status, resp.reason)
            for k, v in resp.getheaders():
                if k.lower() not in HOP and k.lower() != "content-length":
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(data)
            log("%s %s %s -> %d" % (self.client_address[0], method, path, resp.status))
        except Exception as exc:
            log("%s %s %s -> 502 %s" % (self.client_address[0], method, path, exc))
            self.send_error(502, "upstream unavailable")
        finally:
            conn.close()

    def do_GET(self):
        self._proxy("GET")

    def do_HEAD(self):
        self._proxy("HEAD")

    def do_POST(self):
        self._proxy("POST")

    def do_PUT(self):
        self._proxy("PUT")

    def do_DELETE(self):
        self._proxy("DELETE")


def start_info_server():
    """只读信息页：提供 CA 下载与接入说明。

    刻意只放 CA（公开证书材料），**不暴露令牌**——令牌仍需从容器日志或 public/ 取。
    """
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as _Srv

    class InfoHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            pass

        def _send(self, code, ctype, body):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.startswith("/ca.crt"):
                try:
                    with open(CA) as f:
                        self._send(200, "application/x-x509-ca-cert", f.read())
                except Exception:
                    self._send(404, "text/plain; charset=utf-8", "CA 尚未生成")
                return
            if self.path in ("/", "/index.html"):
                ips = [i for i in local_ipv4()
                       if not i.startswith(("127.", "172.", "10.200.", "169.254."))]
                rows = "".join("<li>https://%s:%d</li>" % (ip, PORT) for ip in ips)
                html = """<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>PruneMate 网关</title>
<style>body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;max-width:640px;margin:40px auto;
padding:0 20px;color:#0f172a;line-height:1.7}code{background:#f1f5f9;padding:2px 6px;border-radius:4px}
h1{font-size:1.3rem}.box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:16px 0}
a.btn{display:inline-block;background:#0284c7;color:#fff;padding:10px 18px;border-radius:999px;
text-decoration:none;font-weight:600}</style>
<h1>PruneMate 网关</h1>
<div style="border:2px solid #dc2626;background:#fef2f2;border-radius:12px;padding:14px 18px;
color:#b91c1c;margin:16px 0;line-height:1.8;font-size:0.92rem">
<b>⚠️ 安全警示</b><br>
· 本机 2376 端口等价于该主机的<b>容器层 root</b>，只能在内网使用，不要做端口转发或公网映射。<br>
· 若 PruneMate 只管理本机，<b>不需要安装本网关</b>。<br>
· 本页只提供 CA（公开证书），不显示令牌。
</div>
<div class="box">
<p><b>1. 下载 CA 证书</b>（PruneMate 侧的「外部主机 CA 证书」就贴这个）</p>
<p><a class="btn" href="/ca.crt">下载 ca.crt</a></p>
</div>
<div class="box">
<p><b>2. 访问令牌</b></p>
<p>出于安全考虑，本页<b>不显示令牌</b>。请从以下位置获取：</p>
<ul>
<li>容器日志：<code>docker logs prunemate-gateway</code> 开头那段</li>
<li>应用目录：<code>docker/public/token.txt</code></li>
<li>命令：<code>docker exec prunemate-gateway python /app/gateway.py --show</code></li>
</ul>
</div>
<div class="box">
<p><b>3. 在 PruneMate 里填的地址</b></p>
<ul>%s</ul>
</div></html>""" % rows
                self._send(200, "text/html; charset=utf-8", html)
                return
            self._send(404, "text/plain; charset=utf-8", "not found")

    try:
        srv = _Srv(("0.0.0.0", INFO_PORT), InfoHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        log("只读信息页：http://<本机IP>:%d/ （仅提供 CA 下载，不含令牌）" % INFO_PORT)
    except Exception as exc:
        log("信息页启动失败（端口 %d 可能被占用）：%s" % (INFO_PORT, exc))


def print_client_config(show_token=True):
    """打印客户端要用的配置；只读，不改动任何状态。

    show_token=False 时只打印令牌位置提示，不输出令牌本身（用于启动日志）。
    CA 是公开证书材料，始终打印。
    """
    ips = [i for i in local_ipv4()
           if not i.startswith(("127.", "172.", "10.200.", "169.254."))]
    log("")
    log("================ 客户端配置 ================")
    if ips:
        for ip in ips[:6]:
            log("  主机地址: https://%s:%d" % (ip, PORT))
    else:
        log("  主机地址: https://<本机IP>:%d" % PORT)
    if show_token:
        log("")
        log("  ---- 访问令牌（整段复制这一行）----")
        log("  " + TOKEN)
        log("  ---- 令牌结束 ----")
    else:
        log("  访问令牌: 已隐藏（容器内执行 --show 查看，或看 public/token.txt）")
    log("  （令牌填到 PruneMate 主机的「访问令牌」输入框）")
    log("")
    log("  ---- CA 证书（整段复制，贴到 PruneMate 的「外部主机 CA 证书」）----")
    try:
        with open(CA) as _f:
            for _line in _f.read().strip().splitlines():
                log("  " + _line)
    except Exception:
        log("  （CA 尚未生成）")
    log("  ---- CA 结束 ----")
    log("===========================================")
    log("")


def regen(what):
    """重新生成密钥材料。what: token | certs | all"""
    removed = []
    if what in ("token", "all"):
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            removed.append("token")
    if what in ("certs", "all"):
        for name in ("server.crt", "server.key", "ca.crt", "ca.key",
                     "ca.srl", "server.csr", "server.ext"):
            path = os.path.join(STATE_DIR, name)
            if os.path.exists(path):
                os.remove(path)
        removed.append("certs")
    log("已清除: %s" % (", ".join(removed) or "无"))


def export_public():
    """把客户端接入信息写到 PUBLIC_DIR，方便没有 shell 的用户直接查看"""
    dirs = [d.strip() for d in
            (os.environ.get("PUBLIC_DIR", "") + "," + os.environ.get("PUBLIC_DIR_2", "")).split(",")
            if d.strip()]
    if not dirs:
        return
    for pub in dirs:
        _export_to(pub)


def _export_to(pub):
    try:
        os.makedirs(pub, exist_ok=True)
        ips = [i for i in local_ipv4()
               if not i.startswith(("127.", "172.", "10.200.", "169.254."))]
        lines = ["PruneMate 网关 — 客户端接入信息", "=" * 40, ""]
        lines.append("在 PruneMate 页面里填以下地址之一：")
        for ip in ips:
            lines.append("  https://%s:%d" % (ip, PORT))
        lines += ["", "访问令牌（整行复制，填到 PruneMate 主机的「访问令牌」）：",
                  "---- 令牌开始 ----", TOKEN, "---- 令牌结束 ----", ""]
        lines += ["CA 文件：同目录下的 ca.crt",
                  "  PruneMate 容器需要挂载它，并设置 REQUESTS_CA_BUNDLE=/certs/ca.crt", ""]
        with open(os.path.join(pub, "client-info.txt"), "w") as f:
            f.write("\n".join(lines) + "\n")
        with open(os.path.join(pub, "token.txt"), "w") as f:
            f.write(TOKEN + "\n")
        if os.path.exists(CA):
            with open(CA) as src, open(os.path.join(pub, "ca.crt"), "w") as dst:
                dst.write(src.read())
        log("接入信息已导出到 %s" % pub)
    except Exception as exc:
        log("导出到 %s 失败: %s" % (pub, exc))


def parse_args(argv):
    """返回 'serve' / 'show' / 'regen:<what>'"""
    if not argv:
        return "serve"
    if "--show" in argv:
        return "show"
    if "--regen-all" in argv:
        return "regen:all"
    if "--regen-token" in argv:
        return "regen:token"
    if "--regen-certs" in argv:
        return "regen:certs"
    log("未知参数: %s" % " ".join(argv))
    log("可用: --show | --regen-token | --regen-certs | --regen-all")
    sys.exit(2)


def main():
    global TOKEN
    os.makedirs(STATE_DIR, exist_ok=True)

    if not shutil.which("openssl"):
        log("镜像里缺少 openssl，无法自动生成证书")
        sys.exit(1)

    mode = parse_args(sys.argv[1:])

    if mode == "show":
        TOKEN = ensure_token() if os.path.exists(TOKEN_FILE) else ""
        if not TOKEN:
            log("尚未生成令牌，先正常启动一次")
            sys.exit(1)
        print_client_config()
        return

    if mode.startswith("regen:"):
        regen(mode.split(":", 1)[1])
        TOKEN = ensure_token()
        ensure_certs()
        export_public()
        print_client_config()
        log("完成。运行中的网关卡表要重建才会加载新证书/令牌：")
        log("  docker compose restart tls-gateway")
        return

    TOKEN = ensure_token()
    ensure_certs()
    export_public()

    # 启动日志默认打印令牌（方便没有 shell 的用户）；
    # 若日志会被外发/归档，设 HIDE_TOKEN_IN_LOG=1 只打印位置提示。
    _hide = (os.environ.get("HIDE_TOKEN_IN_LOG") or "").strip().lower() in ("1","true","yes")
    log("")
    log("================ 客户端配置 ================")
    log("  主机地址: https://<本机IP>:%d" % PORT)
    if _hide:
        log("  访问令牌: 已隐藏（HIDE_TOKEN_IN_LOG=1），见 public/token.txt 或 --show")
    else:
        log("")
    log("  ---- 访问令牌（整段复制这一行）----")
    log("  " + TOKEN)
    log("  ---- 令牌结束 ----")
    log("  （令牌填到 PruneMate 主机的「访问令牌」输入框）")
    log("")
    log("  ---- CA 证书（整段复制，贴到 PruneMate 的「外部主机 CA 证书」）----")
    try:
        with open(CA) as _f:
            for _line in _f.read().strip().splitlines():
                log("  " + _line)
    except Exception:
        log("  （CA 尚未生成）")
    log("  ---- CA 结束 ----")
    log("===========================================")
    log("")

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(CERT, KEY)

    srv = ThreadingHTTPServer((BIND, PORT), Handler)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)

    start_info_server()
    log("TLS 网关已启动：https://%s:%d -> %s" % (BIND, PORT, UPSTREAM))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
