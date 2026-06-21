from datetime import datetime
from pathlib import Path

import pandas as pd


DATA_DIR = Path("data")
MANUAL_COMMENTS_PATH = DATA_DIR / "manual_comments.csv"
HOT_COMMENTS_PATH = DATA_DIR / "hot_game_comments.csv"
HOT_VIDEOS_PATH = DATA_DIR / "hot_game_videos.csv"

REQUIRED_COLUMNS = ["BV号", "评论内容"]
OUTPUT_COLUMNS = ["评论id", "评论内容", "评论点赞数", "评论回复数", "评论时间", "BV号", "AV号", "视频标题"]


def ensure_manual_template():
    if MANUAL_COMMENTS_PATH.exists():
        return

    template = pd.DataFrame(
        [
            {
                "BV号": "BV这里换成真实BV号",
                "评论内容": "这里粘贴评论文本",
                "评论点赞数": 0,
                "评论回复数": 0,
                "评论时间": "",
            }
        ]
    )
    template.to_csv(MANUAL_COMMENTS_PATH, index=False, encoding="utf-8-sig")
    print(f"已创建手动评论模板：{MANUAL_COMMENTS_PATH}")


def load_video_lookup():
    if not HOT_VIDEOS_PATH.exists():
        return {}

    videos = pd.read_csv(HOT_VIDEOS_PATH)
    lookup = {}
    for _, row in videos.iterrows():
        lookup[row["BV号"]] = {
            "AV号": row.get("AV号", ""),
            "视频标题": row.get("视频标题", ""),
        }
    return lookup


def normalize_manual_comments(manual_comments):
    for column in REQUIRED_COLUMNS:
        if column not in manual_comments.columns:
            raise ValueError(f"manual_comments.csv 缺少必填列：{column}")

    video_lookup = load_video_lookup()
    rows = []

    for index, row in manual_comments.iterrows():
        bvid = str(row.get("BV号", "")).strip()
        content = str(row.get("评论内容", "")).strip()

        if not bvid or bvid.startswith("#") or bvid == "BV这里换成真实BV号":
            continue
        if not content or content == "这里粘贴评论文本":
            continue

        video_info = video_lookup.get(bvid, {})
        rows.append(
            {
                "评论id": f"manual_{bvid}_{index}",
                "评论内容": content,
                "评论点赞数": row.get("评论点赞数", 0),
                "评论回复数": row.get("评论回复数", 0),
                "评论时间": row.get("评论时间", "") or datetime.now().isoformat(timespec="seconds"),
                "BV号": bvid,
                "AV号": video_info.get("AV号", ""),
                "视频标题": video_info.get("视频标题", row.get("视频标题", "")),
            }
        )

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def save_csv_safely(table, path):
    try:
        table.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"已保存：{path}")
    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback_path = path.with_name(f"{path.stem}_{timestamp}{path.suffix}")
        table.to_csv(fallback_path, index=False, encoding="utf-8-sig")
        print(f"原文件被占用，已另存为：{fallback_path}")


def import_manual_comments():
    ensure_manual_template()

    manual_comments = pd.read_csv(MANUAL_COMMENTS_PATH)
    normalized = normalize_manual_comments(manual_comments)

    if normalized.empty:
        print("manual_comments.csv 中没有可导入的评论。")
        print("请填写 BV号 和 评论内容 后重新运行：python -m app.import_manual_comments")
        return

    if HOT_COMMENTS_PATH.exists():
        existing = pd.read_csv(HOT_COMMENTS_PATH)
    else:
        existing = pd.DataFrame(columns=OUTPUT_COLUMNS)

    merged = pd.concat([existing, normalized], ignore_index=True)
    merged = merged.drop_duplicates(subset=["BV号", "评论内容"], keep="first")

    save_csv_safely(merged, HOT_COMMENTS_PATH)
    print(f"本次导入手动评论：{len(normalized)} 条")
    print(f"合并后评论总数：{len(merged)} 条")


if __name__ == "__main__":
    import_manual_comments()
