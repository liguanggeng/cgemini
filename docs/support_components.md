# 顶层调度配套组件讲义



> 老师寄语：今天我们补齐上节所需的“助手班底”。这些内存实现可让我们在本地沙箱里演练

> Agent1/2/3 的协作流程，帮助大家更好地理解 orchestrator 的工作节奏。



## 学习目标

- 认识调度层需要的四个基础协作者：TaskRegistry、KnowledgeService、AgentGateway、FeedbackRouter。

- 手把手实现一套内存版本，便于快速实验与单元测试。

- 了解如何用简单的 Prompt 模板驱动 Agent1 的回复。



## 组件概览

| 组件 | 教学版职责 | 关键方法 |

|------|------------|----------|

| InMemoryTaskRegistry | 管理任务 ID 与状态，便于回溯 | `register`、`update_state`、`get` |

| InMemoryKnowledgeService | 提供函数索引、经验卡、检查单的快照 | `load_snapshot`、`commit_updates` |

| SimpleAgentGateway | 统一调用代理；教学版直接调用 Python 函数或伪模型 | `invoke` |

| SimpleFeedbackRouter | 根据 Agent3 审核结果调整任务状态或返回修订意见 | `route` |



## 推荐数据流

1. Orchestrator 注册任务后，立即向知识服务索要 snapshot。

2. Agent1 被调用时，Prompt 中注入 `knowledge_refs`，返回任务说明与 lessons。

3. Agent2 在教学版中暂时返回伪函数描述（下一节完善）。

4. Agent3 给出审核结果，反馈路由器根据 `decision` 字段决定是否循环或结束。



## Prompt 演示：Agent1 教学模板

```text

任务目标：{user_request}

可复用函数：{function_index}

经验提醒：{lessons}



请输出：

- objective: ...

- requirements: ...

- constraints: ...

- tooling: ...

- lessons: ...

```

> 课堂作业：尝试为 Agent1 设计一组默认问题（如“是否有术语表？”），写入模板，观察生成效果。



## 反馈路由示例逻辑

- 无论结果如何，统一通过 `context.set_artifact('agent3_feedback', review_payload)` 留存审核原始信息。

- 若 Agent3 `decision == "approve"` → 调用 `context.mark_state(TaskState.DONE)` 收尽。

- 若 `decision == "revise"` → 把状态回退至 `building`，便 Agent2 重做修订。

- 若 `decision == "reject"` → 直接标记 `failed`，等待人工介入或回到 Agent1。



## Gemini ????
- `GeminiAgentGateway`?`src/orchestrator/gemini_gateway.py`??? Google Gemini ???? Agent1/2/3 ??????????? JSON?
- ????? `GEMINI_MODEL`?`GOOGLE_GENAI_MODEL` ? `DEFAULT_MODEL` ??????????? `gemini-2.0-flash-001`?
- ?????? `google-genai` ??? `GOOGLE_API_KEY`?? Vertex ?????????? `gemini_usage_guide.md`?
- `examples/demo_run.py` ?? `--use-gemini` ? `USE_GEMINI=1` ???????????????????????
- `InMemoryKnowledgeService` ???????? `data/knowledge_updates.jsonl`????????
