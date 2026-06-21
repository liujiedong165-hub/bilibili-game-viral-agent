import time
from datetime import datetime

import requests


HEADERS = {
    "User-Agent": "Mozilla/5.0 GameViralAgent/0.1",
    "Referer": "https://www.bilibili.com/",
}


class BiliApiError(RuntimeError):
    def __init__(self, code, message, payload=None):
        self.code = code
        self.message = message
        self.payload = payload or {}
        super().__init__(f"B站接口返回异常：code={code}，message={message}")


class PartialCommentsError(BiliApiError):
    def __init__(self, code, message, partial_comments, payload=None):
        self.partial_comments = partial_comments
        super().__init__(code=code, message=message, payload=payload)


def get_json(url, params=None, request_delay=0.8):
    """请求 B站公开接口，并返回 data 字段。"""
    try:
        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=20,
        )

        if response.status_code == 412:
            raise BiliApiError(
                code=412,
                message="Precondition Failed，通常表示评论接口触发请求条件限制或风控",
                payload={"url": response.url},
            )

        response.raise_for_status()
        data = response.json()

        if data.get("code") != 0:
            raise BiliApiError(
                code=data.get("code"),
                message=data.get("message"),
                payload=data,
            )

        time.sleep(request_delay)
        return data.get("data") or {}

    except BiliApiError:
        raise
    except Exception as error:
        raise RuntimeError(f"请求 B站接口失败：{error}")


def get_game_ranking(rid=4):
    """获取指定游戏分区排行榜。"""
    data = get_json(
        "https://api.bilibili.com/x/web-interface/ranking/v2",
        {
            "rid": rid,
            "type": "all",
        },
    )
    return data.get("list", [])


def get_region_recent_videos(rid=4, page=1, page_size=50):
    """获取指定分区近期视频。"""
    data = get_json(
        "https://api.bilibili.com/x/web-interface/dynamic/region",
        {
            "rid": rid,
            "pn": page,
            "ps": page_size,
        },
    )
    return data.get("archives", [])


def get_video_detail(bvid):
    """根据 BV 号获取视频详情。"""
    return get_json(
        "https://api.bilibili.com/x/web-interface/view",
        {
            "bvid": bvid,
        },
    )


def get_video_stat_from_detail(detail):
    """从视频详情中读取播放、点赞、收藏、评论等数据。"""
    stat = detail.get("stat") or {}

    if not stat:
        raise RuntimeError("未能从视频详情中读取统计数据")

    return stat


def normalize_comment(item):
    return {
        "评论id": item.get("rpid"),
        "评论内容": item.get("content", {}).get("message", ""),
        "评论点赞数": item.get("like", 0),
        "评论回复数": item.get("rcount", 0),
        "评论时间": datetime.fromtimestamp(item.get("ctime", 0)).isoformat(),
    }


def get_hot_comments(
    aid,
    max_comments=10,
    max_pages=3,
    delay_seconds=1,
):
    """获取单个视频评论文本。

    如果前面已经拿到部分评论，后续请求遇到 412，会返回已拿到的部分评论。
    """
    comments = []
    seen_comment_ids = set()

    for sort in [2, 1]:
        for page in range(1, max_pages + 1):
            if len(comments) >= max_comments:
                return comments[:max_comments]

            params = {
                "type": 1,
                "oid": aid,
                "pn": page,
                "ps": 20,
                "sort": sort,
            }

            try:
                data = get_json(
                    "https://api.bilibili.com/x/v2/reply",
                    params,
                    request_delay=0,
                )
            except BiliApiError as error:
                if error.code == 412 and comments:
                    raise PartialCommentsError(
                        code=412,
                        message="评论接口触发 412，但已取得部分评论",
                        partial_comments=comments[:max_comments],
                        payload=error.payload,
                    )
                raise

            replies = data.get("replies") or []

            for item in replies:
                comment_id = item.get("rpid")
                if comment_id in seen_comment_ids:
                    continue

                seen_comment_ids.add(comment_id)
                comments.append(normalize_comment(item))

                if len(comments) >= max_comments:
                    return comments[:max_comments]

            time.sleep(delay_seconds)

            if not replies:
                break

    return comments[:max_comments]
