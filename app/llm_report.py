import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import BadRequestError, OpenAI


DATA_DIR = Path("data")
REPORT_DIR = DATA_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

load_dotenv()
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")


def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("未检测到 OPENAI_API_KEY，请先在 .env 文件中填写 API Key。")
    return OpenAI(api_key=api_key)


def get_latest_analysis_path():
    analysis_path = DATA_DIR / "video_analysis.csv"
    candidates = [analysis_path] if analysis_path.exists() else []
    candidates.extend(DATA_DIR.glob("video_analysis_*.csv"))

    if not candidates:
        raise FileNotFoundError("未找到分析数据，请先运行：python -m app.analyze")

    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_data():
    video_path = DATA_DIR / "hot_game_videos.csv"
    comment_path = DATA_DIR / "hot_game_comments.csv"
    analysis_path = get_latest_analysis_path()

    if not video_path.exists():
        raise FileNotFoundError("未找到视频数据，请先运行：python -m app.collect")
    if not comment_path.exists():
        raise FileNotFoundError("未找到评论数据，请先运行：python -m app.collect")

    return (
        pd.read_csv(video_path),
        pd.read_csv(comment_path),
        pd.read_csv(analysis_path),
    )


def build_prompt(video_data, analysis_data, comment_table):
    if comment_table.empty:
        comment_text = "没有采集到评论样本，请基于互动指标做低置信度判断。"
    else:
        top_comments = comment_table.sort_values(by="评论点赞数", ascending=False).head(20)
        comment_text = "\n".join(
            f"- {content}"
            for content in top_comments["评论内容"].dropna().tolist()
        )

    return f"""
你是一个游戏内容增长分析 Agent，擅长分析 B站游戏区爆款视频。

你的任务不是复制原视频，而是分析它的爆火机制，并生成原创企划。
你必须区分：
1. 可以复用的机制：选题逻辑、情绪钩子、内容结构、发布时间策略、评论触发点。
2. 不可以复用的内容：原视频标题、封面构图、脚本文案、素材、UP主个人表达方式。

请输出一份中文报告，结构必须包含：

一、爆火结论
二、数据证据
三、UP主状态判断
四、观众吸引点
五、可复用的爆款机制
六、匹配的企划类型
七、原创企划方案：原创选题、5个标题候选、3组封面文案、前15秒脚本、视频结构大纲、评论区引导问题、推荐发布时间
八、相似度和风险提醒
九、适合投递游戏行业实习简历的项目描述

视频基础数据：
{json.dumps(video_data, ensure_ascii=False, indent=2)}

基础分析结果：
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

热门评论样本：
{comment_text}
"""


def generate_report(bvid):
    video_table, comment_table, analysis_table = load_data()

    matched_video = video_table[video_table["BV号"] == bvid]
    matched_analysis = analysis_table[analysis_table["BV号"] == bvid]
    matched_comments = comment_table[comment_table["BV号"] == bvid]

    if matched_video.empty:
        raise ValueError(f"未找到 BV号：{bvid}，请确认它在 data/hot_game_videos.csv 中。")
    if matched_analysis.empty:
        raise ValueError(f"未找到 BV号：{bvid} 的分析结果，请先运行：python -m app.analyze")

    video_data = matched_video.iloc[0].to_dict()
    analysis_data = matched_analysis.iloc[0].to_dict()
    prompt = build_prompt(video_data, analysis_data, matched_comments)

    print(f"正在生成报告：{bvid}")
    try:
        response = get_client().responses.create(
            model=MODEL_NAME,
            input=prompt,
        )
    except BadRequestError as error:
        raise RuntimeError(
            f"模型调用失败：当前 OPENAI_MODEL={MODEL_NAME} 可能不可用。"
            "请在 .env 中换成账号可用的模型，例如 gpt-5.4-mini、gpt-5.2 或 gpt-4.1-mini。"
        ) from error

    report = response.output_text
    output_path = REPORT_DIR / f"report_{bvid}.md"
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"报告已保存：{output_path}")
    return report


if __name__ == "__main__":
    input_bvid = input("请输入要分析的 BV 号：").strip()
    generated_report = generate_report(input_bvid)
    print("\n========== AI 分析报告 ==========\n")
    print(generated_report)
