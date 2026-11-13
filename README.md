<h2 align="center">⚠️ 安全警示</h2>

<div style="border:2px solid #dc2626;background:#fef2f2;border-radius:12px;padding:16px 20px;color:#b91c1c;line-height:1.9;">

> <span style="color:#dc2626;font-weight:700;font-size:1.05rem;">请先读完这一段，再决定是否部署。</span>

**1. 权限等级：本程序等价于宿主机 root**

PruneMate 挂载了 `/var/run/docker.sock`，容器内以 root 运行。**能控制它，就等于能控制整台宿主机**——
可以起停任意容器、挂载任意目录、读取任意宿主文件。这不是配置问题，是 Docker socket 的固有性质。

**2. 单机安装建议（推荐做法）**

| 场景 | 建议 |
|---|---|
| 只清理**本机** Docker | **只装 `prunemate.fpk`**，不要装网关、不要开放 2376 |
| 需要管理**其他机器** | 才在被管理机装 `prunemate-gateway.fpk` |
| 无论哪种 | 只在内网使用，禁止端口转发 / 内网穿透 / 公网映射 |

**3. 必须做的三件事**

- 首次登录后**立即修改默认密码**
- 绑定内网网卡，用防火墙限制访问来源（不要 `0.0.0.0` 直接对公网）
- 需要长期开着的话，把管理端放进独立 VLAN 或仅允许固定 IP 访问

**4. TOFU（首次信任）风险**

「按地址自动获取 CA」或添加 https 主机时的自动获取，属于**首次信任**：第一次连接时信任
网关 2377 页面给出的 CA。若那一刻网络被中间人控制，攻击者可以塞入自己的 CA 并截获令牌。

- 高安全环境：**关闭自动获取**（界面里的勾选框），改用「选择证书文件」本地上传
- 或者关闭网关信息页（`INFO_PORT=0`），让 2377 不可达

</div>

# PruneMate · 飞牛 fnOS 打包版

