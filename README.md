# 163 邮件转发总结服务

基于 FastAPI + Celery 风格的轮询（当前为轻量 worker 脚本）实现：用户录入 163 邮箱授权码与接收邮箱，系统 IMAP 轮询、调用 DeepSeek 总结并 SMTP 发送。

快速开始（开发，单机 sqlite）
```bash
python -m venv .venv
source .venv/bin/activate  # Windows 用 .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # 填写 DEEPSEEK_API_KEY、FERNET_KEY 等
uvicorn app.main:app --reload
python worker.py  # 另启一个终端运行后台轮询
```

## Docker Compose（建议生产，一键起 web+worker+db+nginx）
```bash
cp .env.example .env  # 修改数据库/密钥
# 推荐将 DATABASE_URL 改为: postgresql+psycopg2://app:app@db:5432/app
docker compose up -d --build
```

- web: FastAPI
- worker: 轮询 163 邮箱并发送总结
- db: Postgres 15
- redis: 预留做队列/限流（当前 worker 未使用队列，可后续接入 Celery）
- nginx: 反代/静态/可扩展 TLS

## 环境变量关键项
- `DEEPSEEK_API_KEY`: 服务端持有，前端不暴露
- `FERNET_KEY`: 用于加密存储 163 授权码
- `DATABASE_URL`: 默认 sqlite，可切换 postgres
- `POLL_INTERVAL_SECONDS`: 轮询间隔（秒）

## 核心功能
- 用户注册/登录（密码哈希，JWT 会话）
- 绑定 163 账号：邮箱、授权码、接收邮箱
- 取消服务：删除账号记录并停轮询
- 邮件处理：遵循原版逻辑，UNSEEN 拉取→DeepSeek 总结→SMTP 发目标邮箱

## Web 前端（无需懂数据库）
- 打开浏览器访问 `http://服务器IP:8000`（或经 nginx 80/443）。
- 注册账号 → 登录 → 在控制台填写 163 邮箱、授权码、接收邮箱；可留空 IMAP/SMTP 主机/端口使用默认 163 配置。
- 删除账号即停止服务（后台不再轮询）。

## 待完善
- Gmail 等多提供商
- Celery/Redis 队列化与重试/DLQ
- 前端样式与文件存储/日志出口
- TLS/证书自动化（Let’s Encrypt）
