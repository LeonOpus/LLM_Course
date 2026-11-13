"""
Deep Research Agent 数据 Schema V2
================================

核心改进：
1. 多步轨迹：search → tool_response → visit → tool_response → finish
2. 强制引用规范：答案中的 [1][2] 必须对应 tool_response
3. 行业标签：金融/餐饮/创业/智慧交通
4. 完整 metadata：industry, question_type, num_steps, total_tokens
"""

from datetime import datetime

# =============================================================================
# 行业和问题类型定义
# =============================================================================

INDUSTRIES = {
    "finance": "金融",
    "catering": "餐饮",
    "startup": "创业",
    "smart_transport": "智慧交通"
}

QUESTION_TYPES = {
    "policy": "政策法规",      # 最新政策、法规变化
    "market": "市场分析",      # 市场规模、趋势、机会
    "competitor": "竞争情报",  # 竞争对手分析
    "calculation": "数据计算", # 财务计算、指标分析
    "risk": "风险评估",        # 风险识别和评估
    "expansion": "扩张建议",   # 业务拓展建议
}

# =============================================================================
# System Prompt 定义
# =============================================================================

def get_system_prompt_v2() -> str:
    """获取 V2 版本的系统提示词"""
    current_date = datetime.now().strftime("%Y年%m月%d日")

    return f'''你是"拓业智询"——一个专业的企业咨询助手，服务于银行的对公客户（中小企业）。你的职责是帮助企业主解决在金融、餐饮、创业、智慧交通等行业中遇到的业务问题。

## 当前时间
{current_date}

## 可用工具

1. **search**(query: str) -> str
   搜索互联网，返回相关网页的标题、摘要和URL列表。
   - 用于：获取初步信息、发现相关来源
   - 返回：多条搜索结果，每条包含标题、摘要、URL

2. **visit**(url: str) -> str
   访问指定网页，获取详细内容。
   - 用于：当搜索摘要信息不足时，深入阅读原文
   - 返回：网页的主要文本内容

3. **calculator**(expression: str) -> str
   执行数学计算。
   - 用于：财务计算、数据分析、指标换算
   - 支持：四则运算、百分比、幂运算

4. **finish**(answer: str, references: list) -> None
   输出最终答案，结束研究。
   - answer: 完整的回答内容，必须包含引用标注 [1][2] 等
   - references: 引用来源列表，格式为 ["[1] 来源名称: 关键信息", "[2] ..."]

## 工作流程

### 简单问题（常识/定义类）
如果问题可以基于通用知识直接回答，无需搜索，直接用 finish 输出答案。

### 复杂问题（需要查证）
1. **搜索信息**：使用 search 获取相关结果
2. **必要时深入**：如果搜索摘要不足，使用 visit 阅读 1 个关键网页
3. **整合答案**：综合信息，用 finish 输出带引用的答案

## 效率要求（重要！）

- **最多调用 3 次工具**（不含 finish），然后必须用 finish 输出答案
- 搜索结果的摘要通常足够回答问题，不要过度搜索
- 典型流程：search → finish 或 search → visit → finish
- 禁止反复搜索同一主题，禁止访问超过 2 个网页

## 输出格式

每次输出必须包含两部分：

**思考部分**：
<think>
- 当前进展：已知什么，还需要什么
- 下一步计划：打算采取什么行动
- [如果搜索结果不理想] 反思并调整策略
</think>

**行动部分**：
<tool_call>
{{"name": "工具名", "arguments": {{"参数": "值"}}}}
</tool_call>

## 引用规范（重要！）

1. 答案中的每个事实性陈述必须标注引用，如 [1]、[2]
2. 引用编号必须对应你实际查阅的来源
3. finish 的 references 参数必须列出所有引用来源
4. 禁止编造不存在的引用

## 示例

用户: 餐饮行业最近有什么扶持政策？

<think>
这是一个政策查询问题，需要搜索最新的餐饮行业扶持政策。
下一步：使用 search 查询相关政策信息。
</think>
<tool_call>
{{"name": "search", "arguments": {{"query": "2025年餐饮行业扶持政策"}}}}
</tool_call>

[工具返回]
[1] 商务部：2025年餐饮业纾困扶持政策
摘要：商务部发布餐饮业纾困措施，包括减税降费、租金减免...
URL: https://example.com/policy1

[2] 各地餐饮消费券发放计划
摘要：多地推出餐饮消费券，刺激餐饮消费复苏...
URL: https://example.com/policy2

<think>
搜索到了相关政策信息，摘要已经足够回答问题。
主要政策包括：商务部的纾困措施、各地消费券计划。
可以整合回答了。
</think>
<tool_call>
{{"name": "finish", "arguments": {{"answer": "根据最新信息，餐饮行业目前有以下主要扶持政策：\\n\\n1. **商务部纾困措施** [1]：包括减税降费、租金减免等措施，帮助餐饮企业渡过难关。\\n\\n2. **地方消费券计划** [2]：多个城市推出餐饮消费券，通过补贴刺激消费，帮助餐饮企业恢复客流。\\n\\n建议您关注当地商务局的具体实施细则，及时申请相关补贴。", "references": ["[1] 商务部: 2025年餐饮业纾困扶持政策", "[2] 各地政府: 餐饮消费券发放计划"]}}}}
</tool_call>'''


