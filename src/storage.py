from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
    text,
)
from sqlalchemy.engine import Connection, Engine


metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("user_id", String(64), primary_key=True),
    Column("city", String(64)),
    Column("age_range", String(32)),
    Column("gender", String(32)),
    Column("created_at", String(32), nullable=False),
)

sessions = Table(
    "sessions",
    metadata,
    Column("session_id", String(64), primary_key=True),
    Column("user_id", String(64), ForeignKey("users.user_id"), nullable=False),
    Column("source", String(64), nullable=False),
    Column("started_at", String(32), nullable=False),
    Column("ended_at", String(32)),
)

answers = Table(
    "answers",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", String(64), ForeignKey("sessions.session_id"), nullable=False),
    Column("question_id", String(64), nullable=False),
    Column("answer_text", Text, nullable=False),
    Column("answer_tag", String(64)),
    Column("created_at", String(32), nullable=False),
)

events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", String(64), ForeignKey("sessions.session_id"), nullable=False),
    Column("event_name", String(64), nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("created_at", String(32), nullable=False),
)

agent_outputs = Table(
    "agent_outputs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", String(64), ForeignKey("sessions.session_id"), nullable=False),
    Column("recommended_team", String(64), nullable=False),
    Column("persona", String(128), nullable=False),
    Column("copy_text", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("created_at", String(32), nullable=False),
)

feedback = Table(
    "feedback",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("session_id", String(64), ForeignKey("sessions.session_id"), nullable=False),
    Column("rating", Integer, nullable=False),
    Column("comment_tag", String(64)),
    Column("created_at", String(32), nullable=False),
)


def get_database_url(db_path: str | Path) -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url

    path = Path(db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"


def get_database_status(db_path: str | Path) -> dict[str, Any]:
    init_db(db_path)
    database_url = get_database_url(db_path)
    backend = "MySQL" if database_url.startswith("mysql") else "SQLite"
    with _engine_for(db_path).connect() as conn:
        table_counts = {
            table_name: _scalar(conn, f"SELECT COUNT(*) FROM {table_name}")
            for table_name in _table_names()
        }
    return {
        "backend": backend,
        "safe_url": _mask_database_url(database_url),
        "table_counts": table_counts,
    }


@lru_cache(maxsize=8)
def get_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
    return create_engine(database_url, pool_pre_ping=True, pool_recycle=1800)


def init_db(db_path: str | Path) -> None:
    engine = _engine_for(db_path)
    metadata.create_all(engine)


def create_session(
    db_path: str | Path,
    *,
    user_id: str | None = None,
    source: str,
    city: str,
    age_range: str,
    gender: str,
) -> str:
    init_db(db_path)
    session_id = f"session_{uuid4().hex[:12]}"
    resolved_user_id = user_id or f"user_{uuid4().hex[:12]}"
    now = _now()

    with _engine_for(db_path).begin() as conn:
        existing_user = conn.execute(
            select(users.c.user_id).where(users.c.user_id == resolved_user_id)
        ).first()
        if existing_user is None:
            conn.execute(
                users.insert().values(
                    user_id=resolved_user_id,
                    city=city,
                    age_range=age_range,
                    gender=gender,
                    created_at=now,
                )
            )

        conn.execute(
            sessions.insert().values(
                session_id=session_id,
                user_id=resolved_user_id,
                source=source,
                started_at=now,
            )
        )
    return session_id


def record_answer(
    db_path: str | Path,
    session_id: str,
    question_id: str,
    answer_text: str,
    answer_tag: str | None = None,
) -> None:
    init_db(db_path)
    with _engine_for(db_path).begin() as conn:
        conn.execute(
            answers.insert().values(
                session_id=session_id,
                question_id=question_id,
                answer_text=answer_text,
                answer_tag=answer_tag,
                created_at=_now(),
            )
        )


def record_event(db_path: str | Path, session_id: str, event_name: str, payload: dict[str, Any]) -> None:
    init_db(db_path)
    now = _now()
    with _engine_for(db_path).begin() as conn:
        conn.execute(
            events.insert().values(
                session_id=session_id,
                event_name=event_name,
                payload_json=json.dumps(payload, ensure_ascii=False),
                created_at=now,
            )
        )
        if event_name == "finish_test":
            conn.execute(
                sessions.update()
                .where(sessions.c.session_id == session_id)
                .values(ended_at=now)
            )


def save_output(
    db_path: str | Path,
    session_id: str,
    *,
    recommended_team: str,
    persona: str,
    copy_text: str,
    reason: str,
) -> None:
    init_db(db_path)
    with _engine_for(db_path).begin() as conn:
        conn.execute(
            agent_outputs.insert().values(
                session_id=session_id,
                recommended_team=recommended_team,
                persona=persona,
                copy_text=copy_text,
                reason=reason,
                created_at=_now(),
            )
        )


def save_feedback(db_path: str | Path, session_id: str, *, rating: int, comment_tag: str) -> None:
    init_db(db_path)
    with _engine_for(db_path).begin() as conn:
        conn.execute(
            feedback.insert().values(
                session_id=session_id,
                rating=rating,
                comment_tag=comment_tag,
                created_at=_now(),
            )
        )


def get_dashboard_metrics(db_path: str | Path) -> dict[str, Any]:
    init_db(db_path)
    with _engine_for(db_path).connect() as conn:
        visits = _scalar(conn, "SELECT COUNT(DISTINCT session_id) FROM events WHERE event_name = 'page_view'")
        sessions_started = _scalar(
            conn, "SELECT COUNT(DISTINCT session_id) FROM events WHERE event_name = 'start_test'"
        )
        sessions_finished = _scalar(
            conn, "SELECT COUNT(DISTINCT session_id) FROM events WHERE event_name = 'finish_test'"
        )
        copy_count = _scalar(conn, "SELECT COUNT(DISTINCT session_id) FROM events WHERE event_name = 'copy_result'")
        feedback_count = _scalar(conn, "SELECT COUNT(*) FROM feedback")
        avg_rating = _scalar(conn, "SELECT AVG(rating) FROM feedback") or 0
        top_teams = _rows(
            conn,
            """
            SELECT recommended_team AS team, COUNT(*) AS count
            FROM agent_outputs
            GROUP BY recommended_team
            ORDER BY count DESC, team ASC
            LIMIT 5
            """,
        )
        top_sources = _rows(
            conn,
            """
            SELECT source, COUNT(*) AS count
            FROM sessions
            GROUP BY source
            ORDER BY count DESC, source ASC
            LIMIT 5
            """,
        )
        city_distribution = _rows(
            conn,
            """
            SELECT city, COUNT(*) AS count
            FROM users
            WHERE city != ''
            GROUP BY city
            ORDER BY count DESC, city ASC
            LIMIT 8
            """,
        )

    return {
        "visits": visits,
        "sessions_started": sessions_started,
        "sessions_finished": sessions_finished,
        "completion_rate": _rate(sessions_finished, sessions_started),
        "copy_rate": _rate(copy_count, sessions_finished),
        "feedback_count": feedback_count,
        "avg_rating": round(float(avg_rating), 2),
        "top_teams": top_teams,
        "top_sources": top_sources,
        "city_distribution": city_distribution,
    }


def get_recent_sessions(db_path: str | Path, limit: int = 50) -> list[dict[str, Any]]:
    init_db(db_path)
    stmt = (
        select(
            sessions.c.session_id,
            sessions.c.source,
            sessions.c.started_at,
            users.c.city,
            users.c.age_range,
            users.c.gender,
            agent_outputs.c.recommended_team,
            agent_outputs.c.persona,
            feedback.c.rating,
        )
        .select_from(
            sessions.join(users, users.c.user_id == sessions.c.user_id)
            .outerjoin(agent_outputs, agent_outputs.c.session_id == sessions.c.session_id)
            .outerjoin(feedback, feedback.c.session_id == sessions.c.session_id)
        )
        .order_by(sessions.c.started_at.desc())
        .limit(limit)
    )
    with _engine_for(db_path).connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(row) for row in rows]


