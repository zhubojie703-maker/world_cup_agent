# 世界杯观赛偏好 Agent MVP

这个 MVP 用世界杯热点做真实用户获取和行为分析实验。前台收集用户观赛偏好，生成主队推荐和可复制文案；后台沉淀访问、完成、复制、反馈等事件，并提供聚合看板和受控 DataAgent 查询。

## 核心能力

- 5 题观赛偏好测试：懂球程度、观赛动机、球队风格、内容需求、观赛场景。
- 可解释主队推荐：用户标签与球队标签加权匹配，再生成推荐理由。
- 行为埋点：`page_view`、`start_test`、`finish_test`、`view_result`、`copy_result`、`feedback_submit`。
- 后台指标：访问、开始、完成、完成率、复制率、平均评分、球队热度、渠道来源、城市分布。
- 受控 DataAgent：支持完成率、球队热度、渠道来源等聚合查询。
- 隐私边界：匿名采集、聚合分析、不展示单个用户隐私。

## 运行方式

```bash
cd world_cup_agent
pip install -r requirements.txt
streamlit run app.py
```

默认不配置数据库环境变量时，系统会写入本地 SQLite：

```text
world_cup_agent/data/world_cup_agent.db
```

如果要部署给朋友使用，配置 `DATABASE_URL` 后会自动切换到 MySQL：

```bash
set DATABASE_URL=mysql+pymysql://wc_user:your_password@your-host:3306/world_cup_agent?charset=utf8mb4
streamlit run app.py
```

线上部署时把 `DATABASE_URL` 和 `WORLD_CUP_AGENT_ADMIN_PASSCODE` 放到部署平台的 Secrets/Environment Variables 里，不要写进代码。

默认用户只会看到 `Agent` 和 `Privacy`。管理员需要在 URL 后添加 `?admin=1`，再输入后台口令，才会看到 `Dashboard` 和 `DataAgent`。

本地默认后台口令：

```text
worldcup2026
```

本地管理员入口：

```text
http://127.0.0.1:8501/?admin=1
```

部署到公开环境时建议改成环境变量：

```bash
set WORLD_CUP_AGENT_ADMIN_PASSCODE=your_strong_passcode
streamlit run app.py
```

## 测试

在仓库根目录运行：

```bash
python -m pytest tests/world_cup_agent -q
```

## 作品集表达

可以包装为：

> 基于世界杯热点的用户偏好 Agent 与行为分析系统。通过社交平台引流真实用户，前台完成观赛偏好采集和个性化推荐，后台用事件埋点和 DataAgent 查询分析用户漏斗、内容需求和渠道表现，形成从用户获取到产品迭代的数据闭环。
