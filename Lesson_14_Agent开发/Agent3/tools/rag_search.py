"""
RAG检索工具 - 基于向量数据库的语义检索
"""
import os
import sys
import json
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.embedding import get_embedding_service


class RAGSearchTool:
    """RAG检索工具类"""
    
    name = "rag_search"
    description = """从研报知识库中检索相关信息。适用于：
    - 查询研报中的具体内容
    - 搜索特定主题的分析
    - 获取历史研报观点"""
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.knowledge_base = []  # 内存知识库
        self._initialized = False
    
    def _load_knowledge_base(self, documents: List[Dict[str, str]] = None):
        """
        加载知识库
        
        Args:
            documents: 文档列表，每个文档包含 'content' 和 'metadata'
        """
        if documents:
            for doc in documents:
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})
                
                # 生成向量
                embedding = self.embedding_service.embed_single(content)
                
                self.knowledge_base.append({
                    "content": content,
                    "metadata": metadata,
                    "embedding": embedding
                })
        
        self._initialized = True
    
    def add_document(self, content: str, metadata: Dict = None):
        """
        添加单个文档到知识库
        
        Args:
            content: 文档内容
            metadata: 元数据
        """
        embedding = self.embedding_service.embed_single(content)
        
        self.knowledge_base.append({
            "content": content,
            "metadata": metadata or {},
            "embedding": embedding
        })
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0
        
        return dot_product / (norm1 * norm2)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        执行语义检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
        
        Returns:
            检索结果列表
        """
        if not self.knowledge_base:
            return []
        
        # 生成查询向量
        query_embedding = self.embedding_service.embed_single(query)
        
        # 计算相似度
        results = []
        for doc in self.knowledge_base:
            similarity = self._cosine_similarity(query_embedding, doc["embedding"])
            results.append({
                "content": doc["content"],
                "metadata": doc["metadata"],
                "similarity": similarity
            })
        
        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results[:top_k]
    
    def run(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        执行RAG检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
        
        Returns:
            检索结果
        """
        results = self.search(query, top_k)
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total_count": len(results)
        }
    
    def load_from_pdf(self, pdf_path: str, chunk_size: int = 500):
        """
        从PDF文件加载知识库
        
        Args:
            pdf_path: PDF文件路径
            chunk_size: 文本分块大小
        """
        from tools.pdf_parser import PDFParserTool
        
        parser = PDFParserTool()
        result = parser.run(pdf_path)
        
        if result.get("success"):
            text = result.get("text_content", "")
            
            # 按###或##切分
            sections = self._split_by_headers(text)
            
            for i, section in enumerate(sections):
                if len(section.strip()) > 50:  # 过滤太短的片段
                    self.add_document(
                        content=section.strip(),
                        metadata={
                            "source": pdf_path,
                            "section_index": i,
                            "type": "pdf"
                        }
                    )
            
            return {
                "success": True,
                "document_count": len(sections),
                "source": pdf_path
            }
        
        return {
            "success": False,
            "error": result.get("error", "PDF解析失败")
        }
    
    def _split_by_headers(self, text: str) -> List[str]:
        """
        按标题切分文本
        
        优先按###切分，如果没有###则按##切分
        """
        import re
        
        # 先尝试按###切分
        sections = re.split(r'\n###\s+', text)
        
        if len(sections) <= 1:
            # 如果没有###，尝试按##切分
            sections = re.split(r'\n##\s+', text)
        
        if len(sections) <= 1:
            # 如果还是没有，按段落切分（连续的换行）
            sections = re.split(r'\n\n+', text)
        
        # 过滤空白片段
        sections = [s for s in sections if s.strip()]
        
        return sections


# 工具函数定义（用于LangGraph）
RAG_SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "rag_search",
        "description": "从研报知识库中进行语义检索，获取相关内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询，如'公司的营收增长情况'、'风险因素分析'"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量，默认5",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}


if __name__ == "__main__":
    # 测试
    rag = RAGSearchTool()
    
    # 添加测试文档
    test_docs = [
        {"content": "贵州茅台2024年营业收入预计增长15%，净利润增长12%。公司坚持高端化战略，产品结构持续优化。", "metadata": {"source": "test", "type": "finance"}},
        {"content": "工商银行作为国内最大的商业银行，资产规模超过40万亿。2024年净息差有所收窄，但资产质量保持稳定。", "metadata": {"source": "test", "type": "finance"}},
        {"content": "新能源汽车行业2024年增速放缓，但渗透率继续提升。宁德时代保持动力电池市场领先地位。", "metadata": {"source": "test", "type": "industry"}},
    ]
    
    for doc in test_docs:
        rag.add_document(doc["content"], doc["metadata"])
    
    # 测试检索
    queries = ["茅台的业绩预期", "银行股的投资价值", "新能源发展趋势"]
    
    for query in queries:
        print(f"\n查询: {query}")
        result = rag.run(query, top_k=2)
        for r in result["results"]:
            print(f"  相似度: {r['similarity']:.3f}")
            print(f"  内容: {r['content'][:100]}...")
