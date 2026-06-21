import os
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from app.bili_client import (
    BiliApiError,
    PartialCommentsError,
    get_game_ranking,
    get_region_recent_videos,
    get_video_detail,
    get_video_stat_from_detail,
    get_hot_comments,
)


DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

VERBOSE = os.getenv("VERBOSE") == "1"

DAY_WINDOW = 30
MIN_VIEWS = 300_000
PAGES_PER_REGION = 20
PAGE_SIZE = 50

COMMENT_MAX_PER_VIDEO = 10
COMMENT_MAX_PAGES = 3
COMMENT_DELAY_SECONDS = 1
COMMENT_BETWEEN_VIDEOS_SECONDS = 2

FAILED_BVIDS_PATH = DATA_DIR / "failed_bvids.csv"
FAILED_COMMENTS_PATH = DATA_DIR / "failed_comments.csv"
RETRY_BVIDS_PATH = DATA_DIR / "retry_bvids.txt"
INPUT_BVIDS_PATH = DATA_DIR / "input_bvids.txt"

GAME_REGIONS = [
    {"rid": 4, "name": "游戏主分区"},
    {"rid": 17, "name": "单机游戏"},
    {"rid": 65, "name": "网络游戏"},
    {"rid": 171, "name": "电子竞技"},
    {"rid": 172, "name": "手机游戏"},
    {"rid": 173, "name": "桌游棋牌"},
    {"rid": 121, "name": "GMV"},
    {"rid": 136, "name": "音游"},
    {"rid": 19, "name": "Mugen"},
]


def log_verbose(message):
    if VERBOSE:
        print(message)


def stat_value(video, key, default=0):
    stat = video.get("stat") or {}
    return stat.get(key, default)


def normalize_candidate(video, source, region_name):
    pubdate = video.get("pubdate") or 0
    return {
        "bvid": video.get("bvid"),
        "aid": video.get("aid"),
        "标题": video.get("title"),
        "UP主ID": (video.get("owner") or {}).get("mid"),
        "UP主名称": (video.get("owner") or {}).get("name") or video.get("author"),
        "分区": video.get("tname") or region_name,
        "来源": source,
        "来源分区": region_name,
        "列表发布时间": datetime.fromtimestamp(pubdate).isoformat() if pubdate else "",
        "列表播放量": stat_value(video, "view"),
        "列表点赞数": stat_value(video, "like"),
        "列表收藏数": stat_value(video, "favorite"),
        "列表评论数": stat_value(video, "reply"),
        "列表弹幕数": stat_value(video, "danmaku"),
        "列表视频时长秒": video.get("duration"),
        "列表封面链接": video.get("pic"),
    }


def make_manual_candidate(bvid, source):
    return {
        "bvid": bvid,
        "aid": None,
        "标题": "",
        "UP主ID": "",
        "UP主名称": "",
        "分区": "",
        "来源": source,
        "来源分区": "手动输入",
        "列表发布时间": "",
        "列表播放量": 0,
        "列表点赞数": 0,
        "列表收藏数": 0,
        "列表评论数": 0,
        "列表弹幕数": 0,
        "列表视频时长秒": "",
        "列表封面链接": "",
    }


def collect_ranking_candidates(region, error_counter):
    rid = region["rid"]
    region_name = region["name"]
    candidates = []

    log_verbose(f"正在获取 {region_name} 排行榜视频...")
    try:
        for video in get_game_ranking(rid=rid):
            if video.get("bvid"):
                candidates.append(
                    normalize_candidate(
                        video=video,
                        source=f"{region_name}排行榜",
                        region_name=region_name,
                    )
                )
    except BiliApiError as error:
        error_counter[f"排行榜失败 code={error.code}"] += 1
        log_verbose(f"{region_name} 排行榜不可用，已跳过。")
    except Exception:
        error_counter["排行榜失败 其他错误"] += 1
        log_verbose(f"{region_name} 排行榜不可用，已跳过。")

    return candidates


