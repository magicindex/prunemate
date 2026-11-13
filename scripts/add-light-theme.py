#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 PruneMate 增加亮色主题（变量覆盖 + 组件修复 + 切换按钮）"""
import io, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "src")

LIGHT_CSS = """    /* ==================== 亮色主题 ==================== */
    html[data-theme="light"]{
      --bg-900:#f7f9fc;
      --bg-800:#eef3f9;
      --accent:#0284c7;
      --accent-strong:#16a34a;
      --accent-soft:rgba(2,132,199,0.10);
      --muted:#5b6879;
      --text:#0f172a;
      --card-border:rgba(15,23,42,0.08);
      --glass-border:rgba(15,23,42,0.10);
      --focus:0 6px 24px rgba(2,132,199,0.16);
      --shadow-strong:0 24px 60px rgba(15,23,42,0.14);
      --btn-elev:0 10px 26px rgba(22,163,74,0.20);
    }
    html[data-theme="light"] body{
      background:
        radial-gradient(600px 300px at 12% 6%, rgba(2,132,199,0.10), transparent 22%),
        linear-gradient(135deg, var(--bg-900), var(--bg-800));
    }
    html[data-theme="light"] .container{
      background:linear-gradient(180deg, rgba(255,255,255,0.97), rgba(248,250,253,0.97));
      box-shadow:var(--shadow-strong), 0 4px 14px rgba(15,23,42,0.06);
    }
    html[data-theme="light"] .container::before{
      background:linear-gradient(180deg, rgba(255,255,255,0.55), transparent 30%);
    }
    html[data-theme="light"] .card{
      background:linear-gradient(160deg,#ffffff,#f7fafd);
      box-shadow:0 2px 10px rgba(15,23,42,0.06);
    }
    html[data-theme="light"] input[type="time"],
    html[data-theme="light"] input[type="number"],
    html[data-theme="light"] input[type="text"],
    html[data-theme="light"] input[type="password"],
    html[data-theme="light"] select{
      background:#ffffff;
      border-color:rgba(15,23,42,0.14);
      color:var(--text);
      box-shadow:inset 0 1px 2px rgba(15,23,42,0.04);
    }
    html[data-theme="light"] .btn-secondary{
      background:linear-gradient(180deg,#ffffff,#f1f5fa);
      border-color:rgba(15,23,42,0.12);
      box-shadow:0 2px 8px rgba(15,23,42,0.08);
      color:var(--text);
    }
    html[data-theme="light"] .btn-secondary:hover{
      background:linear-gradient(180deg,#ffffff,#e8eff8);
      border-color:rgba(15,23,42,0.18);
      box-shadow:0 6px 18px rgba(15,23,42,0.10);
    }
    html[data-theme="light"] .btn-secondary:active{
      box-shadow:inset 0 0 0 1px rgba(15,23,42,0.04), 0 1px 4px rgba(15,23,42,0.10);
    }
    html[data-theme="light"] .slider{background:#c7d2e0;border-color:rgba(15,23,42,0.08)}
    html[data-theme="light"] .slider:before{box-shadow:0 2px 6px rgba(15,23,42,0.28)}
    html[data-theme="light"] .footer{color:#6b7686}
    html[data-theme="light"] .toast{
      background:linear-gradient(90deg, rgba(34,197,94,0.16), rgba(2,132,199,0.10));
      color:#083b25;
      border-color:rgba(22,163,74,0.30);
      box-shadow:0 18px 50px rgba(15,23,42,0.20);
    }
    html[data-theme="light"] .flash.warn{color:#92400e}
    html[data-theme="light"] .btn-info,
    html[data-theme="light"] .btn-theme{background:rgba(15,23,42,0.04)}
    html[data-theme="light"] .btn-info:hover{background:rgba(2,132,199,0.10);color:#0369a1}
    html[data-theme="light"] .btn-logout{background:rgba(15,23,42,0.04)}
    /* 图标/字标：原版「Mate」是白色，亮色底下要转深色；Logo 加一块深色底保持可读 */
    html[data-theme="light"] .wordmark .white{fill:#0f172a}
    html[data-theme="light"] .logo-wrap{background:#0b1120}
    /* 风险标签在浅底上提高对比度 */
    html[data-theme="light"] .tag-warn{background:rgba(251,191,36,0.18);color:#a16207;border-color:rgba(202,138,4,0.35)}
    html[data-theme="light"] .tag-danger{background:rgba(239,68,68,0.12);color:#b91c1c;border-color:rgba(220,38,38,0.30)}
    html[data-theme="light"] .tag-ok{background:rgba(34,197,94,0.14);color:#15803d;border-color:rgba(22,163,74,0.30)}
    /* 预览弹窗是内联样式，需要 !important 才能覆盖 */
    html[data-theme="light"] #prunePreviewModal > div{
      background:linear-gradient(180deg,#ffffff,#f6f9fd) !important;
      border-color:rgba(15,23,42,0.12) !important;
      box-shadow:0 24px 60px rgba(15,23,42,0.22) !important;
    }

    /* 顶部按钮组改成一排，容纳主题切换 */
    .header-buttons{position:absolute;top:24px;right:24px;display:flex;align-items:center;gap:8px;z-index:10}
    .header-buttons .btn-info,
    .header-buttons .btn-logout{position:static;top:auto;right:auto}
    .header-buttons.has-logout .btn-info{right:auto}
    .btn-theme{
      display:flex;align-items:center;justify-content:center;
      width:36px;height:36px;padding:0;border-radius:9999px;cursor:pointer;
      color:var(--muted);background:rgba(255,255,255,0.03);
      border:1px solid var(--glass-border);backdrop-filter:blur(4px);
      transition:all .2s ease;
    }
    .btn-theme:hover{background:rgba(14,165,233,0.10);color:#7dd3fc;border-color:rgba(14,165,233,0.2);transform:translateY(-1px)}
    .btn-theme svg{width:18px;height:18px;stroke-width:2}
    @media (max-width:640px){
      .header-buttons.has-logout .btn-info{right:auto}
    }
    /* ================== 亮色主题结束 ================== */
"""

