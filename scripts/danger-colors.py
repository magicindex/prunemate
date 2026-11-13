#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预览/危险按钮改红；风险提示文案与标签配色统一"""
import io, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(BASE, "src", "index.html")

s = io.open(P, encoding="utf-8").read()
miss = []

# 1) 变量：暗/亮两套危险与警告文字色
if "--danger-text" not in s:
    old = "      --btn-elev: 0 10px 30px rgba(16,185,129,0.15);\n"
    new = old + "      --danger-text:#f87171;\n      --warn-text:#fbbf24;\n"
    if s.count(old) == 1:
        s = s.replace(old, new, 1)
    else:
        miss.append("dark vars")

    old_l = "      --btn-elev:0 10px 26px rgba(22,163,74,0.20);\n"
    new_l = old_l + "      --danger-text:#b91c1c;\n      --warn-text:#a16207;\n"
    if s.count(old_l) == 1:
        s = s.replace(old_l, new_l, 1)
    else:
        miss.append("light vars")

# 2) 危险按钮样式 + 选项说明配色
css_anchor = "    .tag-ok{background:rgba(34,197,94,0.12);color:#34d399;border:1px solid rgba(34,197,94,0.28)}\n"
css_add = css_anchor + """    /* 危险操作按钮（清理预览/确认执行） */
    .btn-danger{background:linear-gradient(90deg,#ef4444,#dc2626);color:#fff;
      box-shadow:0 10px 30px rgba(239,68,68,0.18);padding:7px 20px 9px 20px}
    .btn-danger:hover{transform:translateY(-2px);box-shadow:0 18px 44px rgba(239,68,68,0.24)}
    .btn-danger:active{transform:translateY(1px);box-shadow:0 2px 10px rgba(239,68,68,0.18)}
    /* 风险说明文字：与标签同色系 */
    .option-hint.is-warn{color:var(--warn-text)}
    .option-hint.is-danger{color:var(--danger-text)}
"""
if ".btn-danger" not in s:
    if s.count(css_anchor) == 1:
        s = s.replace(css_anchor, css_add, 1)
    else:
        miss.append("css anchor")

# 3) 按钮类替换
pairs = [
    ('<button type="button" class="btn btn-secondary" onclick="showPrunePreview()">',
     '<button type="button" class="btn btn-danger" onclick="showPrunePreview()">', 1),
    ('class="btn btn-secondary" id="confirmPruneBtn"',
     'class="btn btn-danger" id="confirmPruneBtn"', 2),
    ('<div class="option-hint"><span class="tag tag-warn">',
     '<div class="option-hint is-warn"><span class="tag tag-warn">', 2),
    ('<div class="option-hint"><span class="tag tag-danger">',
     '<div class="option-hint is-danger"><span class="tag tag-danger">', 1),
]
for old, new, cnt in pairs:
    n = s.count(old)
    if n != cnt:
        miss.append("%s (期望 %d 实际 %d)" % (old[:40], cnt, n))
        continue
    s = s.replace(old, new)

if miss:
    print("!! 未完成:", miss)
    sys.exit(1)

io.open(P, "w", encoding="utf-8").write(s)
print("index.html 已更新:", len(s), "字节")
print("  btn-danger 用法:", s.count("btn btn-danger"))
print("  is-warn:", s.count("option-hint is-warn"), "| is-danger:", s.count("option-hint is-danger"))
