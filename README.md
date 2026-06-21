# Bilibili Game Viral Agent

一个用来分析 B 站游戏区高播放视频的小型内容分析工具。它会抓取近 30 天游戏相关视频的基础数据，计算互动指标，再结合少量评论样本和大模型生成复盘报告与原创企划草案。

我做这个项目的目的，是模拟游戏内容运营里常见的一个问题：看到一条游戏视频突然起量之后，如何判断它是选题踩中了热点、UP 主本身有稳定热度，还是评论区/转发带来了二次传播。

## 当前功能

- 采集 B 站游戏相关分区的视频基础数据
- 筛选近 30 天、播放量达到阈值的视频
- 计算点赞率、投币率、收藏率、转发率、评论率、弹幕率
- 根据互动指标给出内容类型判断
- 保留公开接口能拿到的评论样本
- 生成单条视频复盘报告和原创企划草案
- 生成批量总览报告
- 生成数据质量评分表
- 生成一个本地 HTML Dashboard

## 工作流

```text
采集视频数据
→ 清洗和筛选
→ 计算互动指标
→ 判断内容类型
→ 整理评论样本
→ 调用 LLM 生成报告
→ 输出 Dashboard 和 Markdown 报告
```

## 项目结构

```text
app/
  bili_client.py        B 站公开接口请求封装
  collect.py            采集视频数据和评论样本
  analyze.py            计算互动指标和内容类型
  llm_report.py         生成单条视频分析报告
  overview_report.py    生成批量总览报告
  score_reports.py      生成数据质量评分
  dashboard.py          生成本地 HTML Dashboard
  agent.py              一键运行入口
```

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

复制 `.env.example` 为 `.env`，然后填写自己的 OpenAI API Key：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5.4-mini
```

## 使用

采集数据：

```powershell
python -m app.collect
```

计算基础指标：

```powershell
python -m app.analyze
```

运行完整流程：

```powershell
python -m app.agent
```

只生成 Dashboard：

```powershell
python -m app.dashboard
```

## 输出

运行后会在本地 `data/` 目录生成：

- `hot_game_videos.csv`：入选视频基础数据
- `hot_game_comments.csv`：评论样本
- `video_analysis.csv`：指标分析结果
- `quality_scores.csv`：数据质量评分
- `dashboard.html`：本地可视化页面
- `reports/`：单条视频报告和批量总览报告

`data/` 默认不会上传到 GitHub。

## 数据说明

这个项目使用公开可访问的数据接口做原型验证。评论接口有时只能返回少量样本，所以报告里会把评论文本作为辅助证据，主要判断仍然基于播放、点赞、收藏、转发、评论数、弹幕数等结构化指标。

项目不会复刻原视频内容，只分析可以复用的内容机制，例如选题角度、情绪钩子、视频结构和评论区触发点。

## 可以继续改进的地方

- 接入官方授权数据源
- 增加 UP 主完整历史视频分析
- 增加定时任务和自动日报
- 做成交互式 Web 页面
- 加入更稳定的评论数据源
- 对生成的企划做原创性和风险评分

## 简历描述

构建 B 站游戏内容爆款分析与原创企划生成 Agent，自动采集游戏区高播放视频数据，计算互动率、收藏率、转发率、评论率等指标，结合评论样本与 LLM 生成爆火原因、观众吸引点、可复用机制和原创内容企划，并通过 Dashboard 和数据质量评分辅助内容运营判断。