def answer_data_question(db_path: str | Path, question: str) -> dict[str, Any]:
    normalized = question.strip()
    metrics = get_dashboard_metrics(db_path)
    if any(keyword in normalized for keyword in ["完成率", "漏斗", "转化"]):
        return {
            "title": "测试漏斗表现",
            "answer": (
                f"当前访问 {metrics['visits']} 次，开始测试 {metrics['sessions_started']} 次，"
                f"完成测试 {metrics['sessions_finished']} 次，完成率 {metrics['completion_rate']:.0%}。"
            ),
        }
    if any(keyword in normalized for keyword in ["球队", "主队", "热度"]):
        top = metrics["top_teams"][:3]
        text = "，".join(f"{row['team']} {row['count']} 次" for row in top) or "暂无推荐数据"
        return {"title": "球队推荐热度", "answer": f"当前推荐最高的球队是：{text}。"}
    if any(keyword in normalized for keyword in ["渠道", "来源", "小红书"]):
        top = metrics["top_sources"][:3]
        text = "，".join(f"{row['source']} {row['count']} 次" for row in top) or "暂无渠道数据"
        return {"title": "渠道来源表现", "answer": f"当前主要来源是：{text}。"}
    return {
        "title": "可查询问题示例",
        "answer": "你可以问：当前完成率是多少、哪个球队最热、哪个渠道带来的用户最多。",
    }


def _engine_for(db_path: str | Path) -> Engine:
    return get_engine(get_database_url(db_path))


def _table_names() -> Iterable[str]:
    return [
        "users",
        "sessions",
        "answers",
        "events",
        "agent_outputs",
        "feedback",
    ]


def _mask_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite"):
        return database_url
    parts = urlsplit(database_url)
    if not parts.password:
        return database_url
    username = parts.username or ""
    host = parts.hostname or ""
    port = f":{parts.port}" if parts.port else ""
    masked_netloc = f"{username}:***@{host}{port}"
    return urlunsplit((parts.scheme, masked_netloc, parts.path, parts.query, parts.fragment))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _scalar(conn: Connection, sql: str, params: dict[str, Any] | None = None) -> Any:
    return conn.execute(text(sql), params or {}).scalar()


def _rows(conn: Connection, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(text(sql), params or {}).mappings().all()]


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)
