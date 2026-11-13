#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二遍：推送通知正文 + 计划描述 + 1.4.0 新增 UI 文案"""
import io, os

BASE = os.path.dirname(os.path.abspath(__file__))

def apply(path, pairs):
    s = io.open(path, encoding="utf-8").read()
    miss = []
    for old, new, cnt in pairs:
        n = s.count(old)
        if n == 0 or (cnt is not None and n != cnt):
            miss.append((old[:60], n))
        s = s.replace(old, new)
    io.open(path, "w", encoding="utf-8").write(s)
    print(os.path.relpath(path, BASE), "-> 未匹配:", miss if miss else "无")
    return len(miss)

COMMON_PY = [
    ('return f"daily at {formatted_time} ({tz_name})"',
     'return f"每天 {formatted_time}（{tz_name}）"', 1),
    ('return f"weekly at {day_names.get(day_key, day_key)} {formatted_time} ({tz_name})"',
     'return f"每周{day_names.get(day_key, day_key)} {formatted_time}（{tz_name}）"', 1),
    ('return f"monthly on day {day_of_month} at {formatted_time} ({tz_name})"',
     'return f"每月 {day_of_month} 日 {formatted_time}（{tz_name}）"', 1),
    ('return f"{freq} at {formatted_time} ({tz_name})"',
     'return f"{freq} {formatted_time}（{tz_name}）"', 1),
    ('"mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",\n            "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday",',
     '"mon": "周一", "tue": "周二", "wed": "周三",\n            "thu": "周四", "fri": "周五", "sat": "周六", "sun": "周日",', 1),
    ('send_notification("PruneMate run completed"', 'send_notification("PruneMate 清理完成"', 1),
    ('"message": "Prune job executed successfully." if ran else "Prune job skipped (busy or timeout)."',
     '"message": "清理任务执行成功。" if ran else "清理任务已跳过（正忙或超时）。"', 1),
    ('"PruneMate test notification",', '"PruneMate 测试通知",', 1),
    ('"This is a test message from PruneMate.\\n\\nIf you see this, your current provider settings are working."',
     '"这是来自 PruneMate 的测试消息。\\n\\n如果你看到这条消息，说明当前推送配置有效。"', 1),
]

PY_133 = COMMON_PY + [
    ('summary_lines.append("📊 Per-host results:")', 'summary_lines.append("📊 各主机结果：")', 1),
    ("f\"  - 🗑️ {result['containers']} containers\"", "f\"  - 🗑️ {result['containers']} 个容器\"", 1),
    ("f\"  - 💿 {result['images']} images\"", "f\"  - 💿 {result['images']} 个镜像\"", 1),
    ("f\"  - 🌐 {result['networks']} networks\"", "f\"  - 🌐 {result['networks']} 个网络\"", 1),
    ("f\"  - 📦 {result['volumes']} volumes\"", "f\"  - 📦 {result['volumes']} 个数据卷\"", 1),
    ("f\"  - 🏗️ {result['build_cache']} build caches\"", "f\"  - 🏗️ {result['build_cache']} 项构建缓存\"", 1),
    ("f\"  - 💾 {human_bytes(result['space'])} reclaimed\"", "f\"  - 💾 已释放 {human_bytes(result['space'])}\"", 1),
    ('summary_lines.append(f"• {result[\'name\']}: ✅ Nothing to prune")',
     'summary_lines.append(f"• {result[\'name\']}: ✅ 无需清理")', 1),
    ("summary_lines.append(f\"• {result['name']}: ❌ {result.get('error', 'Unknown error')}\")",
     "summary_lines.append(f\"• {result['name']}: ❌ {result.get('error', '未知错误')}\")", 1),
    ('summary_lines.append("📈 Total across all hosts:")', 'summary_lines.append("📈 全部主机合计：")', 1),
    ('"  - 🗑️ Containers: ', '"  - 🗑️ 容器：', 1),
    ('"  - 💿 Images: ', '"  - 💿 镜像：', 1),
    ('"  - 🌐 Networks: ', '"  - 🌐 网络：', 1),
    ('"  - 📦 Volumes: ', '"  - 📦 数据卷：', 1),
    ('"  - 🏗️ Build caches: ', '"  - 🏗️ 构建缓存：', 1),
    ('"  - 💾 Space reclaimed: ', '"  - 💾 已释放空间：', 1),
    ('summary_lines.append("✅ Nothing to prune this run")', 'summary_lines.append("✅ 本次无需清理")', 1),
]

PY_140 = COMMON_PY + [
    ('f"Schedule: {describe_schedule()}"', 'f"计划：{describe_schedule()}"', 1),
    ('summary_lines.append("Results by host")', 'summary_lines.append("各主机结果")', 1),
    ('"  - Containers: ', '"  - 容器：', 2),
    ('"  - Images: ', '"  - 镜像：', 2),
    ('"  - Networks: ', '"  - 网络：', 2),
    ('"  - Volumes: ', '"  - 数据卷：', 2),
    ('"  - Build caches: ', '"  - 构建缓存：', 2),
    ('"  - Space reclaimed: ', '"  - 已释放空间：', 2),
    ('f"{result[\'name\']}: Nothing to prune"', 'f"{result[\'name\']}：无需清理"', 1),
    ("f\"{result['name']}: Error - {result.get('error', 'Unknown error')}\"",
     "f\"{result['name']}：出错 - {result.get('error', '未知错误')}\"", 1),
    ('summary_lines.append("Totals across all hosts")', 'summary_lines.append("全部主机合计")', 1),
    ('summary_lines.append("Nothing to prune in this run")', 'summary_lines.append("本次无需清理")', 1),
]

IDX_140 = [
    ('</svg>Time</label>', '</svg>时间</label>', 1),
    ('PruneMate · 2026 · V1.3.3 · ', 'PruneMate · 2026 · V1.4.0 · ', 1),
    ("statusDot.title = host.enabled ? 'Checking Docker connection...' : 'Disabled';",
     "statusDot.title = host.enabled ? '正在检测 Docker 连接…' : '已停用';", 1),
    ("online: { color: '#22c55e', title: 'Online' }", "online: { color: '#22c55e', title: '在线' }", 1),
    ("offline: { color: '#ef4444', title: 'Offline: Docker ping failed' }",
     "offline: { color: '#ef4444', title: '离线：Docker ping 失败' }", 1),
    ("disabled: { color: '#6b7280', title: 'Disabled' }", "disabled: { color: '#6b7280', title: '已停用' }", 1),
    ("dot.title = 'Status unavailable'", "dot.title = '状态不可用'", 1),
    ("throw new Error('Failed to check Docker hosts')", "throw new Error('检查 Docker 主机失败')", 1),
]

rc = 0
rc += apply(os.path.join(BASE, "zh", "prunemate.py"), PY_133)
rc += apply(os.path.join(BASE, "zh-1.4.0", "prunemate.py"), PY_140)
rc += apply(os.path.join(BASE, "zh-1.4.0", "index.html"), IDX_140)
print("TOTAL_MISSING=%d" % rc)
