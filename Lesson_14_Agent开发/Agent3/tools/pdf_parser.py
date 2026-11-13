"""
PDF解析工具 - 使用阿里DocMind API
"""
import os
import sys
import json
import time
import base64
import httpx
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings


class PDFParserTool:
    """PDF解析工具类 - 使用阿里云DocMind"""

    name = "pdf_parser"
    description = """解析PDF研报文档，提取文本内容、表格、图表信息。适用于：
    - 读取研究报告内容
    - 提取财务报表数据
    - 获取研报关键信息"""

    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/docmind/document-analysis"
    
    def _submit_task(self, file_path: str) -> Optional[str]:
        """
        提交PDF解析任务
        
        Args:
            file_path: PDF文件路径
        
        Returns:
            任务ID
        """
        # 读取文件并base64编码
        with open(file_path, 'rb') as f:
            file_content = base64.standard_b64encode(f.read()).decode('utf-8')
        
        file_name = os.path.basename(file_path)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "docmind-v1",
            "input": {
                "file_type": "pdf",
                "file_name": file_name,
                "file_content": file_content
            },
            "parameters": {
                "parse_mode": "scan",  # scan模式更适合复杂文档
                "output_figure": True,
                "output_table": True
            }
        }
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/async-submit",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("output", {}).get("task_id"):
                        return result["output"]["task_id"]
                    else:
                        print(f"提交任务失败: {result}")
                        return None
                else:
                    print(f"API请求失败: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            print(f"提交任务异常: {e}")
            return None
    
    def _get_task_result(self, task_id: str, max_wait: int = 120) -> Optional[Dict]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            max_wait: 最大等待时间（秒）
        
        Returns:
            解析结果
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "task_id": task_id
        }
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        f"{self.base_url}/async-fetch",
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        task_status = result.get("output", {}).get("task_status")
                        
                        if task_status == "SUCCEEDED":
                            return result.get("output", {}).get("result")
                        elif task_status == "FAILED":
                            print(f"任务失败: {result}")
                            return None
                        else:
                            # 任务还在处理中
                            time.sleep(2)
                    else:
                        print(f"获取结果失败: {response.status_code}")
                        return None
            except Exception as e:
                print(f"获取结果异常: {e}")
                time.sleep(2)
        
        print("任务超时")
        return None
    
    def _parse_result(self, result: Dict) -> Dict[str, Any]:
        """
        解析API返回结果
        
        Args:
            result: API原始结果
        
        Returns:
            结构化的解析结果
        """
        parsed = {
            "text_content": "",
            "tables": [],
            "figures": [],
            "page_count": 0,
            "sections": []
        }
        
        if not result:
            return parsed
        
        # 提取文本内容
        pages = result.get("pages", [])
        parsed["page_count"] = len(pages)
        
        all_text = []
        for page in pages:
            page_text = []
            for block in page.get("blocks", []):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        page_text.append(text)
                elif block.get("type") == "table":
                    parsed["tables"].append({
                        "page": page.get("page_no", 0),
                        "content": block.get("table", {})
                    })
                elif block.get("type") == "figure":
                    parsed["figures"].append({
                        "page": page.get("page_no", 0),
                        "caption": block.get("caption", "")
                    })
            
            all_text.append("\n".join(page_text))
        
        parsed["text_content"] = "\n\n--- 分页 ---\n\n".join(all_text)
        
        return parsed
    
    def parse_local_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        解析本地PDF文件（使用简单方法，不依赖DocMind API）
        
        Args:
            file_path: PDF文件路径
        
        Returns:
            解析结果
        """
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(file_path)
            
            result = {
                "success": True,
                "file_path": file_path,
                "page_count": len(reader.pages),
                "text_content": "",
                "pages": []
            }
            
            all_text = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                all_text.append(text)
                result["pages"].append({
                    "page_no": i + 1,
                    "text": text[:2000] if len(text) > 2000 else text  # 限制每页文本长度
                })
            
            result["text_content"] = "\n\n".join(all_text)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    def run(self, file_path: str, use_docmind: bool = True) -> Dict[str, Any]:
        """
        解析PDF文件

        Args:
            file_path: PDF文件路径
            use_docmind: 是否使用DocMind API（需要DASHSCOPE_API_KEY），默认True

        Returns:
            解析结果
        """
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在: {file_path}"
            }

        if use_docmind and self.api_key:
            # 使用DocMind API
            print(f"使用DocMind API解析: {file_path}")
            task_id = self._submit_task(file_path)
            if task_id:
                result = self._get_task_result(task_id)
                if result:
                    parsed = self._parse_result(result)
                    parsed["success"] = True
                    parsed["method"] = "docmind"
                    return parsed
            print("DocMind解析失败，回退到本地解析")
        elif use_docmind and not self.api_key:
            print("DASHSCOPE_API_KEY未设置，使用本地解析")

        # 使用本地解析（PyPDF2）
        result = self.parse_local_pdf(file_path)
        result["method"] = "local"
        return result


# 工具函数定义（用于LangGraph）
PDF_PARSER_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "pdf_parser",
        "description": "解析PDF研报文档，提取文本内容。适用于读取研究报告、财务报表等PDF文件。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "PDF文件的完整路径"
                },
                "use_docmind": {
                    "type": "boolean",
                    "description": "是否使用DocMind API进行高级解析，默认True（需要DASHSCOPE_API_KEY）",
                    "default": True
                }
            },
            "required": ["file_path"]
        }
    }
}


if __name__ == "__main__":
    # 测试
    parser = PDFParserTool()
    
    test_path = "data/中金公司2025年中期报告.pdf"
    
    if os.path.exists(test_path):
        print(f"解析文件: {test_path}")
        result = parser.run(test_path)
        print(f"解析成功: {result.get('success')}")
        print(f"页数: {result.get('page_count')}")
        print(f"文本长度: {len(result.get('text_content', ''))}")
        print(f"前500字符:\n{result.get('text_content', '')[:500]}")
    else:
        print(f"测试文件不存在: {test_path}")
