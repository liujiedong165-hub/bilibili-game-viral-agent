from pathlib import Path

import pandas as pd

from app.analyze import analyze_video_data
from app.dashboard import build_dashboard
from app.llm_report import generate_report, get_latest_analysis_path
from app.overview_report import generate_overview_report
from app.score_reports import score_data_quality


DATA_DIR = Path("data")


def select_agent_targets(limit=5):
    try:
        analysis_path = get_latest_analysis_path()
    except FileNotFoundError:
        analyze_video_data()
        analysis_path = get_latest_analysis_path()

    analysis = pd.read_csv(analysis_path)
    if analysis.empty:
        return []

    ranked = analysis.sort_values(
        by=["播放量", "互动率", "评论率"],
        ascending=[False, False, False],
    )
    return ranked["BV号"].head(limit).tolist()


def run_agent(limit=5):
    print("开始运行游戏爆款分析 Agent。")
    analyze_video_data()
    score_data_quality()
    build_dashboard()

    targets = select_agent_targets(limit=limit)
    print(f"本次选择 {len(targets)} 个重点视频生成报告：")
    for bvid in targets:
        print(f"- {bvid}")

    for bvid in targets:
        generate_report(bvid)

    generate_overview_report()
    print("Agent 运行完成。报告保存在 data/reports 文件夹。")


if __name__ == "__main__":
    raw_limit = input("请输入要生成报告的视频数量，默认 5：").strip()
    limit = int(raw_limit) if raw_limit else 5
    run_agent(limit=limit)
