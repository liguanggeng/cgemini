# Agent1 设计讲义：需求编排者

> 老师寄语：Agent1 是整套系统的“班长”，负责把用户模糊的需求整理成可以交接的任务说明。本节课我们把它的职责、输入输出格式和提示模板梳理清楚，再用轻量代码实现教学版逻辑。

## 学习目标
- 明确 Agent1 的责任边界：只整理需求，不直接写函数实现。
- 掌握结构化输出格式，保证信息完整可传递。
- 学会将知识卡、函数索引等上下文注入 Prompt，形成“复用 + 缺口”双视角。

## 职责速览
- **信息收集**：识别需求中的目标、约束、潜在变量，必要时补问。
- **知识引用**：快速浏览函数索引与经验卡，指出可复用的资产与注意事项。
- **结构化交付**：输出模板包含 `objective / requirements / constraints / tooling / lessons / open_questions` 等字段。
- **经验沉淀**：根据任务结果更新 lessons，以便后续 Agent1/2 使用。

## 输入与输出
- **输入**
  - `user_request`：原始用户需求文本。
  - `knowledge.function_index`：现有函数概要，用于判断复用。
  - `knowledge.lessons`：历史经验卡，提醒常见坑。
  - `knowledge.audit_checklists`：Agent3 的审核重点，可在需求说明中提前提示。
- **输出**（推荐字段）
  ```json
  {
    "objective": "用户核心目的",
    "requirements": ["必须满足的业务要点"],
    "constraints": ["外部限制：语言、性能、接口协议..."],
    "tooling": {
      "reuse": ["可复用函数"],
      "gaps": ["需要新增的函数能力"],
      "notes": "调用提示、参数提醒"
    },
    "open_questions": ["需向用户确认的问题"],
    "lessons_applied": ["用到了哪些经验卡"],
    "lessons_to_add": ["本轮新发现，可供沉淀"]
  }
  ```

## Prompt 思路
1. **上下文注入**：将函数索引做成表格/列表，让模型一眼看到已有资源；lessons 以 bullet 呈现。
2. **任务拆解**：引导模型先判断任务分类（翻译/数据清洗/分析等），再列出具体子任务。
3. **复用 vs 缺口**：要求模型分别列出可复用函数和缺失能力，避免混在一起。
4. **检核提醒**：将审核 checklist 中的高频项融入输出（如“记得规划验证用例”）。

### 示例 Prompt 片段
```text
[系统角色]
你是需求编排专家，只负责梳理用户目标并生成给 Agent2 的任务说明，不直接写代码。

[参考函数]
- translate_and_spellcheck: 翻译并检查拼写
- summarize_product_features: 提炼产品卖点...

[经验卡]
- 翻译任务需确认术语表
- 若目标输出要被调用，请标注接口格式

[输出格式]
请返回 JSON，字段包含 objective、requirements、constraints、tooling、open_questions、lessons_applied、lessons_to_add。
```

> 课堂练习：尝试添加“疑问模板”，例如鼓励模型在 open_questions 中使用“若...请提供...”的句式，提升与用户的互动质量。

## 教学版实现策略
- 使用一个简单的 Python 函数 `generate_task_brief(payload)`，读取输入字典并返回上述 JSON。
- 默认逻辑可以：
  1. 直接将 `user_request` 作为 objective。
  2. 从 lessons 中提取标题放入 `lessons_applied`。
  3. 假设缺少术语表，将其写入 open_questions。
  4. 将所有函数名列入 `tooling.reuse`，作为示例。
- 后续可替换为真实 LLM 调用或更复杂规则。

## 与 Orchestrator 的接口
- `AgentGateway` 中为 `"agent1"` 注册处理函数（如 `agent1_handler`）。
- Orchestrator 调用时传入字段：
  ```python
  payload = {
      "user_request": context.user_request,
      "knowledge": context.knowledge_refs,
      "history": context.history,
  }
  ```
- Agent1 函数返回的 dict 直接写入 `context.artifacts["task_brief"]`。

## 拓展思路
- **提问策略库**：维护常见领域的“必问问题”列表，根据函数标签自动选择。
- **任务档案**：为重复出现的需求类别建立模板，如“翻译 + 校对”场景直接引用标准模板。
- **自评机制**：令 Agent1 对输出自查（比如 checklist），提升稳定性。

下一讲我们会把这个教学版函数落地，并演示如何让 Agent2 消化这些结构化信息。加油！
