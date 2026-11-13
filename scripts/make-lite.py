#!/usr/bin/env python3
"""从主源码生成「纯本机版」：移除所有外部主机 / 网关 / 令牌 / CA 相关代码。

输出到 lite-fpk/app/docker/zh/，由 scripts/build-lite-fpk.sh 打包。
原则：只删不改——不重写业务逻辑，避免与主版本产生行为差异。
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "lite-fpk", "app", "docker", "zh")

HOST_ROUTES = [
    "/hosts", "/hosts/add", "/hosts/<int:index>/update", "/hosts/<int:index>/delete",
    "/hosts/<int:index>/toggle", "/hosts/status", "/hosts/overview",
    "/hosts/fetch-ca", "/hosts/ca", "/hosts/auto-ca",
]
HOST_FUNCS = [
    "fetch_ca_from_gateway", "load_host_stats", "save_host_stats", "explain_host_error",
]
HOST_JS = [
    "loadHosts", "refreshHostStatuses", "refreshHostOverview", "loadCaFile", "fetchCa",
    "saveAutoCa", "uploadCa", "clearCa", "editHost", "cancelEditHost", "addNewHost",
    "deleteHost", "toggleHost", "initHostsCollapse", "refreshAll",
]


def strip_route(text, route):
    """删除指定路由的整个函数（含装饰器）"""
    pat = re.compile(r'@app\.route\(\s*["\']' + re.escape(route) + r'["\'][^\n]*\n', re.M)
    m = pat.search(text)
    if not m:
        return text, False
    start = m.start()
    i = m.end()
    # 跳过可能的第二个装饰器
    while text[i:].lstrip().startswith("@"):
        i = text.index("\n", text.index("@", i)) + 1
    # 找 def 行
    while not text[i:].lstrip().startswith("def "):
        nl = text.find("\n", i)
        if nl == -1:
            return text, False
        i = nl + 1
    # 函数体：到最后一行顶格内容之后
    lines = text[i:].split("\n")
    body = []
    for ln in lines:
        if ln and not ln[0].isspace() and not ln.startswith("#") and body:
            break
        body.append(ln)
    end = i + len("\n".join(body))
    return text[:start] + text[end:], True


def strip_func(text, name):
    """删除模块级函数定义"""
    pat = re.compile(r'^def ' + re.escape(name) + r'\(', re.M)
    m = pat.search(text)
    if not m:
        return text, False
    start = m.start()
    lines = text[m.end():].split("\n")
    body = []
    for ln in lines:
        if ln and not ln[0].isspace() and not ln.startswith("#") and body:
            break
        body.append(ln)
    end = m.end() + len("\n".join(body))
    return text[:start] + text[end:], True


def strip_js_func(text, name):
    """按大括号匹配删除 JS 函数"""
    pat = re.compile(r'\n(\s*)(?:async\s+)?function\s+' + re.escape(name) + r'\s*\(')
    m = pat.search(text)
    if not m:
        return text, False
    i = text.index("{", m.end() - 1)
    depth = 0
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                i += 1
                break
        i += 1
    return text[:m.start()] + text[i:], True


def main():
    os.makedirs(OUT, exist_ok=True)
    report = []

    # ---------- prunemate.py ----------
    py = io.open(os.path.join(SRC, "prunemate.py"), encoding="utf-8").read()

    for r in HOST_ROUTES:
        py, ok = strip_route(py, r)
        report.append(f"route {r}: {'removed' if ok else 'NOT FOUND'}")
    for f in HOST_FUNCS:
        py, ok = strip_func(py, f)
        report.append(f"func {f}: {'removed' if ok else 'NOT FOUND'}")

    # 客户端工厂：整段重写为只支持本机 socket
    start = py.find('def create_docker_client(')
    end = py.find('\ndef ', start + 10)
    lite_client = '''def create_docker_client(host_url: str, token: str = "", ca_pem: str = ""):
    """纯本机版：只支持本机 Docker socket。

    token / ca_pem 参数保留只是为了不改动调用点，实际不使用。
    """
    if docker is None:
        log("Docker SDK not available.")
        return None
    try:
        return docker.DockerClient(base_url="unix:///var/run/docker.sock")
    except Exception as e:
        log(f"Failed to create Docker client for {host_url}: {e}")
        return None

'''
    if start != -1 and end > start:
        py = py[:start] + lite_client + py[end + 1:]
        report.append("create_docker_client: rewritten (unix only)")
    else:
        report.append("create_docker_client: NOT FOUND")

    # 去掉外部主机相关配置项
    for line in ['    "external_ca_pem": "",',
                 '    # 是否允许从网关只读页自动获取 CA（TOFU）。关闭后只能手动选证书文件。',
                 '    "auto_fetch_ca": True,']:
        py = py.replace(line + "\n", "")
    py = py.replace('                           external_ca_pem=config.get("external_ca_pem") or "",\n', '')
    py = py.replace('                           auto_fetch_ca=config.get("auto_fetch_ca", True))', ')')

    # 调用点去掉 token / ca_pem 传参
    py = py.replace('create_docker_client(host_url, (host or {}).get("token", ""), (host or {}).get("ca_pem", ""))',
                    'create_docker_client(host_url)')
    py = py.replace('    "auto_fetch_ca": True,', '')

    # 配置里不再保留外部主机集合
    py = py.replace('    "docker_hosts": [],', '    "docker_hosts": [],   # 纯本机版恒为空')

    # 已删除函数的调用点：改成等价的安全写法
    py = (py
          .replace("        save_host_stats(host_results)\n", "")
          .replace('explain_host_error(None, host_url)', '"无法连接外部主机"')
          .replace('"error": explain_host_error(e),', '"error": str(e),'))

    io.open(os.path.join(OUT, "prunemate.py"), "w", encoding="utf-8").write(py)

    # ---------- index.html ----------
    html = io.open(os.path.join(SRC, "index.html"), encoding="utf-8").read()

    # 整块删除 Docker 主机制卡（含 h2）
    start = html.find("<!-- Docker Hosts Management Section -->")
    end = html.find("<!-- Notifications configuration section -->")
    if start != -1 and end > start:
        html = html[:start] + html[end:]
        report.append("html hosts card: removed")
    else:
        report.append("html hosts card: NOT FOUND")

    for name in HOST_JS:
        html, ok = strip_js_func(html, name)
        report.append(f"js {name}: {'removed' if ok else 'NOT FOUND'}")

    # 删掉只服务于主机卡片的 CSS 规则
    html = re.sub(r'^\s*#hosts-card[^\n]*\n', '', html, flags=re.M)

    # 安全警示里关于网关/CA 的句子改成单机版说法
    html = html.replace(
        '· 单机使用（只清理本机 Docker）时<b>不要安装网关、不要开放 2376</b>；管理外部主机才需要网关。',
        '· 本版本只管理本机 Docker，<b>不连接任何外部主机</b>，也不开放额外端口。')
    html = html.replace(
        '· 外部主机 CA 若使用「自动获取」属于<b>首次信任（TOFU）</b>，首次连接时可能被中间人利用；高安全环境请改为手动上传证书文件。',
        '· 本版本不含令牌与证书功能，没有外部主机信任配置。')

    # 单机版仍需要「清理完成后刷新统计」，补一个只刷统计的 refreshAll
    html = html.replace("    let hostStatusCheckInProgress = false;",
        "    async function refreshAll(){\n"
        "      try { await loadStats(); } catch (e) { console.error('refreshAll:', e); }\n"
        "    }\n\n"
        "    let hostStatusCheckInProgress = false;", 1)

    # 移除对已删函数的调用
    for call in ["loadHosts();", "refreshHostOverview().catch(e => console.error('overview:', e));",
                 "setInterval(refreshHostStatuses, 60000);", "initHostsCollapse();",
                 "refreshHostStatuses();"]:
        html = html.replace(call, "")

    io.open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)

    # ---------- login.html 原样复制 ----------
    io.open(os.path.join(OUT, "login.html"), "w", encoding="utf-8").write(
        io.open(os.path.join(SRC, "login.html"), encoding="utf-8").read())

    # ---------- 产物自检 ----------
    out_py = io.open(os.path.join(OUT, "prunemate.py"), encoding="utf-8").read()
    out_html = io.open(os.path.join(OUT, "index.html"), encoding="utf-8").read()
    leftovers = []
    for name in HOST_FUNCS:
        # 允许出现在注释里，但不允许以调用形式出现
        if re.search(r'(?<!#)\b' + re.escape(name) + r'\s*\(', out_py):
            leftovers.append("py:" + name)
    # refreshAll 是刻意补回的（只刷统计），单独校验存在且仅定义一次
    reintroduced = {"refreshAll"}
    for name in HOST_JS + ["refreshHostStatuses", "loadHosts"]:
        if name in reintroduced:
            continue
        if re.search(r'\b' + re.escape(name) + r'\s*\(', out_html):
            leftovers.append("js:" + name)
    if out_html.count("async function refreshAll(") != 1:
        leftovers.append("js:refreshAll 定义数量异常")
    if leftovers:
        report.append("残留引用: " + ", ".join(sorted(set(leftovers))))
    else:
        report.append("残留引用: 无")

    print("\n".join("  " + r for r in report))
    missing = [r for r in report if "NOT FOUND" in r or r.startswith("残留引用: ") and "无" not in r]
    if missing:
        print(f"\n警告：{len(missing)} 项未找到，请检查源码是否变化")
        return 1
    print("\n生成完成：", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
