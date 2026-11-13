# 安全审计与网络风险报告

对象：PruneMate 双包方案（`prunemate.fpk` + `prunemate-gateway.fpk`）
审计时间：2026-11-12
审计方式：包结构与配置核查、运行态端口探测、TLS/令牌行为实测、代码审阅

---

## 一、两个包的职责与暴露面

| | `prunemate.fpk`（管理端） | `prunemate-gateway.fpk`（被管理端） |
|---|---|---|
| 装在哪 | 管理机 | 被管理的 Docker 主机 |
| 对外端口 | 7676（Web 界面） | 2376（TLS 网关） |
| 对内端口 | — | 2375（仅 127.0.0.1） |
| 挂载 | `/var/run/docker.sock` | `/var/run/docker.sock`（只读）+ socket-proxy |
| 依赖 | 官方镜像 `anoniemerd/prunemate:1.4.0` | 同左（基座）+ `tecnativa/docker-socket-proxy:v0.5.0` |
| 相互依赖 | 无 | 无（可单独安装/卸载） |

两个包唯一的共同点是复用同一个基础镜像，**没有运行时依赖关系**：只装网关也能工作，
只装 PruneMate 也能本地清理。

---

## 二、端口矩阵（实测）

| 主机 | 端口 | 暴露范围 | 用途 | 风险 |
|---|---|---|---|---|
| 管理端 | 7676 | 0.0.0.0 | Web 控制台 | 中（已开认证） |
| 被管理端 | 2376 | 0.0.0.0 | TLS 网关 | **高** |
| 被管理端 | 2375 | 127.0.0.1 only | socket-proxy | 低（本机） |

实测确认：`<被管理机>:2375` 从外部不可达（000），`2376` 可达。

---

## 三、核心风险：2376 等价于该主机 root

Docker socket 本质是 root 权限。**即使经 socket-proxy 收窄，也只限制了"能调哪些 API 分组"，
没有限制分组内的操作。**

实测证据（v0.5.0 默认 ACL）：

```
POST /containers/<id>/start  → 放行（容器被真的启动）
POST /containers/<id>/exec   → 放行（只是容器 id 不存在才返回 400）
```

原因：ACL 规则 `^/containers` 命中 `CONTAINERS=1` 就整体放行，`ALLOW_START`/`ALLOW_STOP`
这类细粒度开关只在**关闭 CONTAINERS** 时生效。而 PruneMate 必须列容器才能判断哪些镜像/卷被占用，
所以 `CONTAINERS` 关不掉。

**结论：拿到 2376 的令牌 = 拿到该主机的容器层控制权（可起停容器、创建 exec 进入 shell）。**

### 缓解措施（v1.0.1 起改为严格白名单）

原版模板用分组 ACL，`CONTAINERS=1` 等于放行整个 `/containers` 子树。
新版改成**方法 + 路径**白名单，只放行 PruneMate 实际调用的端点：

| 放行 | 说明 |
|---|---|
| `GET /_ping`、`GET /version` | 连通性探测 |
| `GET /containers/json` | 列容器 |
| `GET /images/json` | 列镜像 |
| `GET /networks` | 列网络 |
| `GET /system/df` | 预览里算可回收空间 |
| `POST /containers/prune` | 清停止容器 |
| `POST /images/prune` | 清未使用镜像 |
| `POST /networks/prune` | 清未使用网络 |
| `POST /build/prune` | 清构建缓存 |

其它一律 403，包括：`/containers/{id}/start|stop|restart|kill|exec`、`/containers/create`、
`DELETE /containers/{id}`、`DELETE /images/{id}`、`/secrets`、`/swarm`、`/info`。

**数据卷清理默认关闭**（`volumes` 端点未放行）——要开必须在模板里取消注释并同步 `VOLUMES=1`。

实测结果：

```
GET  /containers/json            -> 200
POST /containers/prune           -> 200
POST /containers/<id>/start      -> 403
POST /containers/<id>/stop       -> 403
POST /containers/<id>/exec       -> 403
DELETE /containers/<id>          -> 403
DELETE /images/<name>            -> 403
GET  /secrets | /swarm | /info   -> 403
```

PruneMate 在严格白名单下预览、清理均正常（实测读到 92 项构建缓存）。

### 为什么不用「容器 ID 白名单」

危险操作是 `/containers/{id}/start|exec|delete` 这类**生命周期动作**，
按 ID 放行等于允许对这些容器做任何事——包括 exec 进去拿 shell，风险反而更高。
正确的切法是**限制"能做什么"而不是"对哪个对象做"**：
只保留列举与 prune，把整个 `/containers/{id}/*` 关掉。

### 残留风险

- 仍可执行 **prune**（删停止容器、删未使用镜像、删构建缓存），属于破坏性但不可持久化的操作
- 数据卷 prune 默认关闭，若打开则存在误删数据风险
- 令牌明文放在请求头，靠 TLS 保护
- 网关私钥存在被管理机本地 `/var/apps/prunemate-gateway/shares/state/`（600 权限）

---|---|
| TLS（自签 CA） | 链路加密，防嗅探 |
| 访问令牌（64 位） | 未持令牌者直接 403 |
| 接口白名单 | 挡住 `secrets`/`auth`/`swarm`/`nodes` 等分组 |
| 内层只绑回环 | proxy 不经局域网暴露 |

### 残留风险

- 令牌是**明文**放在请求头里，靠 TLS 保护；TLS 被降级或中间人成功则令牌泄露
- `CONTAINERS=1` 带来的容器级操作无法通过该 proxy 拦截
- 网关证书私钥就在被管理机本地（`/var/apps/prunemate-gateway/shares/state/`），
  拿到该目录等于可冒充网关

**建议**：2376 只在必要时间段开放；用防火墙限制来源 IP；不要做端口转发/内网穿透。

