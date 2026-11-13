# PruneMate 网关（飞牛 fnOS 应用）

<h2 align="center">⚠️ 安全警示</h2>

<div style="border:2px solid #dc2626;background:#fef2f2;border-radius:12px;padding:16px 20px;color:#b91c1c;line-height:1.9;">

**1. 2376 端口等价于被管理主机的容器层 root**

网关把 Docker API 暴露给网络。白名单已把可调用范围收窄到「列举 + prune」，
拿不到 shell、改不了容器状态，但**仍能删掉停止的容器与未使用镜像**。

**2. 只允许内网使用**

- 不要做端口转发、内网穿透、公网映射
- 用防火墙只允许 PruneMate 所在主机的 IP 访问 2376
- 最稳妥：平时停掉应用，需要清理时再启动

**3. 单机使用者不需要安装本包**

如果 PruneMate 只管理它自己那台机器，**不要装网关**，本包可以完全不装。

**4. 本包以 root 进程运行**

读取 `/var/run/docker.sock` 需要权限，所以进程以 root 启动，没有容器 namespace 隔离。
权限层面它本来就要代理 Docker API，等价；真正的边界是网络 + 令牌。

**5. 凭证位置与轮换**

令牌与 CA 在共享目录 `@appshare/prunemate-gateway/`，**重装会重新生成**，
届时需在 PruneMate 侧同步更新。

</div>

独立于 PruneMate 主应用的配套组件，**装在被管理的 Docker 主机上**，让其他机器上的
PruneMate 能安全地管理这台主机的 Docker。

两个包互不依赖、可单独安装/卸载：

| 包 | 装在哪 | 作用 |
|---|---|---|
| `prunemate.fpk` | 管理端 | 清理助手本体（定时清理、预览、通知） |
| `prunemate-gateway.fpk` | 被管理端 | 对外提供受控的 Docker API 通道 |

## 装完就能用

安装后自动启动，**首次启动会自动生成**：

- 自签 CA 与服务端证书（证书里自动写入本机全部 IPv4 地址）
- 64 位随机访问令牌

不需要跑任何脚本，也不需要改配置文件。

## 为什么不用容器

早期版本用容器跑，但要在目标机拉取基础镜像，镜像源受限时安装会直接失败。
现在网关**直接运行在主机上**（纯 Python 标准库 + 系统自带的 openssl），
不依赖任何镜像，也不占用 Docker 的 compose 项目。

```
PruneMate ──https + 令牌──> 网关(2376) ──unix socket──> dockerd
```

接口白名单在网关内部实现，因此也不需要中间那层 docker-socket-proxy 容器。

## 取客户端配置

**最简单：文件管理器打开共享目录 `prunemate-gateway`**

安装包声明了数据共享目录，网关启动时会把三样东西写进去：

```
/vol1/@appshare/prunemate-gateway/
├── client-info.txt   地址 + 令牌 + 用法（直接打开看）
├── token.txt         只有令牌
└── ca.crt            给 PruneMate 侧粘贴
```

在飞牛「文件管理」里找 **`vol1 > @appshare > prunemate-gateway`** 即可，不需要 shell。

> 注意：`@appcenter > prunemate-gateway > config` 与 `.../gateway` 是安装包自身的文件，
> **证书和令牌只在 `@appshare > prunemate-gateway` 这一处**。

另外：浏览器打开 `http://<这台机器IP>:2377/` 也能下载 CA（但页面不显示令牌）

- 页面提供 `ca.crt` 下载（公开证书，可安全分发）
- 页面**不显示令牌**，令牌请从容器日志或 `docker/public/token.txt` 取

也可以用命令：

```bash
docker exec prunemate-gateway python /app/gateway.py --show
```

输出形如：

```
主机地址: https://192.168.1.10:2376
环境变量: PRUNEMATE_HOST_TOKEN=3bd9aa42...
CA 文件 : /state/ca.crt
```

把 CA 取出来：

