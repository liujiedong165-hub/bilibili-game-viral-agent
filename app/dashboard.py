from pathlib import Path

import pandas as pd

from app.llm_report import DATA_DIR, get_latest_analysis_path


OUTPUT_PATH = DATA_DIR / "dashboard.html"


def render_table(df, columns, limit=20):
    return df[columns].head(limit).to_html(index=False, escape=False)


def build_dashboard():
    video_table = pd.read_csv(DATA_DIR / "hot_game_videos.csv")
    comment_table = pd.read_csv(DATA_DIR / "hot_game_comments.csv")
    analysis_table = pd.read_csv(get_latest_analysis_path())

    comment_counts = comment_table.groupby("BV号").size().reset_index(name="评论样本数") if not comment_table.empty else pd.DataFrame(columns=["BV号", "评论样本数"])
    merged = analysis_table.merge(comment_counts, on="BV号", how="left")
    merged["评论样本数"] = merged["评论样本数"].fillna(0).astype(int)

    top_views = merged.sort_values(by="播放量", ascending=False)
    top_interaction = merged.sort_values(by="互动率", ascending=False)
    type_counts = merged["内容类型判断"].value_counts().reset_index()
    type_counts.columns = ["内容类型", "数量"]

    html = f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>B站游戏爆款分析 Agent Dashboard</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 32px; color: #1f2933; }}
    h1, h2 {{ margin-bottom: 12px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }}
    .metric {{ border: 1px solid #d7dee8; padding: 14px; border-radius: 8px; }}
    .metric strong {{ display: block; font-size: 24px; margin-top: 6px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 28px; font-size: 14px; }}
    th, td {{ border: 1px solid #d7dee8; padding: 8px; text-align: left; }}
    th {{ background: #f3f6fa; }}
  </style>
</head>
<body>
  <h1>B站游戏爆款分析 Agent Dashboard</h1>
  <div class="metrics">
    <div class="metric">视频数量<strong>{len(video_table)}</strong></div>
    <div class="metric">评论样本<strong>{len(comment_table)}</strong></div>
    <div class="metric">最高播放<strong>{int(video_table["播放量"].max()):,}</strong></div>
    <div class="metric">平均互动率<strong>{merged["互动率"].mean():.3f}</strong></div>
  </div>

  <h2>播放量 Top 视频</h2>
  {render_table(top_views, ["BV号", "视频标题", "UP主名称", "播放量", "互动率", "评论样本数", "内容类型判断"], 20)}

  <h2>互动率 Top 视频</h2>
  {render_table(top_interaction, ["BV号", "视频标题", "UP主名称", "播放量", "互动率", "收藏率", "转发率", "评论率", "评论样本数"], 20)}

  <h2>内容类型分布</h2>
  {type_counts.to_html(index=False, escape=False)}
</body>
</html>
"""

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        file.write(html)

    print(f"Dashboard 已保存：{OUTPUT_PATH}")
    return OUTPUT_PATH


if __name__ == "__main__":
    build_dashboard()
