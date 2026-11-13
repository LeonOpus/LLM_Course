"""
基础智能体类
定义所有智能体的通用接口和功能
"""
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import sys
sys.path.append(str(__file__).rsplit('/', 4)[0])

from core.tools.llm import LLMService

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """智能体状态"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentMessage:
    """智能体消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    receiver: str = ""
    content: str = ""
    message_type: str = "text"  # text, task, result, error
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


class BaseAgent(ABC):
    """
    基础智能体抽象类
    所有专业智能体都需要继承此类
    """

    def __init__(
        self,
        name: str,
        role: str,
        llm_service: Optional[LLMService] = None
    ):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.role = role
        self.state = AgentState.IDLE
        self.llm = llm_service or LLMService()

        # 消息历史
        self.message_history: List[AgentMessage] = []

        # 系统提示
        self._system_prompt = self._build_system_prompt()

        logger.info(f"[{self.name}] 初始化智能体: {self.role}")

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """构建系统提示，子类必须实现"""
        pass

    @abstractmethod
    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """执行任务，子类必须实现"""
        pass

    async def think(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        思考并生成回复

        Args:
            input_text: 输入文本
            context: 上下文信息

        Returns:
            思考结果
        """
        self.state = AgentState.THINKING
        logger.info(f"[{self.name}] 开始思考: {input_text[:100]}...")

        try:
            # 构建消息
            messages = [{"role": "system", "content": self._system_prompt}]

            # 添加上下文
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                messages.append({
                    "role": "user",
                    "content": f"当前上下文:\n{context_str}"
                })

            # 添加用户输入
            messages.append({"role": "user", "content": input_text})

            # 调用LLM
            response = await self.llm.achat(messages)

            self.state = AgentState.IDLE
            logger.info(f"[{self.name}] 思考完成, 回复长度: {len(response)}")

            return response

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"[{self.name}] 思考失败: {str(e)}")
            raise

    def send_message(self, receiver: str, content: str, message_type: str = "text") -> AgentMessage:
        """
        发送消息给其他智能体

        Args:
            receiver: 接收者名称
            content: 消息内容
            message_type: 消息类型

        Returns:
            发送的消息
        """
        message = AgentMessage(
            sender=self.name,
            receiver=receiver,
            content=content,
            message_type=message_type
        )

        self.message_history.append(message)
        logger.info(f"[{self.name}] 发送消息给 {receiver}: {content[:50]}...")

        return message

    def receive_message(self, message: AgentMessage):
        """
        接收消息

        Args:
            message: 接收到的消息
        """
        self.message_history.append(message)
        logger.info(f"[{self.name}] 收到来自 {message.sender} 的消息: {message.content[:50]}...")

    def get_status(self) -> Dict[str, Any]:
        """获取智能体状态"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "state": self.state.value,
            "message_count": len(self.message_history)
        }

    def reset(self):
        """重置智能体状态"""
        self.state = AgentState.IDLE
        self.message_history.clear()
        logger.info(f"[{self.name}] 已重置")