def collect_recent_candidates(region, error_counter):
    rid = region["rid"]
    region_name = region["name"]
    candidates = []
    consecutive_404 = 0

    log_verbose(f"正在获取 {region_name} 近期视频，最多 {PAGES_PER_REGION} 页...")

    for page in range(1, PAGES_PER_REGION + 1):
        try:
            videos = get_region_recent_videos(
                rid=rid,
                page=page,
                page_size=PAGE_SIZE,
            )
            consecutive_404 = 0

            if not videos:
                log_verbose(f"{region_name} 第{page}页没有返回视频，停止扫描该分区。")
                break

            for video in videos:
                if video.get("bvid"):
                    candidates.append(
                        normalize_candidate(
                            video=video,
                            source=f"{region_name}近期视频第{page}页",
                            region_name=region_name,
                        )
                    )

        except BiliApiError as error:
            error_counter[f"近期视频失败 code={error.code}"] += 1
            if error.code == -404:
                consecutive_404 += 1
                if page == 1 or consecutive_404 >= 2:
                    log_verbose(f"{region_name} 近期视频接口无有效页，停止扫描该分区。")
                    break
                continue
            log_verbose(f"{region_name} 第{page}页接口不可用，已跳过。")
        except Exception:
            error_counter["近期视频失败 其他错误"] += 1
            log_verbose(f"{region_name} 第{page}页接口不可用，已跳过。")

    return candidates


def collect_bvid_file_candidates(path, source):
    candidates = []

    if not path.exists():
        return candidates

    print(f"检测到 {path}，正在读取 BV 号...")
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            bvid = line.strip()
            if bvid and not bvid.startswith("#"):
                candidates.append(make_manual_candidate(bvid=bvid, source=source))

    return candidates


def collect_candidate_videos():
    candidate_videos = []
    error_counter = Counter()
    retry_only = os.getenv("RETRY_ONLY") == "1"

    if retry_only:
        print("当前为只重试模式：只读取 retry_bvids.txt 和 input_bvids.txt。")
    else:
        for region in GAME_REGIONS:
            candidate_videos.extend(collect_ranking_candidates(region, error_counter))
            candidate_videos.extend(collect_recent_candidates(region, error_counter))

    candidate_videos.extend(collect_bvid_file_candidates(RETRY_BVIDS_PATH, "失败BV重试列表"))
    candidate_videos.extend(collect_bvid_file_candidates(INPUT_BVIDS_PATH, "手动BV号列表"))

    deduped = {}
    for video in candidate_videos:
        deduped[video["bvid"]] = video

    candidates = list(deduped.values())
    candidate_path = DATA_DIR / "candidate_videos.csv"
    pd.DataFrame(candidates).to_csv(candidate_path, index=False, encoding="utf-8-sig")
    print(f"候选视频清单已保存：{candidate_path}")

    if error_counter:
        print("候选源接口异常汇总：")
        for label, count in error_counter.items():
            print(f"- {label}：{count} 次")

    return candidates


def build_failure_row(candidate, stage, error, error_code=""):
    return {
        "BV号": candidate.get("bvid"),
        "标题": candidate.get("标题", ""),
        "来源": candidate.get("来源", ""),
        "来源分区": candidate.get("来源分区", ""),
        "失败阶段": stage,
        "错误代码": error_code,
        "错误信息": str(error),
        "记录时间": datetime.now().isoformat(timespec="seconds"),
    }


def save_csv_safely(table, path, label):
    try:
        table.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"{label}已保存：{path}")
        return path
    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback_path = path.with_name(f"{path.stem}_{timestamp}{path.suffix}")
        table.to_csv(fallback_path, index=False, encoding="utf-8-sig")
        print(f"{label}原文件被占用，已另存为：{fallback_path}")
        return fallback_path


def save_failed_bvids(failed_rows):
    columns = ["BV号", "标题", "来源", "来源分区", "失败阶段", "错误代码", "错误信息", "记录时间"]
    failed_table = pd.DataFrame(failed_rows, columns=columns)
    save_csv_safely(failed_table, FAILED_BVIDS_PATH, "失败 BV 清单")


