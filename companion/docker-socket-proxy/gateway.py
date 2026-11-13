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
  UPSTREAM   上游地址，默认 http://127.0.0.1:2375
  STATE_DIR  状态目录，默认 /state
  EXTRA_HOSTS 额外要写进证书 SAN 的地址，逗号分隔（可选）
  BIND / PORT 监听，默认 0.0.0.0:2376
"""

import fcntl
import http.client
import ipaddress
import os
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

UPSTREAM = os.environ.get("UPSTREAM", "http://127.0.0.1:2375")
STATE_DIR = os.environ.get("STATE_DIR", "/state")
CERT = os.path.join(STATE_DIR, "server.crt")
KEY = os.path.join(STATE_DIR, "server.key")
CA = os.path.join(STATE_DIR, "ca.crt")
TOKEN_FILE = os.path.join(STATE_DIR, "token")
BIND = os.environ.get("BIND", "0.0.0.0")
PORT = int(os.environ.get("PORT", "2376"))
EXTRA_HOSTS = [h.strip() for h in (os.environ.get("EXTRA_HOSTS") or "").split(",") if h.strip()]

_u = urlsplit(UPSTREAM)
UP_HOST = _u.hostname or "127.0.0.1"
UP_PORT = _u.port or 80

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


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "prunemate-tls-gateway"

    def log_message(self, fmt, *args):
        pass

    def _deny(self):
        msg = b"403 Forbidden: missing or invalid X-PruneMate-Token\n"
        self.send_response(403)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)

    def _proxy(self, method):
        path = self.path
        # 版本协商放行：docker 客户端初始化时会先探测，这时还没带上自定义头
        needs_token = not path.rstrip("/").endswith("/version") and path.rstrip("/") != "/version"
        if needs_token and self.headers.get("X-PruneMate-Token", "") != TOKEN:
            log("%s %s %s -> 403" % (self.client_address[0], method, path))
            self._deny()
            return

        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        headers["X-Forwarded-For"] = self.client_address[0]
        headers["X-Forwarded-Proto"] = "https"

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


def print_client_config():
    """打印客户端要用的配置；只读，不改动任何状态"""
    ips = [i for i in local_ipv4()
           if not i.startswith(("127.", "172.", "10.200.", "169.254."))]
    log("")
    log("================ 客户端配置 ================")
    if ips:
        for ip in ips[:6]:
            log("  主机地址: https://%s:%d" % (ip, PORT))
    else:
        log("  主机地址: https://<本机IP>:%d" % PORT)
    log("  环境变量: PRUNEMATE_HOST_TOKEN=%s" % TOKEN)
    log("  CA 文件 : %s" % CA)
    log("  （CA 拷到 PruneMate 侧挂载，并设 REQUESTS_CA_BUNDLE=/certs/ca.crt）")
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
        print_client_config()
        log("完成。运行中的网关卡表要重建才会加载新证书/令牌：")
        log("  docker compose restart tls-gateway")
        return

    TOKEN = ensure_token()
    ensure_certs()

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(CERT, KEY)

    srv = ThreadingHTTPServer((BIND, PORT), Handler)
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)

    print_client_config()
    log("TLS 网关已启动：https://%s:%d -> %s" % (BIND, PORT, UPSTREAM))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