```bash
docker cp prunemate-gateway:/state/ca.crt ./ca.crt
```

然后在 PruneMate 那一侧：

```yaml
environment:
  - PRUNEMATE_HOST_TOKEN=<上面那串>
  - REQUESTS_CA_BUNDLE=/certs/ca.crt
volumes:
  - ./ca.crt:/certs/ca.crt:ro
```

页面里「Docker 主机」填 `https://<本机IP>:2376`。

## 从日志里取 CA 与令牌

容器日志开头就是完整配置：

```bash
docker logs prunemate-gateway | head -40
```

会打印令牌和**完整的 CA 证书**（PEM，整段可直接复制）。在飞牛的容器管理界面里点开
「日志」也能看到同一段，不需要 shell。

### 日志会被外发时的处理

CA 是公开证书，写进日志没有风险；**令牌属于凭据**。如果这台机器的日志会被采集或发到
第三方（比如接了日志系统），建议关掉令牌输出：

```bash
HIDE_TOKEN_IN_LOG=1 docker compose up -d
```

关掉后日志只显示令牌位置提示，令牌仍可用 `--show` 或 `public/token.txt` 获取。

## 复制令牌的注意事项

日志里的令牌是**单独一行**，两边有分隔标记：

```
  ---- 访问令牌（整段复制这一行）----
  b3e81305b0c6aa99976eb1e2ebdfe8cb8a152ebd5a9f8ddec01f0328b9e73fab
  ---- 令牌结束 ----
```

复制时带上换行或缩进没关系——PruneMate 侧会自动去掉空白字符和 `访问令牌:` 之类的前缀，
网关自身也容忍请求头里的空白。

## 随时换私钥 / 令牌

```bash
docker exec prunemate-gateway python /app/gateway.py --regen-certs
docker exec prunemate-gateway python /app/gateway.py --regen-token
docker exec prunemate-gateway python /app/gateway.py --regen-all
docker restart prunemate-gateway      # 让新证书/令牌生效
```

换了证书要重取 `ca.crt`；换了令牌要更新 PruneMate 的环境变量。

## 端口与权限

| 端口 | 绑定 | 用途 |
|---|---|---|
| 2376 | 0.0.0.0 | 对外的 TLS 网关（唯一暴露面） |
| 2375 | 127.0.0.1 | 内层 socket-proxy，仅本机可达 |

放行的是**方法 + 路径白名单**，只保留 PruneMate 实际调用的端点：

```
GET  /_ping  /version
GET  /containers/json  /images/json  /networks  /system/df
POST /containers/prune  /images/prune  /networks/prune  /build/prune
```

其余全部 403，包括 `/containers/{id}/start|stop|exec`、`/containers/create`、
`DELETE /containers/{id}`、`DELETE /images/{id}`、`/secrets`、`/swarm`、`/info`。

**数据卷清理默认不开放**（`volumes` 端点未放行）。确需开启：
在 `haproxy.cfg.template` 里取消 `volumes` 两行注释，并把 compose 的 `VOLUMES` 改成 `1`。

> ⚠️ 2376 在权限上基本等价于本机 root。务必只放内网，不要做端口转发或内网穿透，
> 并建议用防火墙只允许 PruneMate 所在主机的 IP 访问。详见 `app/docker/README.md`。

## 目录

```
app/docker/
├── docker-compose.yml   # socket-proxy + TLS 网关
├── Dockerfile.gateway
├── gateway.py           # 网关本体（纯 Python 标准库）
├── regen.sh             # 轮换辅助脚本
└── README.md            # 详细说明（部署、验证、安全边界）
```

状态目录：`/var/apps/prunemate-gateway/shares/state`（证书、私钥、令牌）。

## 许可证

网关代码 AGPL-3.0；内层使用 [Tecnativa/docker-socket-proxy](https://github.com/Tecnativa/docker-socket-proxy) v0.5.0（Apache-2.0）。
