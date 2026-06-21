from pathlib import Path

import pandas as pd

from app.llm_report import DATA_DIR, REPORT_DIR, get_latest_analysis_path


def score_data_quality():
    video_table = pd.read_csv(DATA_DIR / "hot_game_videos.csv")
    comment_table = pd.read_csv(DATA_DIR / "hot_game_comments.csv")
    analysis_table = pd.read_csv(get_latest_analysis_path())

    comment_counts = comment_table.groupby("BV号").size().to_dict() if not comment_table.empty else {}
    rows = []

    for _, row in analysis_table.iterrows():
        bvid = row["BV号"]
        comment_count = int(comment_counts.get(bvid, 0))
        interaction_rate = float(row["互动率"])
        views = int(row["播放量"])

        comment_score = min(comment_count / 10, 1.0) * 40
        metric_score = min(interaction_rate / 0.2, 1.0) * 30
        scale_score = min(views / 1_000_000, 1.0) * 30
        total_score = round(comment_score + metric_score + scale_score, 1)

        if comment_count >= 10:
            confidence = "高"
        elif comment_count >= 3:
            confidence = "中"
        else:
            confidence = "低"

        rows.append(
            {
                "BV号": bvid,
                "视频标题": row["视频标题"],
                "播放量": views,
                "互动率": interaction_rate,
                "评论样本数": comment_count,
                "数据质量分": total_score,
                "评论置信度": confidence,
            }
        )

    score_table = pd.DataFrame(rows).sort_values(by="数据质量分", ascending=False)
    output_path = DATA_DIR / "quality_scores.csv"
    score_table.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"质量评分已保存：{output_path}")
    return output_path


if __name__ == "__main__":
    score_data_quality()
