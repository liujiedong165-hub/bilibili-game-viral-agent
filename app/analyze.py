from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")


def save_csv_safely(table, path, label):
    try:
        table.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"{label}已保存：{path}")
        return path
    except PermissionError:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback_path = path.with_name(f"{path.stem}_{timestamp}{path.suffix}")
        table.to_csv(fallback_path, index=False, encoding="utf-8-sig")
        print(f"{label}原文件被占用，已另存为：{fallback_path}")
        return fallback_path


def safe_divide(numerator, denominator):
    if denominator == 0:
        return 0
    return numerator / denominator


def classify_content_type(favorite_rate, share_rate, comment_rate, danmaku_rate):
    if favorite_rate >= 0.02:
        return "攻略资料型：收藏率高，观众可能觉得有保存价值"
    if share_rate >= 0.006:
        return "社交传播型：转发率高，适合传播或讨论"
    if comment_rate >= 0.005:
        return "争议讨论型：评论率高，评论区可能有明显讨论点"
    if danmaku_rate >= 0.008:
        return "情绪共鸣型：弹幕率高，观看过程中的即时反馈较强"
    return "综合推荐型：可能由选题、标题、封面和推荐共同推动"


def classify_creator_status(current_views, median_views, sample_count):
    if sample_count < 3:
        return "样本不足：当前只采集到少量该UP主视频，暂不能严格判断"

    if median_views == 0:
        return "样本不足：缺少该UP主历史播放数据"

    viral_index = current_views / median_views

    if viral_index >= 5:
        return f"偶然爆火倾向：本视频约为该UP主样本中位播放的 {viral_index:.1f} 倍"
    if viral_index >= 2:
        return f"明显高于平时：本视频约为该UP主样本中位播放的 {viral_index:.1f} 倍"
    return f"持续热度倾向：本视频与该UP主样本表现接近，爆火指数 {viral_index:.1f}"


def analyze_video_data():
    video_path = DATA_DIR / "hot_game_videos.csv"

    if not video_path.exists():
        raise FileNotFoundError("未找到 data/hot_game_videos.csv，请先运行：python -m app.collect")

    video_table = pd.read_csv(video_path)

    if video_table.empty:
        print("没有采集到符合条件的视频。")
        return pd.DataFrame()

    up_stats = video_table.groupby("UP主ID")["播放量"].agg(["median", "count"]).reset_index()
    up_stats = up_stats.rename(
        columns={
            "median": "UP主样本中位播放量",
            "count": "UP主样本视频数",
        }
    )

    video_table = video_table.merge(up_stats, on="UP主ID", how="left")
    analysis_rows = []

    for _, row in video_table.iterrows():
        views = int(row["播放量"])
        total_interactions = (
            int(row["点赞数"])
            + int(row["投币数"])
            + int(row["收藏数"])
            + int(row["转发数"])
            + int(row["评论数"])
        )

        interaction_rate = safe_divide(total_interactions, views)
        like_rate = safe_divide(int(row["点赞数"]), views)
        coin_rate = safe_divide(int(row["投币数"]), views)
        favorite_rate = safe_divide(int(row["收藏数"]), views)
        share_rate = safe_divide(int(row["转发数"]), views)
        comment_rate = safe_divide(int(row["评论数"]), views)
        danmaku_rate = safe_divide(int(row["弹幕数"]), views)

        content_type = classify_content_type(
            favorite_rate=favorite_rate,
            share_rate=share_rate,
            comment_rate=comment_rate,
            danmaku_rate=danmaku_rate,
        )

        creator_status = classify_creator_status(
            current_views=views,
            median_views=float(row["UP主样本中位播放量"]),
            sample_count=int(row["UP主样本视频数"]),
        )

        analysis_rows.append(
            {
                "BV号": row["BV号"],
                "视频标题": row["视频标题"],
                "UP主名称": row["UP主名称"],
                "播放量": views,
                "互动率": round(interaction_rate, 4),
                "点赞率": round(like_rate, 4),
                "投币率": round(coin_rate, 4),
                "收藏率": round(favorite_rate, 4),
                "转发率": round(share_rate, 4),
                "评论率": round(comment_rate, 4),
                "弹幕率": round(danmaku_rate, 4),
                "内容类型判断": content_type,
                "UP主样本视频数": int(row["UP主样本视频数"]),
                "UP主样本中位播放量": int(row["UP主样本中位播放量"]),
                "UP主状态判断": creator_status,
            }
        )

    result_table = pd.DataFrame(analysis_rows)
    output_path = DATA_DIR / "video_analysis.csv"
    saved_path = save_csv_safely(result_table, output_path, "分析结果")

    print("基础分析完成。")
    print(f"分析结果路径：{saved_path}")
    print(result_table.head())

    return result_table


if __name__ == "__main__":
    analyze_video_data()
