#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「保存并应用计划」和「预览并运行」放到同一行，等高"""
import io, os

BASE = os.path.dirname(os.path.abspath(__file__))

CSS = """    .action-row{display:flex;align-items:stretch;gap:10px;margin-top:10px;flex-wrap:wrap}
    .action-row .btn{margin:0}
"""

OLD_SAVE = """      <!-- Save and schedule button -->
      <div style="margin-top: 10px;">
        <button type="submit" class="btn btn-primary">
          保存并应用计划
        </button>
      </div>
    </form>"""

NEW_SAVE = """      <!-- 操作按钮：保存 / 预览，同一行等高 -->
      <div class="action-row">
        <button type="submit" class="btn btn-primary">
          保存并应用计划
        </button>
        <button type="button" class="btn btn-secondary" onclick="showPrunePreview()">
          预览并运行
        </button>
      </div>
    </form>"""

OLD_PREVIEW = """
    <!-- Manual prune with preview -->
    <div style="margin-top: 6px;">
      <button type="button" class="btn btn-secondary" onclick="showPrunePreview()">
        预览并运行
      </button>
    </div>
"""

CSS_ANCHOR = "    .option-block{padding:6px 0 2px;border-bottom:1px solid var(--card-border)}\n"

for rel in ("zh-1.4.0/index.html", "zh/index.html"):
    p = os.path.join(BASE, rel)
    s = io.open(p, encoding="utf-8").read()
    if ".action-row" in s:
        print(rel, "已处理过，跳过")
        continue
    n1, n2, n3 = s.count(OLD_SAVE), s.count(OLD_PREVIEW), s.count(CSS_ANCHOR)
    if n1 != 1 or n2 != 1 or n3 != 1:
        print(rel, "!! 锚点异常", n1, n2, n3)
        continue
    s = s.replace(OLD_SAVE, NEW_SAVE, 1)
    s = s.replace(OLD_PREVIEW, "", 1)
    s = s.replace(CSS_ANCHOR, CSS + CSS_ANCHOR, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print(rel, "OK", len(s), "字节")
