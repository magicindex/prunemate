#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给「清理选项」5 个开关增加说明与推荐等级"""
import io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))

CSS = """    .option-block{padding:6px 0 2px;border-bottom:1px solid var(--card-border)}
    .option-block:last-child{border-bottom:none;padding-bottom:0}
    .option-hint{font-size:0.76rem;color:var(--muted);line-height:1.55;margin:0 0 8px;padding-right:4px}
    .option-hint .tag{display:inline-block;font-size:0.68rem;font-weight:700;padding:1px 6px;
      border-radius:5px;margin-right:6px;vertical-align:1px;white-space:nowrap}
    .tag-warn{background:rgba(251,191,36,0.14);color:#fbbf24;border:1px solid rgba(251,191,36,0.28)}
    .tag-danger{background:rgba(239,68,68,0.14);color:#f87171;border:1px solid rgba(239,68,68,0.30)}
    .tag-ok{background:rgba(34,197,94,0.12);color:#34d399;border:1px solid rgba(34,197,94,0.28)}
"""

BLOCK = """<h2>清理选项</h2>
      <div class="card">
        <!-- 容器 -->
        <div class="option-block">
          <div class="toggle-row">
            <span class="label-text">所有未使用的容器</span>
            <label class="switch">
              <input type="checkbox" name="prune_containers" id="prune_containers"
                     {% if config.prune_containers %}checked{% endif %}>
              <span class="slider"></span>
            </label>
          </div>
          <div class="option-hint"><span class="tag tag-warn">建议关闭</span>只删除<b>已停止</b>的容器，运行中的不受影响。停止的容器里未保存的改动会一起消失，确认没有需要保留的停止状态容器再打开。</div>
        </div>

        <!-- 镜像 -->
        <div class="option-block">
          <div class="toggle-row">
            <span class="label-text">所有未使用的镜像</span>
            <label class="switch">
              <input type="checkbox" name="prune_images" id="prune_images"
                     {% if config.prune_images %}checked{% endif %}>
              <span class="slider"></span>
            </label>
          </div>
          <div class="option-hint"><span class="tag tag-warn">谨慎开启</span>删除<b>所有没有容器在用</b>的镜像，带标签的也删——比 docker 自带的悬空镜像清理更彻底。删掉旧版本镜像后无法回滚，建议先点「预览并运行」看清楚清单。</div>
        </div>

        <!-- 网络 -->
        <div class="option-block">
          <div class="toggle-row">
            <span class="label-text">所有未使用的网络</span>
            <label class="switch">
              <input type="checkbox" name="prune_networks" id="prune_networks"
                     {% if config.prune_networks %}checked{% endif %}>
              <span class="slider"></span>
            </label>
          </div>
          <div class="option-hint"><span class="tag tag-ok">建议开启</span>删除没有容器连接的 bridge 网络，自定义网络也在内。compose 下次启动容器时会自动重建，基本没有影响。</div>
        </div>

        <!-- 数据卷 -->
        <div class="option-block">
          <div class="toggle-row">
            <span class="label-text">所有未使用的数据卷</span>
            <label class="switch">
              <input type="checkbox" name="prune_volumes" id="prune_volumes"
                     {% if config.prune_volumes %}checked{% endif %}>
              <span class="slider"></span>
            </label>
          </div>
          <div class="option-hint"><span class="tag tag-danger">强烈建议关闭</span>删除<b>所有</b>未挂载到容器的数据卷，卷里的数据<b>永久丢失</b>、无法恢复。容器停止、升级或 compose down 期间，它的卷都会变成"未引用"，下一次定时任务就会被清掉——本机历史上已经删掉 120 个卷。</div>
        </div>

        <!-- 构建缓存 -->
        <div class="option-block">
          <div class="toggle-row">
            <span class="label-text">所有构建缓存</span>
            <label class="switch">
              <input type="checkbox" name="prune_build_cache" id="prune_build_cache"
                     {% if config.prune_build_cache %}checked{% endif %}>
              <span class="slider"></span>
            </label>
          </div>
          <div class="option-hint"><span class="tag tag-ok">建议开启</span>清理 BuildKit 构建缓存，只影响下次构建的速度，不影响运行中的容器和已有镜像。</div>
        </div>
      </div>

      """

START = "<h2>清理选项</h2>"
END = "<!-- Docker Hosts Management Section -->"
CSS_ANCHOR = "    .toggle-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:5px 0}\n"

for rel in ("zh-1.4.0/index.html", "zh/index.html"):
    p = os.path.join(BASE, rel)
    s = io.open(p, encoding="utf-8").read()
    if ".option-block" in s:
        print(rel, "已处理过，跳过")
        continue
    i, j = s.find(START), s.find(END)
    if i < 0 or j < 0 or j < i:
        print(rel, "!! 锚点缺失", i, j)
        continue
    s = s[:i] + BLOCK + s[j:]
    if CSS_ANCHOR not in s:
        print(rel, "!! CSS 锚点缺失")
        continue
    s = s.replace(CSS_ANCHOR, CSS_ANCHOR + CSS, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print(rel, "OK", len(s), "字节")