def save_failed_comments(failed_comment_rows):
    columns = ["BV号", "标题", "来源", "来源分区", "失败阶段", "错误代码", "错误信息", "记录时间"]
    failed_table = pd.DataFrame(failed_comment_rows, columns=columns)
    save_csv_safely(failed_table, FAILED_COMMENTS_PATH, "评论采集失败清单")


def append_comments(video_row, comments, comment_rows):
    for comment in comments:
        comment["BV号"] = video_row["BV号"]
        comment["AV号"] = video_row["AV号"]
        comment["视频标题"] = video_row["视频标题"]
        comment_rows.append(comment)


def collect_comments_for_video(video_row, comment_rows, failed_comment_rows):
    bvid = video_row["BV号"]
    aid = video_row["AV号"]

    print(f"正在采集评论：{bvid}，最多 {COMMENT_MAX_PER_VIDEO} 条")

    try:
        comments = get_hot_comments(
            aid,
            max_comments=COMMENT_MAX_PER_VIDEO,
            max_pages=COMMENT_MAX_PAGES,
            delay_seconds=COMMENT_DELAY_SECONDS,
        )

        if comments:
            append_comments(video_row, comments, comment_rows)
            print(f"{bvid} 评论采集成功：{len(comments)} 条")
            return

        failed_comment_rows.append(
            {
                "BV号": bvid,
                "标题": video_row["视频标题"],
                "来源": video_row["数据来源"],
                "来源分区": video_row["来源分区"],
                "失败阶段": "评论采集",
                "错误代码": "NO_COMMENTS",
                "错误信息": "接口请求成功，但未返回评论文本",
                "记录时间": datetime.now().isoformat(timespec="seconds"),
            }
        )
        print(f"{bvid} 未返回评论文本。")

    except PartialCommentsError as error:
        append_comments(video_row, error.partial_comments, comment_rows)
        print(f"{bvid} 后续请求触发 412，已保留部分评论：{len(error.partial_comments)} 条")

    except BiliApiError as error:
        if error.code == 412:
            print(f"{bvid} 评论接口返回 412，未取得评论文本，仅保留视频基础数据。")
            return

        failed_comment_rows.append(
            {
                "BV号": bvid,
                "标题": video_row["视频标题"],
                "来源": video_row["数据来源"],
                "来源分区": video_row["来源分区"],
                "失败阶段": "评论采集",
                "错误代码": error.code,
                "错误信息": str(error),
                "记录时间": datetime.now().isoformat(timespec="seconds"),
            }
        )
        print(f"{bvid} 评论采集失败，但视频数据已保留：code={error.code}，message={error.message}")

    except Exception as error:
        failed_comment_rows.append(
            {
                "BV号": bvid,
                "标题": video_row["视频标题"],
                "来源": video_row["数据来源"],
                "来源分区": video_row["来源分区"],
                "失败阶段": "评论采集",
                "错误代码": "",
                "错误信息": str(error),
                "记录时间": datetime.now().isoformat(timespec="seconds"),
            }
        )
        print(f"{bvid} 评论采集失败，但视频数据已保留：{error}")

    time.sleep(COMMENT_BETWEEN_VIDEOS_SECONDS)


