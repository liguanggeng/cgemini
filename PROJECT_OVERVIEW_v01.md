# 项目说明 v0.1

## 概述
本项目围绕 Google Gemini Function Call 能力，构建多代理协作的函数资产管理流程。系统核心是顶层调度器（Top-Level Orchestrator），按 Agent1/2/3 的职责闭环完成“需求澄清 → 函数设计 → 审核沉淀”，并将知识更新持久化至本地 JSONL 文件，便于积累可复用的函数与经验。

## 主要组件
- **TopLevelOrchestrator** (`src/orchestrator/top_level.py`)
  - 管理任务状态 (`TaskContext`) 与历史记录。
  - 串行驱动 Agent1(需求整理)、Agent2(函数工程)、Agent3(审核)的协作，实现从“需求澄清”到“函数声明”再到“代码实现”的完整闭环。
  - 提供 `_safe_drive` 保障异常容错，`KnowledgeUpdate` 结构化落地。

- **Support Components** (`src/orchestrator/support.py`)
  - `InMemoryTaskRegistry`：教学版任务注册与状态跟踪。
  - `InMemoryKnowledgeService`：加载知识快照，支持写入本地存储。
  - `SimpleFeedbackRouter`：根据 Agent3 决策回退/完成任务。
  - `build_default_gateway`：提供教学版 handler（纯 Python）。

- **GeminiAgentGateway** (`src/orchestrator/gemini_gateway.py`)
  - 调用 `google-genai` 客户端执行真实模型推理。
  - 支持 `GEMINI_MODEL`/`GOOGLE_GENAI_MODEL`/`DEFAULT_MODEL` 环境变量覆盖默认模型。
  - 针对 Agent1/2/3 构造定制 Prompt，并支持 Agent2 的“声明”与“实现”两种模式。

- **KnowledgeStore** (`src/orchestrator/knowledge_store.py`)
  - 以 JSONL 形式持久化 `KnowledgeUpdate`。
  - 默认输出目录：`data/knowledge_updates.jsonl`。

## 运行方式
1. 建议使用仓库根目录下的虚拟环境 `.venv/`。
2. `.env` 示例：
   ```
   GOOGLE_API_KEY=your-key
   GEMINI_MODEL=gemini-2.5-pro
   ```
3. 执行教学闭环：
   ```ps1
   .\.venv\Scripts\python examples\demo_run.py
   ```
4. 调用真实 Gemini：
   ```ps1
   .\.venv\Scripts\python examples\demo_run.py --use-gemini
   ```
   或设置 `USE_GEMINI=1`。

## 当前进度
- **文档**：`docs/agent1_design.md`、`docs/support_components.md`、`docs/top_level_orchestrator.md`。
- **代码**：
  - 调度器已实现“需求 -> 声明 -> 审核 -> 实现”的完整流程。
  - Agent2 具备了根据审核反馈修正函数声明，并最终生成 Python 实现代码的能力。
- **测试**：项目已引入 `pytest` 框架，并为核心的 Orchestrator、KnowledgeStore 及 Support 组件编写了单元和集成测试。
- **提交**：`Add orchestrator scaffolding with Gemini gateway and persistence`。

## 待办
- 解决 `git push origin master` SSH 连接问题。
- 根据需要扩展知识存储（数据库/云端）与自动化测试。
- 清理未入库文件（如 `testeragents.py`），确认用途后纳入或忽略。

