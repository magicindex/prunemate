# docker-socket-proxy（外部 Docker 主机配套）

[PruneMate](https://github.com/anoniemerd/PruneMate) 的「Docker 主机」功能可以管理**其他**机器上的 Docker，
连接方式是 `tcp://<主机IP>:2375`。Docker 默认不监听 TCP，所以需要在被管理的主机上起一个
[docker-socket-proxy](https://github.com/Tecnativa/docker-socket-proxy)（本项目固定 **v0.5.0**）。

## 部署（在被管理的主机上，一条命令）

```bash
docker compose up -d
docker compose logs tls-gateway | head -30
```

**首次启动会自动完成所有准备工作**，不需要手动跑任何脚本：

- 生成自签 CA 与服务端证书（证书里自动写入本机全部 IPv4，客户端用哪个 IP 连都能校验通过）
- 生成 64 位随机访问令牌
- 在日志里打印客户端要填的配置

这些状态存在 `gateway-state` 卷里，之后重启 / `docker compose up -d` 都沿用同一套，不会重新生成。

架构：

```
PruneMate ──https(自签CA)──> tls-gateway ──http──> docker-socket-proxy ──unix──> dockerd
              ↑ 令牌在 TLS 里              ↑ 只绑 127.0.0.1，做接口白名单
```

只有网关的 `2376` 对外开放，`docker-socket-proxy` 绑在回环上，局域网访问不到。

## 客户端怎么配（第一次需要拷一个文件）

日志里会打印这样一段：

```
================ 客户端配置（复制这一段） ================
  主机地址: https://<本机IP>:2376
  环境变量: PRUNEMATE_HOST_TOKEN=3bd9aa42...
  CA 文件 : /state/ca.crt
==========================================================
```

把 CA 取出来：

```bash
docker compose cp tls-gateway:/state/ca.crt ./ca.crt
# 或从卷里取
```

PruneMate 侧：

```yaml
environment:
  - PRUNEMATE_HOST_TOKEN=<日志里那串>
  - REQUESTS_CA_BUNDLE=/certs/ca.crt
volumes:
  - ./ca.crt:/certs/ca.crt:ro
```

然后在页面「Docker 主机」里填 `https://<被管理机IP>:2376`。

> **为什么 CA 还要单独拷**：CA 是每台机器首次启动时随机生成的，客户端必须事先知道它才谈得上"验证服务端"。
> 这一步无法自动化，也不该自动化——否则任何中间人都能冒充服务端拿到令牌。
> 把固定私钥打进分发包看起来省事，但等于公开私钥，反而更危险。

## 随时重新生成私钥 / 令牌

一条命令，不用手动删文件：

```bash
./regen.sh          # 默认：换新 CA + 服务端证书
./regen.sh token    # 只换访问令牌
./regen.sh all      # 两个都换
```

脚本会自动判断网关是否在运行：运行中就用 `docker compose exec` 直接跑再重启，
没运行就用一次性容器处理。**不需要停机删文件**。

也可以手工调用网关内置的命令：

```bash
# 查看当前配置（只读，不改动任何东西）
docker compose exec tls-gateway python /app/gateway.py --show

# 单独重新生成
docker compose exec tls-gateway python /app/gateway.py --regen-certs
docker compose exec tls-gateway python /app/gateway.py --regen-token
docker compose exec tls-gateway python /app/gateway.py --regen-all
docker compose restart tls-gateway      # 让运行中的网关加载新证书/令牌
```

### 换了之后要同步什么

| 轮换内容 | 客户端需要做什么 |
|---|---|
| 证书 | 重新取 `ca.crt`（`docker compose cp tls-gateway:/state/ca.crt ./ca.crt`），覆盖并重建 PruneMate 容器 |
| 令牌 | 更新 `PRUNEMATE_HOST_TOKEN` 环境变量并重建 PruneMate 容器 |

两者不一致的表现都是连不上：证书不对是 TLS 校验失败，令牌不对是 403。

实测：换证书后旧 CA 立即失效（TLS 握手失败），新 CA 正常；换令牌后旧令牌返回 403，新令牌 200。

## 在 PruneMate 里添加

打开 PruneMate → **Docker 主机** → 展开 → 名称随意，URL 填：

```
tcp://<被管理主机IP>:2375
```

保存后点主机行的 ▶️ 启用，右侧状态点变绿即为连通。
之后「预览并运行」会把外部主机的资源一起列出来，定时清理也会一并处理。

## 开了哪些权限

| 变量 | 用途 |
|---|---|
| `CONTAINERS` | 列容器、`containers/prune` |
| `IMAGES` | 列镜像、`images/prune` |
| `NETWORKS` | 列网络、`networks/prune` |
| `VOLUMES` | 列卷、`volumes/prune` |
| `BUILD` | `build/prune`（构建缓存） |
| `SYSTEM` | `/system/df`，预览里算可回收空间 |
| `POST` | **必须开**，否则所有 prune 都是只读、返回 403 |

`EXEC`、`SECRETS`、`AUTH`、`SWARM`、`SERVICES`、`NODES`、`INFO` 保持关闭，访问这些前缀一律 403。

### ⚠️ 一个容易误解的地方

这个 proxy 的粒度是 **URL 前缀分组**，不是"分组内的最小权限"。实测确认：

```
POST /v1.44/containers/<id>/start   → 304（放行，容器被启动了）
POST /v1.44/containers/<id>/exec    → 400（放行，只是容器 id 不存在）
```

原因是 ACL 里 `^/containers` 命中 `CONTAINERS=1` 就整体放行，
`ALLOW_START` / `ALLOW_STOP` 这些细粒度开关**只在你关闭 `CONTAINERS` 时才起作用**。
PruneMate 必须列容器（判断哪些镜像/卷在被占用），所以 `CONTAINERS` 关不掉。

结论：**它收窄的是"能碰哪些 API 分组"，不是"分组内只能做某一种操作"。**
真正的边界得靠网络隔离，见下面的安全提醒。

## 验证权限边界

```bash
# 应当成功
curl -s http://<IP>:2375/_ping
curl -s http://<IP>:2375/v1.44/containers/json | head -c 100
curl -s http://<IP>:2375/v1.44/system/df | head -c 100

# 应当返回 403（证明没放开）
curl -s -o /dev/null -w '%{http_code}\n' http://<IP>:2375/v1.44/version   # version 默认允许
curl -s -o /dev/null -w '%{http_code}\n' http://<IP>:2375/v1.44/secrets   # 期望 403
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://<IP>:2375/v1.44/exec/xxx/start  # 期望 403
```

## 安全提醒

- 这个端口在权限上**基本等价于该主机的 root**：能删容器、删镜像、删卷，也能创建 exec
- 绝不要映射到公网 / NAT，不要用内网穿透暴露
- **用防火墙只放行 PruneMate 所在主机的 IP**，这是唯一真正有效的边界
- 不需要管理这台主机时就 `docker compose down`，别长期挂着
- 需要更严格的隔离，可以考虑把 proxy 放在独立 Docker 网络里、只让 PruneMate 容器接入，
  而不是用宿主机端口映射
