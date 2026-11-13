"""工具定义模块 - 定义Deep Research Agent可用的5个工具"""

TOOLS = {
    "search": {
        "name": "search",
        "description": "搜索互联网获取信息。返回搜索结果的标题、摘要和URL。用于获取初步信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，要精准包含关键实体"
                }
            },
            "required": ["query"]
        }
    },
    "visit": {
        "name": "visit",
        "description": "访问指定URL，提取网页详细内容。当搜索摘要信息不足或需要验证时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要访问的网页URL"
                },
                "goal": {
                    "type": "string",
                    "description": "访问目的，用于指导信息提取，如'获取公司成立时间'"
                }
            },
            "required": ["url", "goal"]
        }
    },
    "calculator": {
        "name": "calculator",
        "description": "执行数学计算。支持四则运算、百分比、单位换算等。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '100 * 1.05' 或 '(2024 - 1955)'"
                }
            },
            "required": ["expression"]
        }
    },
    "scholar": {
        "name": "scholar",
        "description": "搜索学术文献。用于需要权威学术来源的问题，如科学发现、研究数据等。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "学术搜索关键词"
                }
            },
            "required": ["query"]
        }
    },
    "finish": {
        "name": "finish",
        "description": "结束研究并输出最终答案。必须在收集到足够信息后调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "最终答案，要准确、完整"
                },
                "evidence": {
                    "type": "string",
                    "description": "支持答案的证据，格式：[来源1] 关键信息... [来源2] 关键信息..."
                }
            },
            "required": ["answer", "evidence"]
        }
    }
}


def get_tools_description() -> str:
    """生成工具描述文本"""
    desc = []
    for i, (name, tool) in enumerate(TOOLS.items(), 1):
        params = ", ".join(tool["parameters"]["properties"].keys())
        desc.append(f"{i}. **{name}**({params}): {tool['description']}")
    return "\n".join(desc)


def get_tool_names() -> list:
    """获取所有工具名称"""
    return list(TOOLS.keys())
