# PruneMate 单机版（飞牛 fnOS 应用）

**只清理本机 Docker** 的精简版本。不含外部主机、网关、令牌、证书与相关接口，
也不额外开放端口——比完整版更小的攻击面。

<h2 align="center">⚠️ 安全警示</h2>

<div style="border:2px solid #dc2626;background:#fef2f2;border-radius:12px;padding:16px 20px;color:#b91c1c;line-height:1.9;">

**1. 本质仍是宿主机 root 权限**

本程序挂载 `/var/run/docker.sock`，容器内以 root 运行。**能控制它 = 能控制整台宿主机**。

**2. 只在内网使用**

不要做端口转发、内网穿透、公网映射；建议绑定内网网卡并配合防火墙限制来源。

**3. 首次登录立即改密码**

默认账号 `admin` / `LitKgI13KWYI1a` —— **安装后请立即修改密码**，Web 被弱口令攻破等同于宿主机被接管。

</div>

## 与完整版的区别

| | 单机版 `prunemate-lite.fpk` | 完整版 `prunemate.fpk` |
|---|---|---|
| 清理本机 Docker | ✅ | ✅ |
| 定时任务 / 预览 / 通知 / 统计 | ✅ | ✅ |
| 中文界面 / 亮色主题 | ✅ | ✅ |
| 管理外部 Docker 主机 | ❌ 代码已移除 | ✅ |
| 访问令牌 / CA 证书 | ❌ 代码已移除 | ✅ |
| 对外端口 | 仅 7676 | 7676 + 网关 2376/2377 |

单机版的 `/hosts*` 接口、令牌与 CA 处理、外部主机客户端构造**全部不存在**，
不是靠开关关闭，而是构建时从源码删除。

## 安装

应用中心上传 `prunemate-lite.fpk`，安装后访问 `http://<NAS>:7676`。

与完整版**互斥安装**：两者都用 7676 端口和同名容器，装之前请先卸载另一个。

## 目录

```
app/docker/
├── docker-compose.yaml
├── README.md
└── zh/            生成的中文界面与后端（构建时从主源码裁剪）
```

数据目录：`/var/apps/prunemate-lite/shares/prunemate-lite/`（配置、日志、统计）。

## 许可证

程序与图标 © anoniemerd，AGPL-3.0；打包发布 cyberzero，与上游无隶属关系。
