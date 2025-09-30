# Next Session Checklist

## 状态概览
- 本地虚拟环境在 `.venv/`，已安装 `google-genai`。
- `.env` 中保存 `GOOGLE_API_KEY` 与 `GEMINI_MODEL`，示例脚本会自动加载。
- 知识沉淀默认写入 `data/knowledge_updates.jsonl`，由 `KnowledgeStore` 维护。
- 代码已提交：`Add orchestrator scaffolding with Gemini gateway and persistence`。
- 推送到 `git@github.com:liguanggeng/atest.git` 因 SSH 连接被拒失败，需重新尝试。

## 快速启动
```ps1
# 激活虚拟环境并运行教学示例
.\.venv\Scripts\python examples\demo_run.py

# 调用 Gemini 实例
.\.venv\Scripts\python examples\demo_run.py --use-gemini
```

## 待处理
1. **实现 Worker 执行循环**：构建一个独立的流程，使其能够利用知识库中已批准的函数（包括声明和代码），去解决用户的实际问题。这需要：
   - 设计一个面向用户的 Agent，用于理解用户问题并匹配合适的工具。
   - 实现调用 Gemini API 并处理 `FunctionCall` 返回的逻辑。
   - 加载并执行由 Agent2 生成的 Python 代码。

2. **设计并实现“工匠自省回路”**：当 Worker 在执行函数中遇到失败时，能够捕获错误，并触发一个新的“修复任务”，将包含错误信息的“Bug报告”交由 Agent2 和 Agent3 进行分析、修复和再次审核。

3. **函数代码的持久化**：目前生成的函数代码仅存在于内存产物中。需要设计一种方案，将已批准的函数实现代码（.py 文件）与函数声明（JSON）一起，结构化地保存到文件系统中。

4. **解决 Git 推送问题**：确认 SSH key 或网络策略，然后执行 `git push origin master`。

5. **清理与重构**：审查 `testeragents.py`（未纳入版本控制），确认是否保留或忽略。根据需要，将 `InMemory` 组件替换为更持久化的实现。

## 参考文件
- `docs/support_components.md`：Gemini 网关与知识存储说明。
- `docs/top_level_orchestrator.md`：顶层调度责任与 `KnowledgeUpdate` 结构。
- `src/orchestrator/gemini_gateway.py`：模型覆写环境变量及 JSON 序列化处理。
- `src/orchestrator/support.py`：知识服务接入本地存储的实现。