# =============================================================================
# 数据 Schema 定义
# =============================================================================

"""
完整的数据格式示例：

{
    "messages": [
        {
            "role": "system",
            "content": "<system_prompt>"
        },
        {
            "role": "user",
            "content": "餐饮行业最近有什么扶持政策？"
        },
        {
            "role": "assistant",
            "content": "<think>\\n这是一个政策查询问题...\\n</think>\\n<tool_call>\\n{\"name\": \"search\", ...}\\n</tool_call>"
        },
        {
            "role": "tool_response",
            "name": "search",
            "content": "[1] 商务部：2025年餐饮业纾困扶持政策\\n摘要：...\\nURL: ...\\n\\n[2] 各地餐饮消费券发放计划\\n摘要：..."
        },
        {
            "role": "assistant",
            "content": "<think>\\n搜索到了相关政策信息...\\n</think>\\n<tool_call>\\n{\"name\": \"finish\", ...}\\n</tool_call>"
        }
    ],
    "metadata": {
        "id": "finance_policy_001",
        "industry": "catering",
        "industry_zh": "餐饮",
        "question_type": "policy",
        "question_type_zh": "政策法规",
        "num_steps": 2,
        "tools_used": ["search", "finish"],
        "has_citation": true,
        "total_tokens": 1256,
        "created_at": "2025-01-18"
    }
}
"""

# =============================================================================
# 数据验证函数
# =============================================================================

import re
import json
from typing import Dict, List, Tuple, Optional


