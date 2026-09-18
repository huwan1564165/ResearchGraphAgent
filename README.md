# ResearchGraph

ResearchGraph 是一个可追溯的深度研究 Agent MVP。它把用户输入的复杂研究问题拆分成子问题，搜索并保存来源，提取原文证据，整理研究结论，最后生成带引用的 Markdown 报告。

项目的核心关系是：

```text
Claim（结论） → Evidence（证据） → Source（来源）
```

报告中的结论只使用系统保存的证据，用户可以从结论回溯到证据和来源。

## 功能

- 创建研究项目，填写研究问题、时间范围、地区、研究对象和关注重点。
- 使用 LLM 或规则式方法生成 3 个研究子问题。
- 编辑、删除、添加和确认子问题。
- 使用 Demo、Semantic Scholar 或 Crossref 搜索来源。
- 保存来源并按 URL 去重。
- 从来源摘要或正文中提取原文证据。
- 生成 Claim、置信度和不确定性说明。
- 生成带 `[E1]` 等证据引用和来源链接的报告。
- 查询 Claim 到 Evidence 到 Source 的追溯链。
- LLM 调用失败或证据为空时自动回退到规则式处理。

## 环境要求

- Python 3.10 或更高版本。
- Git（可选，用于版本管理）。
- 使用真实 LLM 时，需要一个 OpenAI 兼容接口和 API Key。

项目当前主要使用 Python 标准库，不需要额外安装第三方 Python 包即可运行和测试。

## 安装

在项目目录执行：

```powershell
git clone https://github.com/huwan1564165/ResearchGraphAgent.git
cd ResearchGraphAgent
```

建议创建虚拟环境：

```powershell
python -m venv .venv
\.venv\Scripts\Activate.ps1
```

如果 PowerShell 禁止执行脚本，可以直接使用虚拟环境中的 Python：

```powershell
.\.venv\Scripts\python.exe app.py
```

## 配置

复制配置模板：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`：

```dotenv
RESEARCHGRAPH_APP_NAME=ResearchGraph
RESEARCHGRAPH_ENV=development
RESEARCHGRAPH_DB_PATH=data/researchgraph.db

# 配置后使用真实 LLM；留空时使用规则式问题拆解。
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# demo / semantic_scholar / crossref
RESEARCHGRAPH_SEARCH_PROVIDER=demo
SEMANTIC_SCHOLAR_API_KEY=
```

说明：

- `OPENAI_BASE_URL` 可以填写任何兼容 Chat Completions 接口的网关地址。
- 不要把包含真实 API Key 的 `.env` 提交到 Git；该文件已被 `.gitignore` 忽略。
- 网页生成子问题后会显示实际模式：`LLM` 或 `规则式`。
- 使用 `semantic_scholar` 时，如果服务限流或不可用，系统会回退到 Crossref。

## 启动网页

```powershell
python app.py
```

启动后访问：

```text
http://127.0.0.1:8000
```

网页操作流程：

1. 填写研究项目和研究问题，点击“创建项目”。
2. 查看生成的子问题。页面会显示使用的是 LLM 还是规则式模式。
3. 编辑、删除或添加子问题。
4. 点击“确认并运行研究”。
5. 查看报告、证据引用和来源链接。

首次演示建议使用 `RESEARCHGRAPH_SEARCH_PROVIDER=demo`，这样不依赖外部搜索服务，结果稳定且可重复。

## JSON API

应用同时提供无框架 JSON API。

创建项目：

```http
POST /api/projects
Content-Type: application/json
```

请求示例：

```json
{
  "title": "学习效果研究",
  "research_question": "大语言模型是否能够提升中学生的学习效果？",
  "time_range": "2020 年以后",
  "region": "中国",
  "subject": "中学生",
  "focus": "数学和英语学习"
}
```

主要接口：

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `POST` | `/api/projects` | 创建研究项目 |
| `POST` | `/api/projects/{id}/questions` | 生成子问题 |
| `GET` | `/api/projects/{id}/questions` | 获取子问题 |
| `POST` | `/api/projects/{id}/questions/add` | 添加子问题 |
| `PATCH` | `/api/projects/{id}/questions/{question_id}` | 修改子问题 |
| `DELETE` | `/api/projects/{id}/questions/{question_id}` | 删除子问题 |
| `POST` | `/api/projects/{id}/questions/confirm` | 确认子问题 |
| `POST` | `/api/projects/{id}/run` | 执行搜索、证据提取和报告生成 |
| `GET` | `/api/projects/{id}/report` | 获取最新报告 |
| `GET` | `/api/projects/{id}/evidence` | 获取证据及来源详情 |
| `GET` | `/api/projects/{id}/trace?claim_id={id}` | 查询结论追溯链 |

生成子问题的接口会返回实际运行模式：

```json
{
  "question_ids": [1, 2, 3],
  "mode": "llm"
}
```

没有配置 API Key 时，`mode` 会是 `rule_based`。

## 测试

项目使用 Python 标准库 `unittest`：

```powershell
python -m unittest discover -s tests -v
```

也可以检查所有 Python 文件是否能编译：

```powershell
python -m compileall -q agent models tools web app.py config.py
```

测试覆盖配置读取、LLM 客户端、规则式和 LLM 证据抽取、搜索回退、SQLite 存储、API、网页和完整 Demo 流程。

## 常见问题

### 为什么页面显示“规则式”？

通常是因为 `OPENAI_API_KEY` 没有配置，或者 `.env` 不在项目根目录。检查 `.env` 文件和 `OPENAI_BASE_URL` 配置后重启应用。

### LLM 调用失败后会发生什么？

问题拆解阶段会返回错误；证据抽取阶段会自动使用规则式抽取。这样已有来源仍然可以继续生成证据和报告。

### 为什么报告没有结论？

只有成功保存证据的子问题才会创建 Claim。请检查搜索是否返回来源、来源是否有摘要或正文，以及证据抽取结果是否为空。

### 如何切换到离线演示？

在 `.env` 中设置：

```dotenv
RESEARCHGRAPH_SEARCH_PROVIDER=demo
OPENAI_API_KEY=
```

这样搜索使用确定性的 Demo 数据，问题拆解和证据抽取也会使用规则式实现。

## 项目结构

```text
ResearchGraphAgent/
├── agent/          # 研究流程和 Agent 服务
├── models/         # 领域数据模型
├── tools/          # LLM、搜索、存储和引用工具
├── web/            # JSON API 和网页界面
├── tests/          # 自动化测试
├── data/           # SQLite 数据目录
├── app.py          # 启动入口
├── config.py       # 环境配置
└── DEVELOPMENT.md  # 开发说明
```

## 当前边界

这是一个可运行的 MVP，适合演示研究流程和验证可追溯设计。它还没有实现用户登录、异步任务队列、来源质量评分、复杂冲突分析和生产环境部署配置。真实研究使用时，应继续核查来源原文和模型生成结果。
