#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PruneMate V1.3.3 简体中文本地化 - 精确字符串替换（带出现次数校验）"""
import sys, io, os

BASE = os.path.dirname(os.path.abspath(__file__))

def apply(path, pairs):
    with io.open(path, encoding="utf-8") as f:
        src = f.read()
    orig = src
    missing = []
    for old, new, cnt in pairs:
        n = src.count(old)
        if n == 0:
            missing.append((old[:70], cnt))
            continue
        if cnt is not None and n != cnt:
            missing.append((old[:70], "expected %s got %s" % (cnt, n)))
        src = src.replace(old, new)
    if missing:
        print("!! 未匹配/次数不符 in %s" % path)
        for m in missing:
            print("   ", m)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("%s: %d -> %d bytes, %d 处替换规则" % (os.path.basename(path), len(orig), len(src), len(pairs)))
    return len(missing)

IDX = [
    # ---- head ----
    ('<html lang="en">', '<html lang="zh-CN">', 1),
    ('<title>PruneMate - Docker cleanup helper</title>', '<title>PruneMate · Docker 清理助手</title>', 1),
    # ---- 头部/logo ----
    ('aria-label="Close"', 'aria-label="关闭"', 1),
    ('title="Visit PruneMate Documentation"', 'title="访问 PruneMate 官方文档"', 1),
    ('title="Logout"', 'title="退出登录"', 1),
    ('<span>Logout</span>', '<span>退出</span>', 1),
    ('alt="prunemate logo"', 'alt="PruneMate 标志"', 1),
    ('<p>Docker image & resource cleanup helper, on a schedule!</p>',
     '<p>定时清理 Docker 镜像与资源的小助手！</p>', 1),
    # ---- 统计卡片 ----
    ('All-Time Statistics', '累计统计', 1),
    ('Loading statistics...', '正在加载统计数据…', 1),
    ('Total Reclaimed', '累计释放', 1),
    ('Prune Runs</div>', '清理次数</div>', 1),
    ('Containers</div>', '容器</div>', 2),
    ('Images</div>', '镜像</div>', 2),
    ('Networks</div>', '网络</div>', 2),
    ('Volumes</div>', '数据卷</div>', 2),
    ('Build Cache</div>', '构建缓存</div>', 2),
    ('First Run', '首次运行', 1),
    ('Last Run', '上次运行', 1),
    ('Failed to load statistics', '统计数据加载失败', 1),
    # ---- 计划 ----
    ('<h2>Schedule</h2>', '<h2>清理计划</h2>', 1),
    ('Enable automatic schedule', '启用自动定时清理', 1),
    ('<label for="frequency">Frequency</label>', '<label for="frequency">频率</label>', 1),
    ('aria-label="Frequency"', 'aria-label="频率"', 1),
    ('>Daily</option>', '>每天</option>', 1),
    ('>Weekly</option>', '>每周</option>', 1),
    ('>Monthly</option>', '>每月</option>', 1),
    ('<label for="time">Time</label>', '<label for="time">时间</label>', 1),
    ("('mon', 'Monday')", "('mon', '周一')", 1),
    ("('tue', 'Tuesday')", "('tue', '周二')", 1),
    ("('wed', 'Wednesday')", "('wed', '周三')", 1),
    ("('thu', 'Thursday')", "('thu', '周四')", 1),
    ("('fri', 'Friday')", "('fri', '周五')", 1),
    ("('sat', 'Saturday')", "('sat', '周六')", 1),
    ("('sun', 'Sunday')", "('sun', '周日')", 1),
    ('Day of the week', '星期几', 1),
    ('Day of the month', '每月几号', 1),
    ('Using Timezone: {{ timezone }}', '当前时区：{{ timezone }}', 1),
    ("Time format: {{ '24-hour' if use_24h else '12-hour (AM/PM)' }}",
     "时间格式：{{ '24 小时制' if use_24h else '12 小时制 (AM/PM)' }}", 1),
    # ---- 清理选项 ----
    ('<h2>Cleanup options</h2>', '<h2>清理选项</h2>', 1),
    ('All unused containers', '所有未使用的容器', 1),
    ('All unused images', '所有未使用的镜像', 1),
    ('All unused networks', '所有未使用的网络', 1),
    ('All unused volumes', '所有未使用的数据卷', 1),
    ('All build cache', '所有构建缓存', 1),
    # ---- Docker 主机 ----
    ('<h2>Docker Hosts</h2>', '<h2>Docker 主机</h2>', 1),
    ('<strong>External Docker hosts</strong>', '<strong>外部 Docker 主机</strong>', 1),
    ('Connect to remote Docker hosts via TCP docker-socket-proxy',
     '通过 TCP docker-socket-proxy 连接远程 Docker 主机', 1),
    ('Add external Docker hosts using ', '使用 ', 1),
    ('</code>. <strong>This function requires a ', '</code> 添加外部 Docker 主机。<strong>该功能需要在每台远程主机上运行 ', 1),
    ('</a> container running on each remote host.</strong> See the ',
     '</a> 容器。</strong>示例 compose 配置请参见 ', 1),
    ('</a> for an example docker-compose.yaml for the docker-socket-proxy.',
     '</a>。', 1),
    ('>Add New Host</h3>', '>添加新主机</h3>', 1),
    ('<label for="new-host-name">Name</label>', '<label for="new-host-name">名称</label>', 1),
    ('<label for="new-host-url">URL</label>', '<label for="new-host-url">地址</label>', 1),
    ('placeholder="Server 1"', 'placeholder="服务器 1"', 1),
    ('>Add Host</button>', '>添加主机</button>', 1),
    # ---- 通知 ----
    ('<h2>Notifications</h2>', '<h2>通知</h2>', 1),
    ('<strong>Notification settings</strong>', '<strong>通知设置</strong>', 1),
    ('Select provider & configure fields', '选择推送服务并填写参数', 1),
    ('<label for="notifications_provider">Provider</label>', '<label for="notifications_provider">推送服务</label>', 1),
    ('aria-label="Notification provider"', 'aria-label="通知推送服务"', 1),
    ('<label for="notification_priority">Priority</label>', '<label for="notification_priority">优先级</label>', 1),
    ('aria-label="Notification priority"', 'aria-label="通知优先级"', 1),
    ('>Low</option>', '>低</option>', 1),
    ('>Medium</option>', '>中</option>', 1),
    ('>High</option>', '>高</option>', 1),
    ('Only notify when something was pruned', '仅在有清理内容时通知', 1),
    ('*When disabled, PruneMate sends a notification after every run.',
     '*关闭后，PruneMate 每次运行都会发送通知。', 1),
    ('Enable Gotify notifications', '启用 Gotify 通知', 1),
    ('<label for="gotify_url">Gotify URL :</label>', '<label for="gotify_url">Gotify 地址：</label>', 1),
    ('aria-label="Gotify server URL"', 'aria-label="Gotify 服务器地址"', 1),
    ('placeholder="App token"', 'placeholder="应用令牌"', 1),
    ('aria-label="Gotify application token"', 'aria-label="Gotify 应用令牌"', 1),
    ('Enable ntfy notifications', '启用 ntfy 通知', 1),
    ('<label for="ntfy_url">ntfy URL :</label>', '<label for="ntfy_url">ntfy 地址：</label>', 1),
    ('aria-label="ntfy server URL"', 'aria-label="ntfy 服务器地址"', 1),
    ('<label for="ntfy_topic">ntfy Topic :</label>', '<label for="ntfy_topic">ntfy 主题：</label>', 1),
    ('aria-label="ntfy topic name"', 'aria-label="ntfy 主题名称"', 1),
    ('<label for="ntfy_token">ntfy Token (optional) :</label>', '<label for="ntfy_token">ntfy 令牌（可选）：</label>', 1),
    ('placeholder="Bearer token (optional)"', 'placeholder="Bearer 令牌（可选）"', 1),
    ('aria-label="ntfy bearer token"', 'aria-label="ntfy Bearer 令牌"', 1),
    ('Enable Discord notifications', '启用 Discord 通知', 1),
    ('aria-label="Discord webhook URL"', 'aria-label="Discord Webhook 地址"', 1),
    ('Enable Telegram notifications', '启用 Telegram 通知', 1),
    ('aria-label="Telegram bot token from @BotFather"', 'aria-label="来自 @BotFather 的 Telegram 机器人令牌"', 1),
    ('aria-label="Telegram chat ID or channel username"', 'aria-label="Telegram 会话 ID 或频道用户名"', 1),
    ('placeholder="123456789 or @channelname"', 'placeholder="123456789 或 @频道名"', 1),
    ('Send test notification', '发送测试通知', 1),
    # ---- 按钮/页脚 ----
    ('Save &amp; Schedule', '保存并应用计划', 1),
    ('Run now', '立即运行', 1),
    ('Preview & Run', '预览并运行', 1),
    ('PruneMate · 2026 · V1.3.3 · ', 'PruneMate · 2026 · V1.3.3 · ', 1),
    # ---- 预览弹窗 ----
    ('🔍 Prune Preview', '🔍 清理预览', 1),
    ('Loading preview...', '正在加载预览…', 2),
    ('>Cancel</button>', '>取消</button>', 2),
    ('✓ Confirm & Execute', '✓ 确认并执行', 2),
    # ---- JS: 主机管理 ----
    ('Failed to load hosts', '主机列表加载失败', 1),
    ("alert('Failed to toggle host: '", "alert('切换主机状态失败：'", 1),
    ("'Unknown error'", "'未知错误'", 3),
    ("alert('Failed to toggle host')", "alert('切换主机状态失败')", 1),
    ("prompt('Host name:', host.name)", "prompt('主机名称：', host.name)", 1),
    ("prompt('Host URL:', host.url)", "prompt('主机地址：', host.url)", 1),
    ('Are you sure you want to delete host "${hostName}"?', '确定要删除主机 "${hostName}" 吗？', 1),
    ("alert('Please enter both host name and URL')", "alert('请填写主机名称和地址')", 1),
    ("host.enabled ? 'Enabled' : 'Disabled'", "host.enabled ? '已启用' : '已停用'", 1),
    ("toggleBtn.title = host.enabled ? 'Disable' : 'Enable'", "toggleBtn.title = host.enabled ? '停用' : '启用'", 1),
    ("editBtn.title = 'Edit'", "editBtn.title = '编辑'", 1),
    ("deleteBtn.title = 'Delete'", "deleteBtn.title = '删除'", 1),
    # ---- JS: 预览渲染 ----
    ('Nothing to prune!', '没有需要清理的内容！', 1),
    ('Your Docker resources are already clean.', '你的 Docker 资源已经很干净了。', 1),
    ('📊 Summary', '📊 汇总', 1),
    ('🗑️ Containers (', '🗑️ 容器 (', 1),
    ('💿 Images (', '💿 镜像 (', 1),
    ('🌐 Networks (', '🌐 网络 (', 1),
    ('📦 Volumes (', '📦 数据卷 (', 1),
    ('🏗️ Build Cache (', '🏗️ 构建缓存 (', 1),
    ("... and '", "... 另有 '", 3),
    ("' more</div>'", "' 项</div>'", 3),
    ("'Failed to connect'", "'连接失败'", 1),
    ('Failed to load preview', '预览加载失败', 1),
    ('⏳ Executing...', '⏳ 执行中…', 1),
    ('Prune completed successfully!', '清理执行成功！', 1),
    ('Check the logs for detailed results.', '详细结果请查看日志。', 1),
    ('>Close</button>', '>关闭</button>', 1),
    ('Execution failed', '执行失败', 1),
]

