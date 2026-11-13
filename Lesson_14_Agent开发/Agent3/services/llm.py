"""
LLM服务封装 - 使用qwen-max
"""
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config import settings


class LLMService:
    """LLM服务类，封装qwen-max调用"""

    def __init__(self):
        if not settings.DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY 未设置，请在 .env 文件中配置")

        self.client = OpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.LLM_BASE_URL
        )
        self.model = settings.LLM_MODEL
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            tools: 工具定义列表
            tool_choice: 工具选择策略
        
        Returns:
            API响应
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        
        response = self.client.chat.completions.create(**kwargs)
        return response
    
    def simple_chat(self, prompt: str, system_prompt: str = None) -> str:
        """
        简单聊天接口
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
        
        Returns:
            助手回复
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.chat(messages)
        return response.choices[0].message.content
    
    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        tool_choice: str = "auto"
    ) -> Dict[str, Any]:
        """
        带工具调用的聊天
        
        Args:
            messages: 消息列表
            tools: 工具定义
            tool_choice: 工具选择策略
        
        Returns:
            API响应
        """
        response = self.chat(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice
        )
        return response


# 单例模式
_llm_service = None


def get_llm_service() -> LLMService:
    """获取LLM服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
