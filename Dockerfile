# 汉化 + 加固后的 PruneMate 镜像
# 基座是上游官方镜像，只覆盖界面/后端文件，不改依赖
FROM anoniemerd/prunemate:1.4.0

COPY src/index.html   /app/templates/index.html
COPY src/login.html   /app/templates/login.html
COPY src/prunemate.py /app/prunemate.py
