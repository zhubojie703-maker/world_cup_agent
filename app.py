from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st

from src.access_control import is_admin_authenticated, should_show_admin_gate, visible_tabs
from src.recommender import build_user_tags, recommend_team
from src.storage import (
    answer_data_question,
    create_session,
    get_dashboard_metrics,
    get_database_status,
    get_recent_sessions,
    init_db,
    record_answer,
    record_event,
    save_feedback,
    save_output,
)


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "world_cup_agent.db"
ADMIN_PASSCODE = os.getenv("WORLD_CUP_AGENT_ADMIN_PASSCODE", "worldcup2026")

QUESTION_TAGS = {
    "football_level": {
        "完全不懂": "beginner",
        "新手": "beginner",
        "偶尔看": "casual",
        "老球迷": "expert",
    },
    "watch_motivation": {
        "和朋友社交": "social",
        "想有参与感": "participation",
        "想找情绪价值": "emotion",
        "喜欢故事感": "story",
    },
    "team_style": {
        "冠军热门": "champion_potential",
        "黑马故事": "underdog_story",
        "球星魅力": "star_power",
        "高颜值/穿搭": "social_style",
        "战术入门": "tactical_intro",
    },
    "content_need": {
        "朋友圈文案": "social_copy",
        "分享海报": "poster",
        "观赛入门": "beginner_guide",
        "赛前科普": "match_preview",
    },
    "viewing_scene": {
        "朋友聚会": "party",
        "酒吧看球": "bar",
        "情侣约会": "date",
        "自己在家": "home",
        "宿舍看球": "dorm",
    },
}


def main() -> None:
    st.set_page_config(page_title="World Cup Agent MVP", page_icon="WC", layout="wide")
    init_db(DB_PATH)
    _inject_css()
    _ensure_state()

    st.title("世界杯观赛偏好 Agent")
    st.caption("MVP: 主队匹配、社交文案、真实用户行为埋点、数据分析后台")

    is_admin = render_admin_gate()
    tab_names = visible_tabs(is_admin)
    tabs = st.tabs(tab_names)
    for tab_name, tab in zip(tab_names, tabs):
        with tab:
            if tab_name == "Agent":
                render_agent()
            elif tab_name == "Dashboard":
                render_dashboard()
            elif tab_name == "DataAgent":
                render_data_agent()
            elif tab_name == "Privacy":
                render_privacy()


def render_admin_gate() -> bool:
    if not should_show_admin_gate(dict(st.query_params)):
        return False

    with st.sidebar:
        st.caption("管理员入口")
        passcode = st.text_input("后台口令", type="password", placeholder="输入后显示分析后台")
        is_admin = is_admin_authenticated(passcode, ADMIN_PASSCODE)
        if is_admin:
            st.success("后台已解锁")
        else:
            st.caption("普通用户不会看到 Dashboard 和 DataAgent。")
        return is_admin


