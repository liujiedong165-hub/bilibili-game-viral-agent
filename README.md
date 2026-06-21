# B站游戏爆款分析与原创企划生成 Agent

这是一个面向游戏内容运营场景的 AI Agent 原型。项目会采集 B站游戏区高播放视频数据，计算互动指标，结合评论样本和 LLM 生成爆火复盘、观众吸引点分析与原创内容企划。

## 功能

- 采集 B站游戏区近 30 天高播放视频数据
- 计算互动率、点赞率、收藏率、转发率、评论率、弹幕率
- 判断内容类型：攻略资料型、社交传播型、争议讨论型等
- 生成数据质量评分
- 生成静态 Dashboard
- 调用 LLM 生成单条视频爆火报告
- 生成批量总览报告和原创企划方向

## 项目结构

```text
app/
  bili_client.py              B站公开接口请求
  collect.py                  视频与评论样本采集
  analyze.py                  基础指标分析
  llm_report.py               单视频 AI 报告生成
  overview_report.py          批量总览报告
  score_reports.py            数据质量评分
  dashboard.py                静态 Dashboard
  agent.py                    Agent 总入口
```

## 环境配置

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

复制 `.env.example` 为 `.env`，并填写自己的 OpenAI API Key：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5.4-mini
```

## 运行方式

采集数据：

```powershell
python -m app.collect
```

基础分析：

```powershell
python -m app.analyze
```

运行完整 Agent：

```powershell
python -m app.agent
```

只生成 Dashboard：

```powershell
python -m app.dashboard
```

## 输出文件

运行后会在本地 `data/` 文件夹生成 CSV、HTML 和 Markdown 报告。该目录默认不上传 GitHub。

## 项目边界

- 本项目使用公开可访问的数据接口做 MVP 原型。
- 评论文本可能受公开接口限制，系统会保留能采集到的样本，并基于数据质量评分标注置信度。
- 项目不复刻原视频内容，只分析可复用的选题机制、结构机制和传播机制。

## 简历描述

构建 B站游戏内容爆款分析与原创企划生成 Agent，自动采集游戏区高播放视频数据，计算互动率、收藏率、转发率、评论率等指标，结合评论样本与 LLM 生成爆火原因、观众吸引点、可复用机制和原创内容企划，并通过 Dashboard 和质量评分辅助游戏内容运营决策。
