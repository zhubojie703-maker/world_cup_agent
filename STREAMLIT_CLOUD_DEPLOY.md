# Streamlit Cloud 部署检查清单

## 1. 公开访问设置

当前 `https://world-cup-agent.streamlit.app/` 会跳转到 Streamlit 登录页，说明应用还不是公开可访问状态。

在 Streamlit Cloud 控制台操作：

1. 打开 `https://share.streamlit.io/`
2. 进入 `world-cup-agent` 这个 app
3. 点击右上角 `Share`
4. 点击 `Make this app public`
5. 再用无痕窗口访问 `https://world-cup-agent.streamlit.app/`

成功标准：无痕窗口不登录 Streamlit，也能直接看到 Agent 页面。

## 2. 入口文件

如果 GitHub 仓库根目录就是 `sql_agent_demo`，Main file path 应该填写：

```text
world_cup_agent/app.py
```

如果 GitHub 仓库根目录就是 `world_cup_agent`，Main file path 应该填写：

```text
app.py
```

## 3. 依赖文件

当前依赖文件在：

```text
world_cup_agent/requirements.txt
```

里面必须至少包含：

```text
streamlit
pandas
sqlalchemy
pymysql
cryptography
Pillow
```

## 4. Secrets 配置

不要把数据库密码写进代码或 GitHub。进入 app 的 `Settings` / `Secrets`，粘贴 root-level secrets：

```toml
DATABASE_URL = "mysql+pymysql://用户名:密码@数据库公网地址:3306/world_cup_agent?charset=utf8mb4"
WORLD_CUP_AGENT_ADMIN_PASSCODE = "换成你自己的后台口令"
```

注意：不能用 `127.0.0.1` 或 `localhost`。Streamlit Cloud 运行在云端，访问不到你电脑本机的 MySQL。

## 5. 数据库选择

小范围演示可以先不配置 `DATABASE_URL`，应用会回退到 SQLite；但 Streamlit Cloud 的文件存储不适合长期保存用户数据。

如果要发小红书收真实数据，建议使用云数据库：

- Railway MySQL
- Aiven MySQL
- 阿里云 RDS MySQL
- 腾讯云 MySQL

成功标准：后台 `?admin=1` 的数据库状态显示 `MySQL`，不是 `SQLite`。

## 6. 发布前验证

公开前按顺序检查：

1. 无痕窗口打开首页，不需要登录
2. 手机流量打开首页，不需要连接你的 Wi-Fi
3. 完成一次测试
4. 进入 `?admin=1`
5. 后台数据库状态显示正确
6. MySQL 里 `sessions`、`answers`、`agent_outputs` 行数增加

## 7. 小红书发布提醒

不要在笔记里写微信号、二维码、诱导加群等内容。建议使用“评论区/主页链接/搜索关键词”的低风险方式引导用户体验。