def render_agent() -> None:
    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        st.subheader("观赛偏好测试")
        with st.form("quiz_form", clear_on_submit=False):
            source = st.selectbox(
                "来源渠道",
                ["xiaohongshu_a", "xiaohongshu_b", "wechat", "bilibili", "direct"],
            )
            city = st.text_input("城市", value="上海", max_chars=20)
            age_range = st.selectbox("年龄段", ["18以下", "18-24", "25-30", "31-40", "40以上"])
            gender = st.selectbox("性别", ["不透露", "女", "男"])
            football_level = st.radio(
                "你现在的懂球程度",
                ["完全不懂", "新手", "偶尔看", "老球迷"],
                horizontal=True,
            )
            watch_motivation = st.radio(
                "你最想从世界杯里获得什么",
                ["和朋友社交", "想有参与感", "想找情绪价值", "喜欢故事感"],
            )
            team_style = st.radio(
                "你更容易被哪类球队吸引",
                ["冠军热门", "黑马故事", "球星魅力", "高颜值/穿搭", "战术入门"],
            )
            content_need = st.radio(
                "你最想让 Agent 生成什么",
                ["朋友圈文案", "分享海报", "观赛入门", "赛前科普"],
                horizontal=True,
            )
            viewing_scene = st.radio(
                "你的主要观赛场景",
                ["朋友聚会", "酒吧看球", "情侣约会", "自己在家", "宿舍看球"],
            )
            submitted = st.form_submit_button("生成我的世界杯主队")

        if submitted:
            answers = {
                "football_level": football_level,
                "watch_motivation": watch_motivation,
                "team_style": team_style,
                "content_need": content_need,
                "viewing_scene": viewing_scene,
            }
            session_id = create_session(
                DB_PATH,
                user_id=st.session_state.user_id,
                source=source,
                city=city.strip(),
                age_range=age_range,
                gender=gender,
            )
            st.session_state.session_id = session_id
            st.session_state.copied = False
            record_event(DB_PATH, session_id, "page_view", {"source": source})
            record_event(DB_PATH, session_id, "start_test", {})
            for question_id, answer_text in answers.items():
                record_answer(
                    DB_PATH,
                    session_id,
                    question_id,
                    answer_text,
                    QUESTION_TAGS.get(question_id, {}).get(answer_text, ""),
                )
            result = recommend_team(build_user_tags(answers))
            record_event(DB_PATH, session_id, "finish_test", {"answer_count": len(answers)})
            record_event(DB_PATH, session_id, "view_result", {"team": result["team_name"]})
            save_output(
                DB_PATH,
                session_id,
                recommended_team=result["team_name"],
                persona=result["persona"],
                copy_text=result["copy_text"],
                reason=result["reason"],
            )
            st.session_state.result = result

    with right:
        st.subheader("推荐结果")
        result = st.session_state.get("result")
        session_id = st.session_state.get("session_id")
        if not result:
            st.info("完成左侧测试后，这里会出现主队推荐和可复制文案。")
            st.markdown(
                """
                <div class="empty-panel">
                    <div class="panel-title">MVP 数据闭环</div>
                    <div>访问、开始测试、完成测试、复制结果和反馈都会进入后台指标。</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            f"""
            <div class="result-card">
                <div class="eyebrow">推荐主队</div>
                <div class="team-name">{result["team_name"]}</div>
                <div class="persona">{result["persona"]}</div>
                <p>{result["reason"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.text_area("可复制文案", result["copy_text"], height=180)
        if st.button("我已复制这段文案", disabled=st.session_state.copied):
            if session_id:
                record_event(DB_PATH, session_id, "copy_result", {"copy_type": "social_copy"})
            st.session_state.copied = True
            st.toast("复制行为已记录")

        with st.form("feedback_form"):
            rating = st.slider("结果满意度", 1, 5, 4)
            comment_tag = st.selectbox(
                "反馈标签",
                ["结果有用", "文案好用", "推荐不准", "想要赛程", "想要穿搭", "想要酒吧推荐"],
            )
            feedback_submitted = st.form_submit_button("提交反馈")
        if feedback_submitted and session_id:
            save_feedback(DB_PATH, session_id, rating=rating, comment_tag=comment_tag)
            record_event(DB_PATH, session_id, "feedback_submit", {"rating": rating, "tag": comment_tag})
            st.success("反馈已记录")


def render_dashboard() -> None:
    st.subheader("行为分析后台")
    render_database_status()
    metrics = get_dashboard_metrics(DB_PATH)
    kpi_cols = st.columns(6)
    kpis = [
        ("访问", metrics["visits"]),
        ("开始", metrics["sessions_started"]),
        ("完成", metrics["sessions_finished"]),
        ("完成率", f"{metrics['completion_rate']:.0%}"),
        ("复制率", f"{metrics['copy_rate']:.0%}"),
        ("平均评分", metrics["avg_rating"]),
    ]
    for col, (label, value) in zip(kpi_cols, kpis):
        col.metric(label, value)

    chart_cols = st.columns(3)
    _render_bar(chart_cols[0], "球队推荐热度", metrics["top_teams"], "team")
    _render_bar(chart_cols[1], "渠道来源", metrics["top_sources"], "source")
    _render_bar(chart_cols[2], "城市分布", metrics["city_distribution"], "city")

    st.subheader("最近会话")
    recent = get_recent_sessions(DB_PATH)
    if recent:
        st.dataframe(pd.DataFrame(recent), use_container_width=True, hide_index=True)
    else:
        st.info("还没有真实会话。先去 Agent 页完成一次测试。")


def render_database_status() -> None:
    status = get_database_status(DB_PATH)
    with st.expander("数据库连接状态", expanded=True):
        cols = st.columns([0.8, 2.2])
        cols[0].metric("当前后端", status["backend"])
        cols[1].code(status["safe_url"], language="text")
        table_df = pd.DataFrame(
            [{"table": table, "rows": count} for table, count in status["table_counts"].items()]
        )
        st.dataframe(table_df, use_container_width=True, hide_index=True)


def render_data_agent() -> None:
    st.subheader("受控 DataAgent 查询")
    question = st.text_input(
        "输入一个数据问题",
        value="当前完成率是多少？",
        placeholder="例如：哪个球队最热？哪个渠道带来的用户最多？",
    )
    if st.button("查询"):
        answer = answer_data_question(DB_PATH, question)
        st.markdown(f"**{answer['title']}**")
        st.write(answer["answer"])
        st.caption("当前 MVP 只开放聚合查询，不返回单个用户明细。")


def render_privacy() -> None:
    st.subheader("数据使用说明")
    st.write(
        """
        本 MVP 只采集匿名用户画像、问卷答案、推荐结果、复制行为和满意度反馈。
        不采集姓名、手机号、微信号等强身份信息。后台只做聚合分析，用于优化 Agent 问题、推荐逻辑和内容策略。
        """
    )
    st.write(
        """
        DataAgent 查询限定为只读聚合分析：例如完成率、渠道表现、球队热度。
        当样本量较小时，分析结论仅用于产品验证，不作为统计代表性结论。
        """
    )


def _render_bar(container, title: str, rows: list[dict], label_key: str) -> None:
    with container:
        st.markdown(f"**{title}**")
        if not rows:
            st.info("暂无数据")
            return
        df = pd.DataFrame(rows)
        df = df.rename(columns={label_key: "label"})
        st.bar_chart(df.set_index("label")["count"], height=220)


def _ensure_state() -> None:
    if "user_id" not in st.session_state:
        st.session_state.user_id = f"user_{uuid4().hex[:12]}"
    if "copied" not in st.session_state:
        st.session_state.copied = False


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f8faf7;
            color: #17201a;
        }
        .block-container {
            padding-top: 1.4rem;
            max-width: 1180px;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #dce5dc;
            border-radius: 8px;
            padding: 0.8rem;
        }
        .result-card, .empty-panel {
            background: #ffffff;
            border: 1px solid #dce5dc;
            border-radius: 8px;
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
        }
        .eyebrow {
            font-size: 0.78rem;
            color: #667368;
            margin-bottom: 0.25rem;
        }
        .team-name {
            font-size: 2.1rem;
            font-weight: 760;
            line-height: 1.1;
            color: #0f5132;
        }
        .persona, .panel-title {
            font-weight: 700;
            margin: 0.45rem 0;
            color: #214a35;
        }
        textarea {
            font-family: "Microsoft YaHei", Arial, sans-serif;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