---

## 三之二、网关 v2.0.0 架构变化（重要）

为解决镜像源拉取失败（`docker.fnnas.com` 对部分镜像返回 401），网关从容器改为
**直接运行在主机上的 Python 进程**：

| 项 | v1.x（容器） | v2.0（主机进程） |
|---|---|---|
| 依赖 | 需要基础镜像 + socket-proxy 镜像 | 只需系统自带 python3 + openssl |
| 中间层 | docker-socket-proxy（haproxy） | 无，白名单在网关内实现 |
| 上游 | 127.0.0.1:2375 | `/var/run/docker.sock` 直连 |
| 运行用户 | 容器内 root | **主机 root**（需读 docker.sock） |
| 卸载 | 删容器 | 杀进程（uninstall_callback） |

**新增风险**：进程以 root 运行，且不像容器那样有 namespace 隔离。但它本来就是要
代理 Docker API 的，权限层面等价；真正的边界仍是网络与令牌。

**建议**：如果不接受 root 进程，可改用容器版（v1.x），代价是需要可用的镜像源。

## 四、管理端（7676）风险

| 项 | 状态 |
|---|---|
| 登录认证 | ✅ 已启用（scrypt，32768 轮） |
| 会话密钥 | ✅ 独立随机，非上游默认值 |
| 未登录访问 | ✅ 302 → 登录页（实测） |
| 容器权限 | ⚠️ 以 root 运行，未 `cap_drop`（原因见下） |
| CSRF | ⚠️ 无 token，无 Origin 校验（上游设计） |
| 安全响应头 | ⚠️ 无 `X-Frame-Options` / CSP（上游设计） |
| `/stats` | ⚠️ 免认证，仅暴露清理计数（上游设计） |

### 关于未启用 `cap_drop: ALL`

启用后 root 失去 `CAP_DAC_OVERRIDE`，写 `/config`、`/var/log` 会 `Permission denied`，
表现为页面保存配置失败。在自己的机器上可以靠 `chown root:root` 数据目录绕过，
但作为分发包装依赖安装钩子改属主并不可靠（实测 fnOS 的 `install_callback` 不保证执行）。

---

## 五、网络层面的连带风险

1. **Tailscale 会把 7676/2376 一起带进 tailnet**
   `.201` 对外广播了整个网段子网路由，tailnet 内任意设备都能访问这两个端口。
   2376 尤其危险——它不需要经过管理端就能直接调被管理机的 Docker。
   建议在 Headscale ACL 里按端口收窄，或把网关绑定到内网网卡而不绑 tailscale 网卡。

2. **多网卡等于多入口**
   `.201` 上有多张网卡（多个内网段 + tailnet），
   `0.0.0.0` 监听意味着每个网段都能进。实测证书 SAN 里已包含这些地址（便于使用，
   但也意味着任意一个地址都能连上）。

3. **本地回环不等于安全**
   同机其他容器若使用 host 网络，可以直接访问 `127.0.0.1:2375`，绕过 TLS 与令牌。

---

## 六、供应链风险

| 项 | 说明 |
|---|---|
| 基础镜像 | `anoniemerd/prunemate:1.4.0`，AGPL-3.0，上游活跃维护 |
| 代理镜像 | `tecnativa/docker-socket-proxy`，固定在 `v0.5.0`（非 latest） |
| 镜像来源 | 走本机配置的镜像源；建议核对 digest |
| 私有凭据 | 仓库内 `fpk/app/docker/docker-compose.yaml` 含默认密码哈希与 `PRUNEMATE_SECRET`，仓库必须保持私有 |

---

## 七、风险汇总

| 编号 | 风险 | 等级 | 处理状态 |
|---|---|---|---|
| R1 | 令牌泄露后可调 API | **中** | v1.0.1 严格白名单：无法 exec/启停/删容器，仅剩 prune |
| R2 | 分组 ACL 粒度粗 | 已解决 | 改为方法+路径白名单，不再依赖分组开关 |
| R3 | tailnet / 多网卡扩大暴露面 | 中 | 待人工按需收窄 |
| R4 | 管理端无 CSRF / 安全头 | 中 | 上游设计，未改 |
| R5 | `/stats` 免认证 | 低 | 仅计数，接受 |
| R6 | 容器内 root，未 cap_drop | 中 | 已知取舍，见第四节 |
| R7 | 令牌明文（靠 TLS 保护） | 中 | TLS 已覆盖 |
| R8 | 网关私钥存于本机磁盘 | 中 | 文件权限 600，随包状态目录 |

---

## 八、建议的加固清单

1. **2376 只绑内网网卡**，不要绑 tailscale：
   `ports: - "内网IP:2376:2376"` 的形式，或在网关里加 `BIND` 环境变量
2. **防火墙限源**：只允许管理端 IP 访问 2376
3. **Headscale ACL 按端口放行**，别让整个 tailnet 都能连 2376
4. **网关用完就停**：`docker compose stop` / 在 fnOS 应用中心停止应用
5. **定期轮换**：`docker exec prunemate-gateway python /app/gateway.py --regen-certs`
6. **不要暴露到公网**，不要用内网穿透
7. 管理端保持强密码，仓库保持私有

---

## 九、结论

- 两个包结构清晰、互不耦合，安装后即刻可用，证书与令牌首次启动自动生成
- 链路加密与访问控制已具备，**能挡住局域网内的随意访问与被动嗅探**
- 严格白名单后，2376 **不再等价于容器层 root**：拿不到 shell、改不了容器状态
- 剩下的破坏面是 prune（删未使用资源），数据卷默认不开放
- 网络隔离（防火墙 / 绑定网卡 / 按需开启）仍建议做，TLS 与令牌是纵深防御的前两层