HEAD_SCRIPT = """  <script>
    /* 首屏前置：读取主题偏好，避免亮色用户看到深色闪一下 */
    (function(){
      var t = null;
      try { t = localStorage.getItem('prunemate-theme'); } catch(e) {}
      if (t !== 'light' && t !== 'dark') {
        t = (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? 'light' : 'dark';
      }
      document.documentElement.setAttribute('data-theme', t);
    })();
  </script>
"""

THEME_BTN = """      <button type="button" id="theme-toggle" class="btn-theme" title="切换主题" aria-label="切换主题"></button>
"""

THEME_JS = """
    // 主题切换：localStorage 记忆，默认跟随系统
    (function initThemeToggle(){
      var btn = document.getElementById('theme-toggle');
      if (!btn) return;
      var sun = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2 12h2M20 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>';
      var moon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
      function render(){
        var light = document.documentElement.getAttribute('data-theme') === 'light';
        btn.innerHTML = light ? moon : sun;
        btn.title = light ? '切换到深色主题' : '切换到亮色主题';
      }
      render();
      btn.addEventListener('click', function(){
        var next = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', next);
        try { localStorage.setItem('prunemate-theme', next); } catch(e) {}
        render();
      });
    })();
"""

def patch_index(path):
    s = io.open(path, encoding="utf-8").read()
    if 'data-theme="light"' in s:
        print("index: 已处理，跳过"); return 0
    miss = []
    anchor_css = "    /* Global box-sizing reset */"
    if s.count(anchor_css) != 1: miss.append("css anchor")
    else: s = s.replace(anchor_css, LIGHT_CSS + "\n" + anchor_css, 1)

    if s.count("</head>") != 1: miss.append("head anchor")
    else: s = s.replace("</head>", HEAD_SCRIPT + "</head>", 1)

    anchor_btn = '      <a href="https://prunemate.org" class="btn-info"'
    if s.count(anchor_btn) != 1: miss.append("btn anchor")
    else: s = s.replace(anchor_btn, THEME_BTN + anchor_btn, 1)

    anchor_js = "  </script>\n</body>"
    if s.count(anchor_js) != 1: miss.append("js anchor")
    else: s = s.replace(anchor_js, THEME_JS + "  </script>\n</body>", 1)

    if miss:
        print("index: 锚点异常", miss); return 1
    io.open(path, "w", encoding="utf-8").write(s)
    print("index: OK", len(s), "字节")
    return 0

LOGIN_CSS = """    /* ==================== 亮色主题 ==================== */
    html[data-theme="light"]{
      --bg-900:#f7f9fc;
      --bg-800:#eef3f9;
      --accent:#0284c7;
      --accent-strong:#16a34a;
      --muted:#5b6879;
      --text:#0f172a;
      --card-border:rgba(15,23,42,0.08);
      --glass-border:rgba(15,23,42,0.10);
      --focus:0 6px 24px rgba(2,132,199,0.16);
      --shadow-strong:0 24px 60px rgba(15,23,42,0.14);
      --radius-lg:18px;
    }
    html[data-theme="light"] body{
      background:
        radial-gradient(600px 300px at 50% 10%, rgba(2,132,199,0.10), transparent 40%),
        linear-gradient(135deg, var(--bg-900), var(--bg-800));
    }
    html[data-theme="light"] .login-container{
      background:linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,253,0.98));
      box-shadow:var(--shadow-strong), 0 10px 35px rgba(15,23,42,0.10);
    }
    html[data-theme="light"] .login-container::before{
      background:linear-gradient(180deg, rgba(255,255,255,0.6), transparent 40%);
    }
    html[data-theme="light"] input[type="text"],
    html[data-theme="light"] input[type="password"]{
      background:#ffffff;
      border-color:rgba(15,23,42,0.14);
      color:var(--text);
    }
    html[data-theme="light"] .logo-wrap{background:#0b1120}
    html[data-theme="light"] .footer{color:#6b7686}
    /* ================== 亮色主题结束 ================== */
"""

def patch_login(path):
    s = io.open(path, encoding="utf-8").read()
    if 'data-theme="light"' in s:
        print("login: 已处理，跳过"); return 0
    anchor = "    *{box-sizing:border-box}"
    if s.count(anchor) != 1:
        print("login: 锚点异常"); return 1
    s = s.replace(anchor, LOGIN_CSS + "\n" + anchor, 1)
    if s.count("</head>") != 1:
        print("login: head 锚点异常"); return 1
    s = s.replace("</head>", HEAD_SCRIPT + "</head>", 1)
    io.open(path, "w", encoding="utf-8").write(s)
    print("login: OK", len(s), "字节")
    return 0

rc = patch_index(os.path.join(SRC, "index.html")) + patch_login(os.path.join(SRC, "login.html"))
sys.exit(rc)
