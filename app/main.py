from app.analyze import analyze_video_data
from app.collect import collect_hot_game_videos
from app.llm_report import generate_report


def main():
    print("欢迎使用 B站游戏爆款分析 Agent")
    print("请选择要执行的操作：")
    print("1. 采集近7天游戏区百万播放视频")
    print("2. 分析已采集视频的数据")
    print("3. 生成某个视频的 AI 爆款分析报告")
    print("4. 依次执行采集和分析")

    choice = input("请输入数字 1/2/3/4：").strip()

    if choice == "1":
        collect_hot_game_videos()
    elif choice == "2":
        analyze_video_data()
    elif choice == "3":
        bvid = input("请输入要分析的 BV 号：").strip()
        generate_report(bvid)
    elif choice == "4":
        collect_hot_game_videos()
        analyze_video_data()
        print("采集和基础分析已完成。")
        print("如需生成 AI 报告，请重新运行：python -m app.main，然后选择 3。")
    else:
        print("输入无效，请重新运行程序，并输入 1/2/3/4。")


if __name__ == "__main__":
    main()