def validate_trajectory(data: Dict) -> Tuple[bool, List[str]]:
    """
    验证轨迹数据的完整性和正确性

    返回: (is_valid, error_messages)
    """
    errors = []

    messages = data.get("messages", [])
    metadata = data.get("metadata", {})

    # 1. 检查基本结构
    if len(messages) < 3:
        errors.append("消息数量不足，至少需要 system + user + assistant")

    # 2. 检查角色顺序
    if messages and messages[0].get("role") != "system":
        errors.append("第一条消息必须是 system")

    if len(messages) > 1 and messages[1].get("role") != "user":
        errors.append("第二条消息必须是 user")

    # 3. 检查最后一条 assistant 消息是否包含 finish
    assistant_messages = [m for m in messages if m.get("role") == "assistant"]
    if assistant_messages:
        last_assistant = assistant_messages[-1].get("content", "")
        # 支持 JSON 和 XML 两种格式
        has_finish = (
            '"name": "finish"' in last_assistant or
            '"name":"finish"' in last_assistant or
            '<name>finish</name>' in last_assistant
        )
        if not has_finish:
            errors.append("最后一条 assistant 消息必须调用 finish 工具")

    # 4. 检查 tool_response 后是否有 assistant 响应
    for i, msg in enumerate(messages[:-1]):
        if msg.get("role") == "tool_response":
            if i + 1 < len(messages) and messages[i + 1].get("role") != "assistant":
                errors.append(f"tool_response (位置 {i}) 后必须是 assistant 响应")

    # 5. 检查引用格式
    if assistant_messages:
        last_content = assistant_messages[-1].get("content", "")
        # 提取 finish 的 answer
        finish_match = re.search(r'"answer"\s*:\s*"([^"]*(?:\\"[^"]*)*)"', last_content)
        if finish_match:
            answer = finish_match.group(1)
            citations = re.findall(r'\[(\d+)\]', answer)
            if not citations:
                errors.append("答案中缺少引用标注 [1][2] 等")

    # 6. 检查 metadata
    required_fields = ["industry", "question_type", "num_steps"]
    for field in required_fields:
        if field not in metadata:
            errors.append(f"metadata 缺少必要字段: {field}")

    if metadata.get("industry") not in INDUSTRIES:
        errors.append(f"无效的行业: {metadata.get('industry')}")

    if metadata.get("question_type") not in QUESTION_TYPES:
        errors.append(f"无效的问题类型: {metadata.get('question_type')}")

    return len(errors) == 0, errors


def extract_tool_calls(content: str) -> List[Dict]:
    """从 assistant 内容中提取工具调用"""
    calls = []
    pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
    matches = re.findall(pattern, content, re.DOTALL)
    for match in matches:
        try:
            calls.append(json.loads(match))
        except json.JSONDecodeError:
            pass
    return calls


def count_steps(messages: List[Dict]) -> int:
    """计算轨迹的步数（assistant 消息数量）"""
    return len([m for m in messages if m.get("role") == "assistant"])


def get_tools_used(messages: List[Dict]) -> List[str]:
    """获取使用的工具列表"""
    tools = []
    for msg in messages:
        if msg.get("role") == "assistant":
            calls = extract_tool_calls(msg.get("content", ""))
            for call in calls:
                tool_name = call.get("name")
                if tool_name and tool_name not in tools:
                    tools.append(tool_name)
    return tools


# =============================================================================
# 数据模板
# =============================================================================

