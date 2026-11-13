import httpx
import json
import asyncio
import logging
import base64
import os
from typing import AsyncGenerator, Dict, Any, Optional, List, Union
import sys
sys.path.append('/app/shared')

from shared.models.subject_models import SubjectType, SUBJECT_CONFIG
from shared.models.request_models import QuestionRequest

logger = logging.getLogger(__name__)


class DashScopeService:
    """阿里云百炼API服务"""
    
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 30, sync_timeout: int = 90, max_retries: int = 3):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        # 为非流式请求创建一个更长的超时配置
        self.timeout = httpx.Timeout(
            connect=10.0,  # 连接超时
            read=timeout,  # 读取超时 (30秒)
            write=10.0,    # 写入超时
            pool=10.0      # 连接池超时
        )
        # 为非流式请求使用更长的超时
        self.sync_timeout = httpx.Timeout(
            connect=10.0,  # 连接超时
            read=sync_timeout,  # 读取超时，可配置
            write=10.0,    # 写入超时
            pool=10.0      # 连接池超时
        )
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.AsyncClient] = None
    
    async def get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端（流式请求用）"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def get_sync_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端（非流式请求用，超时时间更长）"""
        if self._sync_client is None:
            self._sync_client = httpx.AsyncClient(timeout=self.sync_timeout)
        return self._sync_client
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
        if self._sync_client:
            await self._sync_client.aclose()
    
    def _build_system_prompt(self, subject: SubjectType) -> str:
        """构建系统提示词"""
        subject_config = SUBJECT_CONFIG.get(subject)
        subject_name = subject_config["name"] if subject_config else "老师"
        
        if subject == SubjectType.GENERAL:
            base_prompt = f"""你是一个博学的AI助手，请按照以下要求回答用户的问题：

## 回答要求：
1. 回答要准确、详细、实用
2. 提供清晰的分析思路和解答步骤
3. 语言要通俗易懂，适合不同背景的用户
4. 鼓励用户思考，提供相关的延伸知识
5. 注重知识的准确性和实用性
6. 如果涉及专业领域，请说明相关的前提条件
7. 保持客观中立的态度
8. 必要时提供参考资料或进一步学习的建议

## 输出格式：
请使用Markdown格式组织答案，包含：
- # 思路讲解：简要说明问题的核心和解决思路
- # 详细解答：提供完整的答案和分析
- # 总结：概括要点，提供记忆要点或实践建议"""

        elif subject == SubjectType.MATH:
            base_prompt = f"""你是一个专业的{subject_name}老师，请按照以下要求回答学生的数学问题：

## 回答要求：
1. 回答要严谨、准确，注重数学逻辑
2. 提供清晰的解题思路和步骤
3. 适当解释数学概念的本质和意义
4. **⚠️ 公式格式要求（必须严格遵守）：所有数学公式必须用$包裹**
   - 内联公式用单个$，如：$x^2 + 1 = 0$
   - 块级公式用双$$，如：$$x = \\frac{{-b \\pm \\sqrt{{b^2-4ac}}}}{{2a}}$$

## 回答格式：
请严格按照以下Markdown格式组织你的回答：

# 思路讲解
[在这里分析问题的核心思路和解题方法选择]

# 解题步骤
## 步骤一
[详细描述第一个解题步骤]

## 步骤二  
[详细描述第二个解题步骤]

[如有更多步骤，继续添加...]

# 最终结果
[给出最终答案和结论]

## 具体要求：
- 每个解题步骤都要详细说明原理和计算过程
- 对于几何问题，如果需要图形辅助理解，请在回答中明确说明
- 语言要准确、清晰，适合学生理解"""

        elif subject == SubjectType.CHINESE:
            base_prompt = f"""你是一个专业的{subject_name}老师，请按照以下要求回答学生的语文问题：

## 回答要求：
1. 回答要准确、深入，注重文学性和思想性
2. 提供详细的文本分析和解读
3. 注重语言文字的美感和表达技巧
4. 结合相关的文化背景和历史知识
5. 培养学生的文学鉴赏能力和人文素养
6. 鼓励学生多读、多思、多表达
7. 对于古诗文，要注重字词解释和意境分析
8. 对于现代文，要注重主题思想和表现手法
9. 语言表达要优美流畅，富有感染力

## 输出格式：
请使用Markdown格式组织答案，包含：
- # 思路讲解：说明分析的角度和方法
- # 详细分析：深入的文本解读和赏析
- # 总结感悟：概括要点，提供思考启发"""

        elif subject == SubjectType.ENGLISH:
            base_prompt = f"""你是一个专业的{subject_name}老师，请按照以下要求回答学生的英语问题：

## 回答要求：
1. 回答要准确、实用，注重语言的应用性
2. 提供详细的语法解释和用法说明
3. 给出丰富的例句和应用场景
4. 注重听说读写四项技能的综合培养
5. 适当补充相关的文化背景知识
6. 鼓励学生多练习、多运用
7. 对于语法问题，要系统性地讲解规则和例外
8. 对于词汇问题，要提供词根词缀、同义词辨析等
9. 语言表达要清晰易懂，中英文结合使用

## 输出格式：
请使用Markdown格式组织答案，包含：
- # 思路讲解：说明知识点的核心和学习要点
- # 详细解答：系统的语法或词汇讲解
- # 实用例句：丰富的例句和使用场景
- # 学习建议：提供练习方法和记忆技巧"""

        else:
            # 后备的通用提示词
            base_prompt = f"""你是一个专业的助手，请按照以下要求回答问题：

## 回答要求：
1. 回答要准确、详细、易懂
2. 提供清晰的分析思路和解答步骤
3. 语言要适合用户的理解水平
4. 鼓励用户思考，必要时可以提供相关的练习建议
5. 注重知识的系统性和实用性
6. 培养用户的思维和分析能力

## 输出格式：
请使用Markdown格式组织答案，提供清晰的结构和内容。"""
        
        return base_prompt
    
    def _build_user_message(self, request: QuestionRequest) -> Union[str, List[Dict[str, Any]]]:
        """构建用户消息 - 支持多模态（文本+图片）"""
        
        # 如果没有图片，返回简单的文本消息
        if not request.image_url:
            return request.text or "请帮我分析这个问题"
        
        # 有图片时，构建多模态消息
        content = []
        
        # 添加文本内容
        if request.text:
            content.append({
                "type": "text",
                "text": request.text
            })
        else:
            content.append({
                "type": "text", 
                "text": "请分析这张图片"
            })
        
        # 处理图片
        if request.image_url.startswith("file://"):
            # 本地文件路径
            file_path = request.image_url[7:]  # 移除 "file://" 前缀
            
            if os.path.exists(file_path):
                try:
                    # 读取文件并转换为base64
                    with open(file_path, "rb") as image_file:
                        image_data = image_file.read()
                        image_base64 = base64.b64encode(image_data).decode('utf-8')
                    
                    # 获取文件扩展名来确定MIME类型
                    file_ext = os.path.splitext(file_path)[1].lower()
                    mime_type = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg', 
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.webp': 'image/webp'
                    }.get(file_ext, 'image/jpeg')
                    
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}"
                        }
                    })
                    
                    logger.info(f"Loaded local image: {file_path}")
                    
                except Exception as e:
                    logger.error(f"Error loading local image {file_path}: {e}")
                    content.append({
                        "type": "text",
                        "text": f"[图片加载失败: {file_path}]"
                    })
            else:
                logger.warning(f"Local image file not found: {file_path}")
                content.append({
                    "type": "text", 
                    "text": f"[图片文件不存在: {file_path}]"
                })
        
        elif request.image_url.startswith("http"):
            # HTTP URL
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": request.image_url
                }
            })
        
        else:
            # 其他格式，当作文本处理
            content.append({
                "type": "text",
                "text": f"[图片]: {request.image_url}"
            })
        
        return content

    def _build_messages(self, request: QuestionRequest) -> List[Dict[str, Any]]:
        """构建完整的消息列表"""
        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt(request.subject)
            }
        ]
        
        user_message_content = self._build_user_message(request)
        
        messages.append({
            "role": "user",
            "content": user_message_content
        })
        
        return messages

    async def get_answer_stream(self, request: QuestionRequest) -> AsyncGenerator[str, None]:
        """获取流式回答"""
        for attempt in range(self.max_retries):
            try:
                client = await self.get_client()
                
                # 构建请求数据
                messages = self._build_messages(request)
                
                request_data = {
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                logger.info(f"Sending stream request to DashScope API (attempt {attempt + 1}/{self.max_retries})")
                
                # 发送流式请求
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=request_data,
                    headers=headers
                ) as response:
                    
                    logger.info(f"DashScope stream API response: {response.status_code}")
                    
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"DashScope stream API error: status={response.status_code}, response={error_text}")
                        
                        if response.status_code == 429:
                            # 限流错误
                            wait_time = (attempt + 1) * 2
                            logger.warning(f"Stream rate limit hit, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                            if attempt < self.max_retries - 1:
                                continue
                        
                        yield f"API调用失败: {response.status_code} - {error_text.decode() if error_text else 'Unknown error'}"
                        return
                    
                    # 处理流式响应
                    content_received = False
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            
                            if data_str.strip() == "[DONE]":
                                logger.info("Stream completed successfully")
                                break
                            
                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    
                                    if content:
                                        content_received = True
                                        yield content
                                        
                            except json.JSONDecodeError:
                                continue
                            except Exception as e:
                                logger.warning(f"Error processing stream chunk: {e}")
                                continue
                    
                    if not content_received:
                        logger.warning("No content received from stream")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2)
                            continue
                        else:
                            yield "未收到有效内容"
                    
                    return  # 成功完成，退出重试循环
                            
            except httpx.TimeoutException as e:
                logger.error(f"DashScope stream API timeout (attempt {attempt + 1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    yield "请求超时，请稍后重试"
                    return
                await asyncio.sleep(2)
                continue
                
            except httpx.RequestError as e:
                logger.error(f"DashScope stream API request error (attempt {attempt + 1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    yield f"网络请求错误: {str(e)}"
                    return
                await asyncio.sleep(2)
                continue
                
            except Exception as e:
                logger.error(f"DashScope stream API unexpected error (attempt {attempt + 1}): {type(e).__name__}: {str(e)}")
                if attempt == self.max_retries - 1:
                    yield f"服务暂时不可用: {type(e).__name__}: {str(e)}"
                    return
                await asyncio.sleep(1)
                continue
        
        yield "所有重试均失败，服务暂时不可用"
    
    async def get_answer(self, request: QuestionRequest) -> str:
        """获取完整回答（非流式）"""
        for attempt in range(self.max_retries):
            try:
                # 使用专门的同步客户端，超时时间更长
                client = await self.get_sync_client()
                
                # 构建请求数据
                messages = self._build_messages(request)
                
                request_data = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                logger.info(f"Sending request to DashScope API (attempt {attempt + 1}/{self.max_retries}) with extended timeout")
                
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=request_data,
                    headers=headers
                )
                
                logger.info(f"DashScope API response: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    choices = result.get("choices", [])
                    if choices:
                        content = choices[0]["message"]["content"]
                        logger.info(f"Successfully got response, length: {len(content)}")
                        return content
                    else:
                        logger.warning("DashScope API returned empty choices")
                        return "未收到有效回答"
                
                elif response.status_code == 429:
                    # 限流错误，等待后重试
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Rate limit hit, waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                    continue
                
                else:
                    error_text = response.text
                    logger.error(f"DashScope API error: status={response.status_code}, response={error_text}")
                    
                    if attempt == self.max_retries - 1:  # 最后一次尝试
                        return f"API调用失败: {response.status_code} - {error_text}"
                    
                    # 等待后重试
                    await asyncio.sleep(1)
                    continue
                    
            except httpx.TimeoutException as e:
                logger.error(f"DashScope API timeout (attempt {attempt + 1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    return "请求超时，请稍后重试。建议使用流式模式获得更好的体验。"
                await asyncio.sleep(2)
                continue
                
            except httpx.RequestError as e:
                logger.error(f"DashScope API request error (attempt {attempt + 1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    return f"网络请求错误: {str(e)}"
                await asyncio.sleep(2)
                continue
                
            except json.JSONDecodeError as e:
                logger.error(f"DashScope API JSON decode error (attempt {attempt + 1}): {str(e)}")
                if attempt == self.max_retries - 1:
                    return "API响应格式错误"
                await asyncio.sleep(1)
                continue
                
            except Exception as e:
                logger.error(f"DashScope API unexpected error (attempt {attempt + 1}): {type(e).__name__}: {str(e)}")
                if attempt == self.max_retries - 1:
                    return f"服务暂时不可用: {type(e).__name__}: {str(e)}"
                await asyncio.sleep(1)
                continue
        
        return "服务暂时不可用，所有重试均失败" 