def collect_hot_game_videos():
    cutoff_time = datetime.now() - timedelta(days=DAY_WINDOW)

    video_rows = []
    comment_rows = []
    failed_rows = []
    failed_comment_rows = []
    skipped_by_date = 0
    skipped_by_views = 0

    candidate_videos = collect_candidate_videos()
    print(f"去重后候选视频数量：{len(candidate_videos)}")
    print(f"开始筛选近{DAY_WINDOW}天、播放量大于等于 {MIN_VIEWS} 的视频...")

    if not candidate_videos:
        print("没有获取到候选视频。")
        print("你可以手动创建 data/input_bvids.txt，每行放一个 BV 号。")
        save_failed_bvids([])
        save_failed_comments([])
        return pd.DataFrame(), pd.DataFrame()

    for index, candidate in enumerate(candidate_videos, start=1):
        bvid = candidate["bvid"]
        print(f"正在处理第 {index}/{len(candidate_videos)} 个视频：{bvid}")

        try:
            list_publish_time = candidate.get("列表发布时间")
            list_views = int(candidate.get("列表播放量") or 0)

            if list_publish_time:
                publish_time_from_list = datetime.fromisoformat(list_publish_time)
                if publish_time_from_list < cutoff_time:
                    skipped_by_date += 1
                    continue

            if list_views and list_views < MIN_VIEWS:
                skipped_by_views += 1
                continue

            detail = get_video_detail(bvid)
            stat = get_video_stat_from_detail(detail)
            publish_time = datetime.fromtimestamp(detail.get("pubdate", 0))

            if publish_time < cutoff_time:
                skipped_by_date += 1
                continue

            if stat.get("view", 0) < MIN_VIEWS:
                skipped_by_views += 1
                continue

            video_rows.append(
                {
                    "BV号": bvid,
                    "AV号": detail.get("aid"),
                    "CID": detail.get("cid"),
                    "视频标题": detail.get("title"),
                    "UP主ID": detail.get("owner", {}).get("mid"),
                    "UP主名称": detail.get("owner", {}).get("name"),
                    "分区": detail.get("tname") or candidate.get("分区"),
                    "发布时间": publish_time.isoformat(),
                    "视频时长秒": detail.get("duration"),
                    "播放量": stat.get("view", 0),
                    "点赞数": stat.get("like", 0),
                    "投币数": stat.get("coin", 0),
                    "收藏数": stat.get("favorite", 0),
                    "转发数": stat.get("share", 0),
                    "评论数": stat.get("reply", 0),
                    "弹幕数": stat.get("danmaku", 0),
                    "封面链接": detail.get("pic"),
                    "视频链接": f"https://www.bilibili.com/video/{bvid}",
                    "数据来源": candidate.get("来源"),
                    "来源分区": candidate.get("来源分区"),
                }
            )

        except BiliApiError as error:
            failed_rows.append(build_failure_row(candidate, "视频详情解析", error, error.code))
            print(f"处理 {bvid} 失败，已记录到 failed_bvids.csv：code={error.code}，message={error.message}")

        except Exception as error:
            failed_rows.append(build_failure_row(candidate, "视频详情解析", error))
            print(f"处理 {bvid} 失败，已记录到 failed_bvids.csv：{error}")

    print(f"开始为所有入选视频采集评论，每个视频最多 {COMMENT_MAX_PER_VIDEO} 条。")
    print("策略：能拿几条就保存几条；遇到 412 时保留已拿到的部分评论。")
    for index, video_row in enumerate(video_rows, start=1):
        print(f"评论进度：{index}/{len(video_rows)}")
        collect_comments_for_video(video_row, comment_rows, failed_comment_rows)

    video_table = pd.DataFrame(video_rows)
    comment_table = pd.DataFrame(comment_rows)

    video_path = DATA_DIR / "hot_game_videos.csv"
    comment_path = DATA_DIR / "hot_game_comments.csv"

    save_csv_safely(video_table, video_path, "视频数据")
    save_csv_safely(comment_table, comment_path, "评论数据")
    save_failed_bvids(failed_rows)
    save_failed_comments(failed_comment_rows)

    print("采集完成。")
    print(f"最终入选视频数量：{len(video_rows)}")
    print(f"评论样本数量：{len(comment_rows)}")
    print(f"因发布时间过早跳过：{skipped_by_date}")
    print(f"因播放量低于阈值跳过：{skipped_by_views}")
    print(f"失败 BV 数量：{len(failed_rows)}")
    print(f"评论采集失败数量：{len(failed_comment_rows)}")
    print(f"视频数据已保存：{video_path}")
    print(f"评论数据已保存：{comment_path}")

    return video_table, comment_table


if __name__ == "__main__":
    collect_hot_game_videos()
