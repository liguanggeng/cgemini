# 顶层调度层设计讲义

> 老师寄语：本节课我们学习如何搭建整套多代理系统的“指挥塔”——顶层调度层（Top-Level Orchestrator）。请先通读讲义，再跟着示例实现骨架代码。

## 学习目标

- 认清顶层调度层的角色：负责驱动 Agent1/Agent2/Agent3 的协作循环。

- 掌握任务生命周期：任务接收 → 任务澄清 → 函数方案生成 → 审核与沉淀。

- 熟悉调度层需要依赖的核心能力：知识库访问、日志记录、版本化经验管理。

## 系统角色回顾

- **Agent1 (需求编排者)**：整理用户任务，输出结构化任务包。

- **Agent2 (函数工程师)**：检索或实现工具函数，并产出标准化描述。

- **Agent3 (资产管控者)**：审核函数质量，维护工具资产台账。

- **顶层调度层**：协调上述三位的轮转节奏和信息传递，确保闭环。

## 顶层调度层职责拆解

1. **任务入口管理**：接收新任务请求，为任务分配唯一 ID，并初始化上下文。

2. **知识注入与回顾**：查询函数索引、经验卡、审核 checklist 等知识源，向 Agent1 提供任务前情。

3. **阶段驱动**：依次触发 Agent1 → Agent2 → Agent3，每一步都要带着输入产出模板。

4. **反馈闭环**：根据 Agent3 审核结果决定任务是否完成，或回退到 Agent2/Agent1 修正。

5. **沉淀经验**：汇总任务中新增的经验、函数台账变更，写入知识库供下轮使用。

## 核心数据结构（建议）

```text

TaskContext

  - task_id: str

  - user_request: str

  - task_state: Enum['pending', 'clarifying', 'building', 'reviewing', 'done', 'failed']

  - history: list[ConversationTurn]

  - artifacts: dict[str, Any]            # 函数描述、验证结果等

  - knowledge_refs: KnowledgeSnapshot    # 本轮引用到的知识材料

KnowledgeSnapshot

  - function_index: list[FunctionSummary]

  - lessons: list[LessonCard]

  - audit_checklists: list[Checklist]

```

## 调度流程示意

```text

receive_task() ──▶ initialize_context()

      │

      ▼

run_agent1(context) ──▶ context.artifacts['task_brief']

      │

      ▼

run_agent2(context) ──▶ context.artifacts['function_spec']

      │

      ▼

run_agent3(context) ──▶ 审核结果 approve/revise/reject

      │

      ├── approve ──▶ finalize_task()

      ├── revise  ──▶ 回退到 run_agent2()

      └── reject  ──▶ 标记 failed，回退给 Agent1/人工介入

```

## 调度安全增强（教学版补充）
- ?? `KnowledgeUpdate` ??????????? `knowledge_updates` ???????????????

- 引入 `TaskContext.add_history()`、`set_artifact()`、`append_knowledge_updates()` 等方法，统一管理历史、产物与知识沉淀，避免随意改动内部字典。

- `handle_new_task` 借助 `_safe_drive` 对 Agent1/2/3 及反馈路由逐步包装，发生异常时会记录 `last_error`、写入历史并立即更新任务状态。

- 默认 `max_cycles=5` 限制多轮回退，配合统一的 `agent3_review` / `agent3_feedback` 产物，方便调试与人工介入。

## 顶层需要的模块

| 模块 | 职责 | 示例方法 |

|------|------|----------|

| TaskRegistry | 持久化任务元信息 | `register(task_context)` / `update_state(task_id, state)` |

| KnowledgeService | 拉取/写回知识卡与函数索引 | `load_snapshot()` / `commit_updates(updates)` |

| AgentGateway | 统一代理调用入口（可换模型/Prompt） | `invoke(agent_name, payload)` |

| FeedbackRouter | 依据审核反馈决定下一步 | `route(result, context)` |

> 注：此处只列出顶层需要交互的模块，具体实现可以后续迭代补齐。

## 教学用伪代码

```python

class TopLevelOrchestrator:

    def __init__(self, task_registry, knowledge_service, agent_gateway, feedback_router):

        self.task_registry = task_registry

        self.knowledge_service = knowledge_service

        self.agent_gateway = agent_gateway

        self.feedback_router = feedback_router

    def handle_new_task(self, user_request: str) -> TaskContext:

        ctx = self._bootstrap_context(user_request)

        self._drive_agent1(ctx)

        while ctx.task_state not in (TaskState.DONE, TaskState.FAILED):

            self._drive_agent2(ctx)

            review = self._drive_agent3(ctx)

            self.feedback_router.route(review, ctx)

        self._finalize(ctx)

        return ctx

```

## 课堂练习

1. 画出你心目中 Agent1/2/3 之间的数据交换图，并标出关键字段。

2. 想一想：如果 Agent3 要求补充测试案例，调度层应该怎么更新上下文，让 Agent2 知道哪些点需要修复？

3. 设计一个最小化的 `KnowledgeSnapshot`：哪些信息是 Agent1 在澄清用户需求时最常用的？

## 作业指引

- 基于本讲义，编写顶层调度层的骨架类（可放在 `src/orchestrator/top_level.py`）。

- 构造接口时，可使用伪实现或 TODO 标记，等到后续课程再落地细节模块。

- 维持清晰注释，便于日后扩展。

下一节课我们会深入 Agent1 的提示构建与知识注入策略。继续加油！

