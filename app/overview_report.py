from pathlib import Path

import pandas as pd
from openai import BadRequestError

from app.llm_report import DATA_DIR, REPORT_DIR, MODEL_NAME, get_client, get_latest_analysis_path


def load_overview_data():
    video_table = pd.read_csv(DATA_DIR / "hot_game_videos.csv")
    comment_table = pd.read_csv(DATA_DIR / "hot_game_comments.csv")
    analysis_table = pd.read_csv(get_latest_analysis_path())
    return video_table, comment_table, analysis_table


def build_overview_prompt(video_table, comment_table, analysis_table):
    top_by_views = analysis_table.sort_values(by="播放量", ascending=False).head(20)
    type_counts = analysis_table["内容类型判断"].value_counts().to_dict()
    comment_coverage = comment_table.groupby("BV号").size().reset_index(name="评论样本数")
    coverage_summary = {
        "有评论样本的视频数": int(comment_coverage["BV号"].nunique()) if not comment_coverage.empty else 0,
        "评论样本总数": int(len(comment_table)),
        "视频总数": int(len(video_table)),
    }

    return f"""
你是游戏内容增长分析 Agent，请基于本批 B站游戏区视频数据，生成一份批量总览报告。

请输出：
一、本批数据总体结论
二、爆款类型分布
三、互动指标洞察
四、评论样本覆盖情况与置信度说明
五、适合复用的游戏内容企划方向
六、适合写进简历的项目总结
七、下一步优化建议

内容类型分布：
{type_counts}

评论覆盖情况：
{coverage_summary}

播放量 Top 视频分析表：
{top_by_views.to_dict(orient="records")}
"""


def generate_overview_report():
    video_table, comment_table, analysis_table = load_overview_data()
    prompt = build_overview_prompt(video_table, comment_table, analysis_table)

    print("正在生成批量总览报告...")
    try:
        response = get_client().responses.create(
            model=MODEL_NAME,
            input=prompt,
        )
    except BadRequestError as error:
        raise RuntimeError(f"模型调用失败：OPENAI_MODEL={MODEL_NAME} 可能不可用。") from error

    output_path = REPORT_DIR / "overview_report.md"
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(response.output_text)

    print(f"批量总览报告已保存：{output_path}")
    return output_path


if __name__ == "__main__":
    generate_overview_report()
