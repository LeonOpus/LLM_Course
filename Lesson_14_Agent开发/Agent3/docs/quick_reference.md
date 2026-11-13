# LangGraph Agent 快速参考

## 核心文件

```
agents/
├── nodes.py     # 所有节点定义（最重要！）
└── graph.py     # 图构建逻辑

tools/
├── text2sql.py       # 数据库查询
├── code_executor.py  # 代码执行
├── pdf_parser.py     # PDF解析
├── web_search.py     # 网络搜索
└── rag_search.py     # RAG检索
```

## 状态字段速查

| 字段 | 类型 | 说明 |
|------|------|------|
| `query` | str | 用户问题 |
| `intent` | str | 意图类型 |
| `plan` | List[dict] | 执行计划 |
| `current_step` | int | 当前步骤索引 |
| `tool_results` | List[dict] | 工具执行结果 |
| `should_continue` | bool | 是否继续执行 |
| `final_answer` | str | 最终回答 |

## 节点职责速查

| 节点 | 输入 | 输出 | 职责 |
|------|------|------|------|
| RouterNode | query | intent | 意图分类 |
| PlannerNode | query, intent | plan | 制定计划 |
| ExecutorNode | plan, current_step | tool_results | 执行工具 |
| ReflectorNode | tool_results | should_continue | 质量评估 |
| CriticNode | tool_results | final_answer | 生成答案 |

## 常用代码模式

### 1. 定义节点
```python
class MyNode:
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        # 读取状态
        query = state["query"]

        # 处理逻辑
        result = do_something(query)

        # 返回更新
        return {"my_field": result}
```

### 2. 条件路由
```python
def decide_next(state):
    if state["should_continue"]:
        return "executor"
    return "critic"

graph.add_conditional_edges("reflector", decide_next)
```

### 3. 工具调用
```python
tool = self.tools[tool_name]
result = tool.run(**params)
tool_results.append({
    "tool": tool_name,
    "result": result
})
```

## 调试命令

```bash
# 测试集成（无需LLM）
python test_integration.py

# 测试完整流程
python test_code_executor.py

# 启动服务
python main.py

# 查看数据库
python view_db.py
```

## 意图类型

| 意图 | 触发词 | 处理流程 |
|------|--------|----------|
| data_query | 查询、多少、哪些 | Router→Planner→Executor→Critic |
| analysis | 分析、对比、趋势 | Router→Planner→Executor→Reflector→Critic |
| research | 研报、报告、观点 | Router→Planner→Executor→Critic |
| general | 什么是、解释 | Router→Critic |

## 工具返回格式

### text2sql
```python
{
    "success": True,
    "sql": "SELECT ...",
    "raw_data": [...],  # 原始数据
    "answer": "..."     # 自然语言回答
}
```

### code_executor
```python
{
    "success": True,
    "output": "print输出",
    "figures": [{"base64": "..."}],  # 图表
    "error": ""
}
```

## 图表自动捕获

```python
# 代码中创建图表（不要调用savefig）
plt.figure(figsize=(10, 6))
plt.bar(x, y)
plt.title("标题")

# code_executor 自动捕获
# 结果在 result["figures"] 中
```

## 数据传递

```python
# 步骤1: text2sql 获取数据
result1 = text2sql.run("查询银行股")
# result1["raw_data"] = [{"code": "601398", ...}, ...]

# 步骤2: code_executor 使用数据
result2 = code_executor.run(code, data=result1["raw_data"])
# 代码中用 data 变量访问数据
```

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `KeyError: 'data'` | 数据未传递 | 检查 `use_previous_data` |
| `NameError: 'plt'` | 未预导入 | 不要写 `import matplotlib` |
| `__import__ error` | 调用了 savefig | 不要调用 `plt.savefig()` |