把 [PruneMate](https://github.com/anoniemerd/PruneMate)（Docker 定时清理助手）做成飞牛 fnOS 可安装的 `.fpk` 应用包，
并附带完整简体中文界面、登录认证与安全加固。

- 上游项目 / 开发者：**anoniemerd** — <https://github.com/anoniemerd/PruneMate>（AGPL-3.0）
- 中文打包与分发：**cyberzero** — 本仓库
- 本仓版本：**V1.4.0**
- 目标平台：飞牛 fnOS ≥ **1.2.1010**（x86 / ARM 通用，镜像本身多架构）

> 应用中心里显示的「开发者」是上游作者 anoniemerd，「发布者」是 cyberzero。
> 我只做了汉化、加固与 fpk 打包，没有改上游的功能实现。

---

## 两个包，各管一边

| 安装包 | 装在哪 | 作用 |
|---|---|---|
| `prunemate.fpk` | 管理端 | PruneMate 完整版：定时清理、预览、通知 + 外部主机管理 |
| `prunemate-gateway.fpk` | 被管理端 | 安全网关：TLS + 令牌 + Docker API 白名单 |
| `prunemate-lite.fpk` | 本机 | **单机版**：只清理本机 Docker，无外部主机/令牌/证书代码 |

三者的关系：

- 只清理本机 → 装 **单机版**，不需要网关，也不开放额外端口
- 要多管几台机器 → 管理端装**完整版**，被管理机装**网关**

单机版与完整版**互斥**（都用 7676 与同名容器），装之前先卸载另一个。

**两者互不依赖**，可单独安装、单独卸载、各自带 README 与依赖。
网关源码在 [`gateway-fpk/`](./gateway-fpk)，PruneMate 源码在 [`fpk/`](./fpk)。

安全边界与网络风险见 [`docs/security-audit.md`](./docs/security-audit.md)。

## 特性

| 项 | 说明 |
|---|---|
| 简体中文 | 界面、提示、推送通知正文全部汉化，保留 Docker/Gotify/ntfy 等专有名词 |
| 清理项说明 | 每个开关下方有风险说明与推荐等级（建议开启 / 谨慎开启 / 强烈建议关闭） |
| 亮色主题 | 右上角一键切换，偏好存 localStorage，首次访问跟随系统设置 |
| 危险操作醒目 | 清理相关按钮统一红色；风险说明文案按 严重/警告 分级着色，与标签一致 |
| 登录认证 | 默认开启，用户名 `admin`，scrypt 哈希 + 独立会话密钥 |
| 数据卷清理 | **默认关闭**，避免容器停机期间卷被当成"未引用"误删 |
| 容器加固 | `no-new-privileges`、`pids_limit 256`、`mem_limit 512m` |
| 桌面入口 | 安装后在 fnOS 应用中心有图标，点击直达 `http://<NAS>:7676` |

> ⚠️ 镜像自身仍在容器内以 root 运行并挂载 `/var/run/docker.sock`——这是 PruneMate 的工作原理决定的，
> **等于宿主机 root 权限**。所以登录认证不是可选项，请务必保持开启。

---

## 安装

### 方式一：fnOS 应用中心（推荐）

1. 打开「应用中心 → 手动安装」，选择 `prunemate.fpk`
2. 选择安装位置，等待拉取镜像（约 140 MB）
3. 安装完成后从桌面图标或 `http://<NAS 地址>:7676` 打开

### 方式二：命令行

```bash
# 预检（只解析不安装）
fnos-cli app install-fpk /vol1/1000/prunemate.fpk --volume-id <卷ID> --dry-run --yes

# 实际安装
fnos-cli app install-fpk /vol1/1000/prunemate.fpk --volume-id <卷ID> --yes
```

### 默认账号

```
用户名：admin
密码：  LitKgI13KWYI1a
```

> ⚠️ **安装后请立即修改密码**，步骤见「修改密码」一节。

这个密码是所有安装包共用的**出厂默认值**，不是给长期使用的凭据。

**为什么查不到密码**：安装后留在系统里的只有 scrypt 哈希（`PRUNEMATE_AUTH_PASSWORD_HASH`），
是单向散列，从哈希反推不出密码，也没有任何地方保存明文。所以忘记密码只能重置，不能"找回"。

- 想看「是否设了密码」：`docker inspect prunemate --format '{{range .Config.Env}}{{println .}}{{end}}' | grep PASSWORD_HASH`
- 想看「当前密码是什么」：做不到，只能重置

---

## 修改密码

### 方式一：命令行改（推荐，升级不丢）

```bash
docker exec prunemate python prunemate.py --set-password '你的新密码'
docker restart prunemate
```

单机版把容器名换成 `prunemate-lite`。

命令会把新哈希写入 `/config/auth.json`（数据目录里），**升级或重建容器都不会覆盖**。

### 方式二：安装时指定初始密码

在 compose 里加环境变量：

```yaml
environment:
  - PRUNEMATE_INIT_PASSWORD=你的初始密码
```

首次启动时用它生成哈希并写入 `auth.json`；之后即使把这个变量删掉、升级重装，
密码也保持不变（`auth.json` 优先）。

### 密码是怎么存的

```
优先级：/config/auth.json  >  PRUNEMATE_INIT_PASSWORD  >  PRUNEMATE_AUTH_PASSWORD_HASH
```

`auth.json` 只在不存在时由环境变量生成，之后一直是权威来源。文件权限 `0600`。
里面的哈希是 scrypt（32768 轮），**从哈希反推不出密码**，忘记密码只能用
`--set-password` 重设。

> 早期版本把哈希写在 compose 里，升级会被覆盖回出厂密码。现在不会了。

## 预构建镜像

汉化 + 加固后的镜像发布在 GHCR，可直接拉：

```bash
docker pull ghcr.io/magicindex/prunemate:1.4.0-zh
```

镜像 = 官方 `anoniemerd/prunemate:1.4.0` + `src/` 里的替换文件，本仓库根目录的
[`Dockerfile`](./Dockerfile) 就是这个镜像的构建定义，可自行复现：

```bash
docker build -t prunemate:1.4.0-zh .
```

镜像对应源码为当前主分支，digest：`sha256:d2ee2c36677ee6539f1b4216cde95ba4c9c446317f288724cdfa5ac281674cd9`

用这套镜像时不需要再挂 `zh/` 目录，中文已经在镜像里了。

## 管理外部 Docker 主机

PruneMate 可以管理**其他机器**上的 Docker（页面里的「Docker 主机」一节）。
Docker 默认不监听 TCP，所以要在被管理的主机上先起一个 socket 代理，
配套文件在 [`companion/docker-socket-proxy/`](./companion/docker-socket-proxy)
（固定使用 [Tecnativa/docker-socket-proxy](https://github.com/Tecnativa/docker-socket-proxy) **v0.5.0**）。

在被管理的主机上：

```bash
cd companion/docker-socket-proxy
docker compose up -d
curl http://127.0.0.1:2375/_ping      # 期望 200 OK
```

然后在 PruneMate 里「Docker 主机 → 添加新主机」，URL 填 `tcp://<被管理主机IP>:2375`，
保存后点该行的 ▶️ 启用。

已在 fnOS 上实测：A 机的 PruneMate 通过该代理读到 B 机的 12 个镜像与 51 项构建缓存，
预览接口正常返回两个主机的汇总。

### 部署方式

配套 compose 自带 **TLS 网关 + 令牌校验**，在被管理机上一条命令即可：

```bash
docker compose up -d
```

首次启动会**自动生成** CA、服务端证书和 64 位访问令牌，并在日志里打印客户端要填的配置——
不需要手动跑任何脚本。证书的 SAN 会自动写入本机全部 IPv4，客户端用哪个地址连都能校验通过。

PruneMate 侧只需要三项：

```yaml
environment:
  - PRUNEMATE_HOST_TOKEN=<日志里那串>
  - REQUESTS_CA_BUNDLE=/certs/ca.crt
volumes:
  - ./ca.crt:/certs/ca.crt:ro      # docker compose cp tls-gateway:/state/ca.crt ./ca.crt
```

主机地址填 `https://<IP>:2376`。

> CA 需要手动拷一次：它是每台机器首次启动随机生成的，客户端必须事先知道才能验证服务端。
> 把固定私钥打进分发包看似省事，实则等于公开私钥，任何人都能冒充服务端窃取令牌。
> 不依赖 Tailscale / stunnel / 任何第三方安全组件。

> ⚠️ 这个端口权限上基本等价于**该主机 root**。proxy 收窄的是"能访问哪些 API 分组"，
> 不能限制分组内的具体操作（开启 `CONTAINERS` 就同时放行了容器启停与 exec 创建）。
> 必须靠防火墙只放行 PruneMate 所在主机，别暴露到公网。详见配套 README。

## 打包

```bash
./scripts/build-fpk.sh
# 产物：fpk/prunemate.fpk
```

脚本会：
1. 把 `src/` 里的汉化文件同步到 `fpk/app/docker/zh/`
2. 检查/下载 `fnpack`（飞牛官方打包工具 v1.2.3）
3. 在 `fpk/` 里执行 `fnpack build`

需要网络下载 fnpack 与（打包时不需要）镜像。

---

## 手动 Docker 部署（不用 fpk）

见仓库根目录 [`docker-compose.yml`](./docker-compose.yml)，改好路径后：

```bash
docker compose up -d
```

注意：`./config` 与 `./logs` 需要属于 `root:root`（容器 `cap_drop: ALL` 后没有 `CAP_DAC_OVERRIDE`，
否则页面保存配置会报 `Permission denied`）：

```bash
sudo chown root:root ./config ./logs && sudo chmod 755 ./config ./logs
```

---

## 目录结构

```
.
├── src/                      # 汉化后的覆盖文件（基于上游 V1.4.0）
│   ├── index.html            #   主界面模板
│   ├── login.html            #   登录页
│   └── prunemate.py          #   后端（中文提示 + 中文推送正文）
├── fpk/                      # fnpack 打包工程
│   ├── manifest              #   应用元信息
│   ├── ICON.PNG / ICON_256.PNG
│   ├── app/
│   │   ├── docker/
│   │   │   ├── docker-compose.yaml
│   │   │   └── zh/           #   构建时由 src/ 同步进来
│   │   └── ui/config         #   桌面入口定义
│   ├── cmd/                  #   生命周期脚本
│   │   ├── main              #     状态回报
│   │   ├── install_callback  #     部署中文文件 + 修正目录属主
│   │   └── ...
│   ├── config/
│   │   ├── privilege         #   运行账号 docker-prunemate
│   │   └── resource          #   docker-project + 数据目录声明
│   └── wizard/
├── companion/
│   └── docker-socket-proxy/  # 外部 Docker 主机配套（自举 TLS 网关 + proxy，随 fpk 一起分发）
├── patches/                  # 汉化所用的精确替换脚本（可复现）
└── scripts/build-fpk.sh
```

安装后运行目录：

```
/var/apps/prunemate/
├── docker/docker-compose.yaml
├── shares/prunemate/{config,logs,zh}
└── ...
```

---

## 已落实的安全项

| 项目 | 状态 |
|---|---|
| 登录认证 | ✅ 开启（scrypt，32768 轮） |
| 会话密钥 | ✅ 独立随机，不再用上游硬编码兜底值 |
| 容器能力 | ✅ `no-new-privileges` + 资源上限（**未启用** `cap_drop: ALL`，原因见下） |
| 资源限制 | ✅ pids 256 / 内存 512 MB |
| 数据卷清理 | ✅ 默认关闭 |
| 已知问题规避 | ✅ 用 1.4.0（gunicorn 26.2.0），规避 1.3.3 控制套接字与 fork 的竞态死锁 |

关于 `cap_drop: ALL`：本包**没有**启用。原因很实际——容器以 root 跑，砍掉所有能力后
`CAP_DAC_OVERRIDE` 也没了，写入 `/config`、`/var/log` 会直接 `Permission denied`
（页面保存配置失败）。在自己的 NAS 上可以靠 `chown root:root` 数据目录绕过去，
但作为通用安装包，依赖安装钩子去改属主在 fnOS 上并不总是成立（回调不保证以 root 执行）。
两害相权，保留 `no-new-privileges` + 资源上限，登录认证作为主要防线。

已知限制：

- `/stats` 接口免认证，仅暴露清理计数
- 无 CSRF token，表单接口没有 `Origin` 校验
- 响应头缺少 `X-Frame-Options` / CSP

---

## 与上游的关系

本项目是 PruneMate 的**派生分发**，按 **AGPL-3.0** 授权：

- 原作者：anoniemerd（`maintainer` 字段，见 `fpk/manifest`）
- 打包分发：cyberzero（`distributor` 字段）


- 汉化与打包改动的完整源码即本仓库 `src/`、`patches/`、`fpk/`
- **应用图标**：`fpk/ICON*.PNG` 与 `fpk/app/ui/images/*` 的鲸鱼 + 扫帚 + PruneMate 字标，
  全部取自上游镜像内的 `/app/static/prunemate.png`，版权归原作者 anoniemerd，同样以 AGPL-3.0 提供。
  本项目只做了一件事：把这张透明底图合成到 `#0b1120` 深色底板并加圆角，以适配 fnOS 的图标规格。
  没有重新绘制，也没有主张任何图标著作权。
- 上游版权归 anoniemerd 所有，许可证全文见 [LICENSE](./LICENSE)
- 通过 fpk 分发二进制（Docker 镜像）时，源码由本仓库提供，符合 AGPL 的分发要求

如果你再分发本 fpk，请保留本仓库地址并同样以 AGPL-3.0 发布。

---

## 哪些是上游的，哪些是本仓库加的

改了什么、没改什么，说清楚，避免混淆归属。

### 来自上游 anoniemerd/PruneMate（本项目未修改其实现）

| 内容 | 位置 |
|---|---|
| 全部清理逻辑（镜像/容器/网络/卷/构建缓存） | `src/prunemate.py` 的业务函数 |
| 定时调度（APScheduler）、手动执行、预览接口 | 同上 |
| Gotify / ntfy / Discord / Telegram 推送 | 同上 |
| 登录鉴权机制（scrypt 哈希、Basic Auth 回退、`/stats` 免认证策略） | 同上 |
| 页面整体布局、组件结构与视觉设计（深色玻璃拟态） | `src/index.html`、`src/login.html` 的样式与 DOM |
| 应用图标与 Logo 素材 | `/app/static/prunemate.png`、`prunemate-icon.svg` |
| 名称 **PruneMate** | — |
| 许可证 AGPL-3.0 | `LICENSE` |

### 本仓库新增或修改的

| 内容 | 说明 |
|---|---|
| 界面全部中文文案 | 统计卡片、清理计划/选项、Docker 主机、通知设置、预览弹窗、`alert/confirm/prompt` |
| 服务端提示与推送正文汉化 | `flash()` 消息、推送通知里的计划描述与统计行 |
| 清理选项风险说明 | 5 个开关下新增说明文字与「建议开启/谨慎开启/强烈建议关闭」标签（新增 DOM + CSS） |
| 按钮布局调整 | 「保存并应用计划」「预览并运行」合并为同一行、等高 |
| **亮色主题** | 新增 `html[data-theme="light"]` 覆盖 + 右上角切换按钮，偏好存 localStorage |
| 容器加固配置 | compose 里的 `no-new-privileges`、`pids_limit`、`mem_limit`、认证环境变量（部署配置，非代码） |
| fpk 打包工程 | `fpk/` 下 manifest、`cmd/` 生命周期脚本、`config/privilege`、`config/resource`、`ui/config` |
| 构建脚本 | `scripts/build-fpk.sh`、`scripts/build-gateway-fpk.sh`、`Dockerfile` |
| **外部主机每主机令牌** | 主机条目新增 `token` 字段，界面可填；比全局环境变量更细的授权粒度 |
| **外部主机每主机 CA** | 主机条目新增 `ca_pem` 字段，用 `docker.tls.TLSConfig` 单独校验，信任不跨主机 |
| **按地址自动获取 CA** | 新接口 `/hosts/fetch-ca`，从网关 2377 只读页取证书；可一键关闭（TOFU 取舍） |
| **主机用量概览** | 新接口 `/hosts/overview`，卡片显示容器/镜像/占用/可回收 |
| **上次清理记录** | `host_stats.json` 按主机记录数量与释放空间，卡片显示「N 分钟前」 |
| **可读错误提示** | `explain_host_error()` 把底层异常翻译成证书/令牌/网络三类原因 |
| **界面细节** | 刷新按钮、禁缓存响应头、可折叠安全警示（30 秒自动收起） |
| **单机版（`prunemate-lite`）** | 与完整版同源，但**构建时裁剪**：移除全部 `/hosts*` 路由、令牌/CA 处理、外部主机客户端、主机卡片与其 JS/CSS |
| 单机版裁剪脚本 | `scripts/make-lite.py`：按路由/函数/JS 名精确删除，并在产物上做**残留引用自检**，有遗漏就让构建失败 |
| 单机版打包工程 | `lite-fpk/`：appname `prunemate-lite`、`app/ui` 桌面入口、带 `LOCAL` 标识的独立图标 |
| 单机版构建脚本 | `scripts/build-lite-fpk.sh`：生成源码 → 打包 → 校验产物存在 |
| 文档 | 本 README、发版说明 |

### 网关包 `prunemate-gateway`（本仓库原创，非上游）

这一块要特别说明，避免把两件事混在一起：

| 项 | 归属 |
|---|---|
| 网关实现（TLS 终结、令牌校验、接口白名单、证书生成） | **本仓库原创代码**，不在上游项目里 |
| 网关使用的 Docker API | 上游 PruneMate 的调用约定（`containers/images/networks/prune` 等） |
| 图标素材 | **沿用上游 logo**，本仓库没有重绘 |
| `Dockerfile` / compose / 生命周期脚本 | 本仓库编写；v2.0 起已不再使用容器 |
| 许可证 | AGPL-3.0，与上游一致 |

**关于包内 `maintainer` 字段**：网关包在 fnOS 应用中心显示「开发者 anoniemerd / 发布者 cyberzero」，
这是为与本体包保持生态一致而做的标注。**网关代码由 cyberzero 维护，上游作者并未参与实现**，
此处的取舍是"归属上游生态"而非"声称上游编写"。如果你更看重准确性，可把
`gateway-fpk/manifest` 的 `maintainer` 改回 `cyberzero`。

### 边界原则

- **功能与设计归上游**：本项目不改清理策略、不加新功能，只做本地化与打包
- **图标归上游**：见下方「与上游的关系」，未重新绘制、不主张著作权
- **署名分开**：`maintainer` = anoniemerd，`distributor` = cyberzero，互不代表对方
- **网关是新增件**：`prunemate-gateway` 不含上游代码，也不修改上游实现；上游单独使用时不需要它
- **不改上游行为**：外部主机、令牌、CA 这些能力都在本仓库新增的文件里实现，
  上游 `prunemate.py` 的清理策略与调度逻辑保持原样
- **单机版不是分支**：`prunemate-lite` 与完整版共用同一份 `src/`，差异全部由构建脚本裁剪产生；
  上游代码在两者中的业务逻辑完全一致
- **单机版的删除是真的删除**：裁剪后 `/hosts*` 路由、令牌/CA 代码在进程里不存在，
  不是运行期开关，也不依赖任何环境变量

## 接入本项目的网关（https + 令牌）

网关走的是 TLS + 令牌，不是明文 2375。**v2.0 起网关是主机进程，没有容器**，
凭证在应用共享目录里：

```
/appshare > prunemate-gateway
├── client-info.txt   地址 + 令牌 + 用法
├── token.txt         令牌
└── ca.crt            给 PruneMate 侧使用
```

在 PruneMate 页面「Docker 主机」区块：

1. 添加主机：名称随意，地址 `https://<被管理机IP>:2376`
2. 令牌：从 `token.txt` 复制
3. CA：点「按地址自动获取」（从 `http://<IP>:2377/ca.crt` 取），或手动选 `ca.crt` 文件

点「保存」即完成——**不需要改 compose、不需要环境变量**。

`PRUNEMATE_HOST_TOKEN` 与 `REQUESTS_CA_BUNDLE` 仍兼容旧部署，但不再是必需配置。

> 单机使用（只清理本机 Docker）时**不需要装网关**，本机走 unix socket。

**常见错误对照**

| 现象 | 原因 |
|---|---|
| `Invalid bind address format: port is required` | 地址没写端口 |
| `证书校验失败：上传的 CA 与这台网关不匹配` | CA 传错机器，或网关重装换了 CA |
| `令牌无效` | 网关重装换了令牌，去 `token.txt` 重新复制 |
| `无法连接` | 网关没启动，或端口不是 2376 |
| `path not allowed` | 网关白名单拦截（例如 docker-py 请求了未放行的接口） |

## 版本号说明

这里有两套编号，别混：

| 编号 | 含义 | 在哪里 |
|---|---|---|
| `1.4.0` | **应用版本**，跟上游 anoniemerd/PruneMate 保持一致 | `fpk/manifest` 的 `version` 字段，应用中心显示的就是它 |
| `v1.4.0` / `v1.4.0-2` / `v1.4.0-3` | **打包修订号** | Git 标签 / Release 标题 |

刻意不把应用版本往上加，原因：fnOS 用 `manifest` 的 `version` 做版本比较，
写 `1.4.0-1` 容易被当成预发布排在 `1.4.0` 之前，写 `1.4.1` 又对不上上游。
所以**打包层面的改动一律只体现在标签上**，应用版本严格跟随上游。

副作用：应用中心不会把旧包"升级"成新包，换包需要**先卸载再安装**。

| 标签 | 打包改动 |
|---|---|
| `v1.4.0` | 首个打包版本 |
| `v1.4.0-2` | `os_min_version` 由 `1.2.0` 收紧为实测通过的 `1.2.1010` |
| `v1.4.0-3` | 应用图标改用软件内置 logo |
| `v1.4.0-4` | 新增亮色主题（含登录页）与右上角切换按钮 |
| `v1.4.0-5` | 「预览并运行」「确认并执行」改为危险红；清理项风险说明与标签同色系 |
| `v1.4.0-6` | 外部主机支持 `X-PruneMate-Token` 请求头认证 |
| `v1.4.0-7` | 配套改为自举：证书与令牌首次启动自动生成 |
| `v1.4.0-8` | 配套支持随时重新生成私钥与令牌 |
| `v1.4.0-9` | **拆分为两个独立安装包**，网关不再塞进本体包 |
| `v1.4.0-10` | 修正外部主机提示文案（`https://` 与 `tcp://` 两种填法） |
| `v1.4.0-11` | 外部主机支持**每主机令牌**，界面直接填 |
| `v1.4.0-12` | compose 显式声明项目名，避免与应用中心的容器名冲突 |
| `v1.4.0-13` | 外部主机 CA 可在界面粘贴，无需改 compose |
| `v1.4.0-14` | 令牌容错：粘贴时带换行/空格/前缀也能识别 |
| `v1.4.0-15` ~ `-16` | CA 改为上传文件；上传改为页内异步，不刷新、不丢内容 |
| `v1.4.0-17` | 连接失败给出可读原因（证书不匹配 / 令牌无效 / 端口不通） |
| `v1.4.0-18` | 新增「按地址自动获取 CA」 |
| `v1.4.0-19` | CA 状态显示证书份数；清除加二次确认 |
| `v1.4.0-20` | **CA 改为每主机独立**，缩小信任面 |
| `v1.4.0-21` | 主机卡片显示容器/镜像/占用/可回收；预览逐台展示 |
| `v1.4.0-22` | 添加 https 主机未提供 CA 时自动获取（TOFU） |
| `v1.4.0-23` | 新增开关：可关闭自动获取 CA，只用本地上传 |
| `v1.4.0-24` | README 与界面顶部加入红色安全警示；网关 2377 页同步 |
| `v1.4.0-25` | 首页禁缓存；主机统计改用 data 属性匹配；加载超时有提示 |
| `v1.4.0-26` | 新增「刷新统计」按钮 |
| `v1.4.0-27` | 主机卡片显示上次清理数量与释放空间；清理后自动刷新 |
| `v1.4.0-28` | 安全警示 30 秒自动收起为按钮，可手动展开；新增「每次都显示」 |
| `v1.4.0-29` | 编辑主机改为就地表单，可改地址/令牌/CA |
| `v1.4.0-30` | README 补全版本与边界说明，并随包分发 |
| `v1.4.0-31` | 三包合并发布（本体 / 网关 / 单机版同一发布窗口） |
| `v1.4.0-32` | 修复单机版桌面图标后重新合并发布 |
| `v1.4.0-33` | 前端统一安全解析 JSON；修复单机版清理报错，重新合并发布 |
| `v1.4.0-34` | 单机版补齐 refreshAll，重新合并发布（本体/网关字节未变） |
| `v1.4.0-35` | 重建并推送预构建镜像（此前镜像停留在早期版本），README 更新 digest |
| `v1.4.0-36` | README「本仓库新增或修改的」补充单机版条目与边界原则 |
| `v1.4.0-37` | 清洗内网地址，发布者地址改为 GitHub，为公开发布做准备 |
| `v1.4.0-38` | README 恢复显示出厂默认密码（并强调装后立即修改） |
| `v1.4.0-39` | 密码哈希持久化到 `/config/auth.json`，升级不再被覆盖；新增 `--set-password` 与 `PRUNEMATE_INIT_PASSWORD` |

### 网关包的版本号（独立编号）

网关是**独立安装包**，有自己的版本序列，与 PruneMate 本体互不影响：

| 标签 | 改动 |
|---|---|
| `gateway-v1.0.0` | 首个网关包：TLS + 令牌 + 接口白名单 |
| `gateway-v1.0.1` | 改为**方法 + 路径**严格白名单，关闭 `/containers/{id}/*` 生命周期动作 |
| `gateway-v1.0.2` | 接入信息（令牌/CA）导出到 `public/` |
| `gateway-v1.0.3` | compose 显式声明项目名 |
| `gateway-v1.0.4` | 新增只读信息页 2377，浏览器可直接下载 `ca.crt` |
| `gateway-v1.0.5` | 启动日志打印完整 CA，令牌可选择性隐藏 |
| `gateway-v1.0.6` | 令牌单独成行；容忍请求头空白 |
| `gateway-v2.0.0` | **架构变更**：改为直接运行在主机上，不再依赖任何镜像 |
| `gateway-v2.0.3` | 令牌/CA 写入共享目录 `@appshare/prunemate-gateway/` |
| `gateway-v2.0.4` | 凭证在两个位置各放一份（已回退为单一位置） |
| `gateway-v2.0.5` | 凭证只保留共享目录一处 |
| `gateway-v2.0.6` | README 与 2377 页面加入安全警示；开发者标注回到上游 |
| `gateway-v2.0.7` | 放行 `GET /images/{id}/json`；403 区分「令牌无效」与「路径不在白名单」 |
| `gateway-v2.0.8` | README 随包分发；完善变更边界说明 |

### 单机版的版本号

`prunemate-lite` 与本体共用应用版本号，打包修订独立：

| 标签 | 说明 |
|---|---|
| `lite-v1.4.0-1` | 首个单机版：从主源码裁剪，移除 `/hosts*` 接口、令牌/CA 处理、外部主机客户端 |
| `lite-v1.4.0-2` | 修复桌面无图标：补 `app/ui` 入口与 `desktop_*` 字段，使用带 LOCAL 标识的独立图标 |
| `lite-v1.4.0-3` | 修复执行清理报 `Unexpected token '<'`（裁剪后残留函数调用导致 500） |
| `lite-v1.4.0-4` | 补齐 `refreshAll` 桩函数；生成时增加残留引用自检 |

裁剪由 `scripts/make-lite.py` 在构建时完成，不是运行时开关——单机版进程里**不存在**这些代码。

## 更新记录

### V1.4.0-6 ~ -30（打包与配套演进）

- 外部主机：令牌认证 → 每主机令牌 → 每主机独立 CA → 自动获取与开关
- 配套网关：独立成包（`prunemate-gateway.fpk`），从容器版演进到免镜像的主机进程版
- 界面：主机用量卡片、刷新按钮、上次清理结果、可读错误提示、可折叠安全警示
- 打包：两个包各自发布、标签与产物逐一核对

### V1.4.0（2026-11-12）

- 升级到上游 V1.4.0（外部主机健康探测、通知精简、gunicorn 26.2.0）
- 全量简体中文汉化
- 清理选项增加风险说明与推荐等级
- 「保存并应用计划」「预览并运行」合并为同一行等高布局
- 默认关闭数据卷清理
- 打包为飞牛 fpk，安装即成应用