def create_trajectory_template(
    question: str,
    industry: str,
    question_type: str,
    steps: List[Dict]  # [{"think": "...", "tool": "search", "args": {...}}, ...]
) -> Dict:
    """
    创建轨迹数据模板

    steps 格式:
    [
        {"think": "思考内容", "tool": "search", "args": {"query": "..."}},
        {"tool_response": "搜索结果..."},
        {"think": "思考内容", "tool": "finish", "args": {"answer": "...", "references": [...]}},
    ]
    """
    messages = [
        {"role": "system", "content": get_system_prompt_v2()},
        {"role": "user", "content": question}
    ]

    tools_used = []

    for step in steps:
        if "think" in step and "tool" in step:
            # Assistant 消息
            tool_call = json.dumps(
                {"name": step["tool"], "arguments": step["args"]},
                ensure_ascii=False,
                indent=2
            )
            content = f'''<think>
{step["think"]}
</think>

<tool_call>
{tool_call}
</tool_call>'''
            messages.append({"role": "assistant", "content": content})

            if step["tool"] not in tools_used:
                tools_used.append(step["tool"])

        elif "tool_response" in step:
            # Tool response 消息
            messages.append({
                "role": "tool_response",
                "content": step["tool_response"]
            })

    num_steps = count_steps(messages)

    return {
        "messages": messages,
        "metadata": {
            "industry": industry,
            "industry_zh": INDUSTRIES.get(industry, ""),
            "question_type": question_type,
            "question_type_zh": QUESTION_TYPES.get(question_type, ""),
            "num_steps": num_steps,
            "tools_used": tools_used,
            "has_citation": True,
            "total_tokens": 0,  # 后续计算
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
    }


# =============================================================================
# 示例数据
# =============================================================================

EXAMPLE_TRAJECTORY = create_trajectory_template(
    question="餐饮行业最近有什么扶持政策？我在成都开了一家火锅店。",
    industry="catering",
    question_type="policy",
    steps=[
        {
            "think": "用户询问餐饮行业扶持政策，并且在成都开火锅店。需要搜索：\n1. 全国性的餐饮扶持政策\n2. 成都本地的餐饮优惠政策\n先搜索全国政策。",
            "tool": "search",
            "args": {"query": "2025年餐饮行业扶持政策 减税 补贴"}
        },
        {
            "tool_response": """[1] 商务部：2025年餐饮业纾困扶持措施
来源: 商务部官网 | 日期: 2025-01-10
摘要: 商务部联合财政部发布餐饮业纾困措施，主要包括：1）增值税减免，小规模纳税人增值税征收率降至1%；2）房租减免，国有物业减免3个月租金；3）社保缓缴政策延续至2025年底。
URL: https://www.mofcom.gov.cn/policy/2025/catering

[2] 成都市餐饮消费券发放通知
来源: 成都市商务局 | 日期: 2025-01-15
摘要: 成都市将于春节期间发放5000万元餐饮消费券，单笔消费满100元可使用20元消费券，每人每周限领2张。火锅、川菜等特色餐饮可叠加使用。
URL: https://cd.gov.cn/notice/2025/coupon"""
        },
        {
            "think": "搜索到了全国政策和成都本地政策，信息充足：\n- [1] 商务部的减税、租金减免、社保缓缴政策\n- [2] 成都的餐饮消费券，特别提到火锅可叠加使用\n可以整合回答了。",
            "tool": "finish",
            "args": {
                "answer": """根据最新政策，作为成都的火锅店经营者，您可以关注以下扶持政策：

**一、全国性政策** [1]
商务部联合财政部发布的餐饮业纾困措施：
- **增值税减免**：小规模纳税人增值税征收率降至1%
- **房租减免**：如果您租用国有物业，可减免3个月租金
- **社保缓缴**：政策延续至2025年底，缓解现金流压力

**二、成都本地政策** [2]
成都市商务局的消费券计划：
- 春节期间发放5000万元餐饮消费券
- 满100元可用20元券，每人每周限领2张
- **火锅、川菜可叠加使用**，对您特别有利

**建议**：
1. 尽快向税务局确认增值税优惠资格
2. 联系物业确认是否为国有资产，申请租金减免
3. 在店内张贴消费券使用提示，吸引顾客""",
                "references": [
                    "[1] 商务部: 2025年餐饮业纾困扶持措施 (2025-01-10)",
                    "[2] 成都市商务局: 餐饮消费券发放通知 (2025-01-15)"
                ]
            }
        }
    ]
)


if __name__ == "__main__":
    # 验证示例数据
    is_valid, errors = validate_trajectory(EXAMPLE_TRAJECTORY)

    print("=" * 60)
    print("Schema V2 示例数据验证")
    print("=" * 60)

    if is_valid:
        print("✓ 数据格式验证通过")
    else:
        print("✗ 数据格式验证失败:")
        for err in errors:
            print(f"  - {err}")

    print(f"\n消息数量: {len(EXAMPLE_TRAJECTORY['messages'])}")
    print(f"步数: {EXAMPLE_TRAJECTORY['metadata']['num_steps']}")
    print(f"使用工具: {EXAMPLE_TRAJECTORY['metadata']['tools_used']}")
    print(f"行业: {EXAMPLE_TRAJECTORY['metadata']['industry_zh']}")
    print(f"问题类型: {EXAMPLE_TRAJECTORY['metadata']['question_type_zh']}")

    print("\n" + "=" * 60)
    print("消息结构预览:")
    print("=" * 60)
    for i, msg in enumerate(EXAMPLE_TRAJECTORY['messages']):
        role = msg['role']
        content = msg['content'][:80] + "..." if len(msg['content']) > 80 else msg['content']
        print(f"{i+1}. [{role}] {content}")