LOGIN = [
    ('<html lang="en">', '<html lang="zh-CN">', 1),
    ('<title>Login - PruneMate</title>', '<title>登录 · PruneMate</title>', 1),
    ('<h1>Sign in to PruneMate</h1>', '<h1>登录 PruneMate</h1>', 1),
    ('<p class="subtitle">Authentication required to continue</p>',
     '<p class="subtitle">需要身份验证才能继续</p>', 1),
    ('<label for="username">Username</label>', '<label for="username">用户名</label>', 1),
    ('<label for="password">Password</label>', '<label for="password">密码</label>', 1),
    ('<button type="submit" class="btn">Sign In</button>',
     '<button type="submit" class="btn">登 录</button>', 1),
]

PY = [
    ('flash("Invalid credentials", "error")', 'flash("用户名或密码错误", "error")', 1),
    ('flash("Configuration updated.", "success")', 'flash("配置已更新。", "success")', 1),
    ('flash("Prune job executed manually." if ran else "Prune job skipped (busy or timeout).", "info")',
     'flash("已手动执行清理任务。" if ran else "清理任务已跳过（正忙或超时）。", "info")', 1),
    ('flash("Configuration saved. " + ("Test notification sent." if ok else "Test notification failed (check settings & logs)."), "info")',
     'flash("配置已保存。" + ("测试通知已发送。" if ok else "测试通知发送失败（请检查设置与日志）。"), "info")', 1),
    ('flash("Host name and URL are required.", "warn")', 'flash("主机名称和地址为必填项。", "warn")', 2),
    ('flash("URL must start with tcp://, http://, or https://", "warn")',
     'flash("地址必须以 tcp://、http:// 或 https:// 开头", "warn")', 2),
    ('flash(f"Docker host \'{name}\' added successfully.", "info")',
     'flash(f"Docker 主机「{name}」添加成功。", "info")', 1),
    ('flash("Invalid host index.", "warn")', 'flash("主机索引无效。", "warn")', 2),
    ('flash(f"Docker host \'{name}\' updated successfully.", "info")',
     'flash(f"Docker 主机「{name}」已更新。", "info")', 1),
    ('flash(f"Docker host \'{deleted_name}\' deleted successfully.", "info")',
     'flash(f"Docker 主机「{deleted_name}」已删除。", "info")', 1),
]

rc = 0
rc += apply(os.path.join(BASE, "index.html"), IDX)
rc += apply(os.path.join(BASE, "login.html"), LOGIN)
rc += apply(os.path.join(BASE, "prunemate.py"), PY)
print("MR_MISSING=%d" % rc)
sys.exit(0)
