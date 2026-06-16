from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TeamProfile:
    team_name: str
    persona: str
    tags: dict[str, float]
    content_angle: str


TEAM_PROFILES = [
    TeamProfile(
        team_name="阿根廷",
        persona="情绪价值型冠军粉",
        tags={
            "champion_potential": 5,
            "star_power": 5,
            "social_scene": 4,
            "narrative": 5,
            "beginner_friendly": 4,
        },
        content_angle="有球星、有故事、有社交话题，适合想快速进入世界杯氛围的新手。",
    ),
    TeamProfile(
        team_name="法国",
        persona="实力控观赛者",
        tags={
            "champion_potential": 5,
            "star_power": 4,
            "tactical_intro": 4,
            "social_style": 4,
            "beginner_friendly": 3,
        },
        content_angle="阵容强、节奏快、话题密度高，适合喜欢强队和稳定胜负预期的人。",
    ),
    TeamProfile(
        team_name="巴西",
        persona="氛围感观赛者",
        tags={
            "champion_potential": 4,
            "social_style": 5,
            "star_power": 4,
            "social_scene": 5,
            "beginner_friendly": 4,
        },
        content_angle="观赛氛围浓，适合聚会、穿搭、拍照和轻松参与世界杯话题。",
    ),
    TeamProfile(
        team_name="摩洛哥",
        persona="黑马故事收集者",
        tags={
            "underdog_story": 5,
            "narrative": 5,
            "tactical_intro": 3,
            "beginner_friendly": 3,
            "quiet_scene": 3,
        },
        content_angle="黑马叙事强，适合喜欢反差、逆袭和情绪起伏的人。",
    ),
    TeamProfile(
        team_name="日本",
        persona="秩序感成长型观赛者",
        tags={
            "underdog_story": 4,
            "narrative": 4,
            "tactical_intro": 5,
            "beginner_friendly": 4,
            "quiet_scene": 4,
        },
        content_angle="适合想看团队配合、战术执行和成长叙事的新手用户。",
    ),
    TeamProfile(
        team_name="克罗地亚",
        persona="老派故事型观赛者",
        tags={
            "underdog_story": 4,
            "narrative": 5,
            "tactical_intro": 4,
            "quiet_scene": 4,
            "beginner_friendly": 3,
        },
        content_angle="故事感和韧性很强，适合喜欢长线陪伴感的人。",
    ),
]


def build_user_tags(answers: dict[str, str]) -> dict[str, float]:
    tags: dict[str, float] = {}

    def add(tag: str, weight: float) -> None:
        tags[tag] = tags.get(tag, 0.0) + weight

    football_level = answers.get("football_level", "")
    if football_level in {"完全不懂", "新手"}:
        add("beginner_friendly", 3)
    elif football_level == "老球迷":
        add("tactical_intro", 3)

    motivation = answers.get("watch_motivation", "")
    if motivation in {"和朋友社交", "想有参与感"}:
        add("social_scene", 3)
    if motivation in {"想找情绪价值", "喜欢故事感"}:
        add("narrative", 3)

    team_style = answers.get("team_style", "")
    style_map = {
        "冠军热门": ["champion_potential", "star_power"],
        "黑马故事": ["underdog_story", "narrative"],
        "球星魅力": ["star_power", "social_scene"],
        "高颜值/穿搭": ["social_style", "social_scene"],
        "战术入门": ["tactical_intro", "beginner_friendly"],
    }
    for tag in style_map.get(team_style, []):
        add(tag, 4)

    content_need = answers.get("content_need", "")
    if content_need in {"朋友圈文案", "分享海报"}:
        add("social_scene", 2)
        add("social_style", 2)
    if content_need in {"观赛入门", "赛前科普"}:
        add("beginner_friendly", 2)
        add("tactical_intro", 2)

    viewing_scene = answers.get("viewing_scene", "")
    if viewing_scene in {"朋友聚会", "酒吧看球", "情侣约会"}:
        add("social_scene", 2)
    if viewing_scene in {"自己在家", "宿舍看球"}:
        add("quiet_scene", 2)

    return tags


def recommend_team(user_tags: dict[str, float]) -> dict[str, Any]:
    ranked = []
    for team in TEAM_PROFILES:
        score = sum(user_tags.get(tag, 0.0) * weight for tag, weight in team.tags.items())
        ranked.append((score, team))

    score, team = max(ranked, key=lambda item: item[0])
    matched_tags = [
        tag for tag in sorted(user_tags, key=user_tags.get, reverse=True) if team.tags.get(tag, 0) > 0
    ][:3]
    tag_text = "、".join(_tag_label(tag) for tag in matched_tags) or "世界杯氛围"
    reason = f"推荐理由：你的偏好集中在{tag_text}，{team.content_angle}"

    return {
        "team_name": team.team_name,
        "score": round(score, 2),
        "persona": team.persona,
        "reason": reason,
        "copy_text": build_social_copy(team.team_name, team.persona, reason),
        "matched_tags": matched_tags,
    }


def build_social_copy(team_name: str, persona: str, reason: str) -> str:
    return (
        f"今晚我的世界杯主队是{team_name}。\n"
        f"观赛人格：{persona}。\n"
        f"{reason}\n"
        "不一定懂球，但我已经有自己的看球立场了。"
    )


def _tag_label(tag: str) -> str:
    labels = {
        "champion_potential": "冠军热门",
        "star_power": "球星魅力",
        "social_scene": "社交氛围",
        "narrative": "故事感",
        "beginner_friendly": "新手友好",
        "underdog_story": "黑马叙事",
        "social_style": "氛围穿搭",
        "tactical_intro": "战术入门",
        "quiet_scene": "沉浸观赛",
    }
    return labels.get(tag, tag)
