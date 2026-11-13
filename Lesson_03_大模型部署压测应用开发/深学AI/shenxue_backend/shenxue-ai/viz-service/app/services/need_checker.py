import logging
import re
from typing import List
import sys
sys.path.append('/app/shared')

from shared.models.subject_models import SubjectType, SUBJECT_CONFIG
from app.models.viz_models import CheckRequest

logger = logging.getLogger(__name__)


class NeedChecker:
    """检查是否需要可视化的服务"""
    
    def __init__(self):
        # 数学可视化关键词
        self.math_viz_keywords = [
            # 几何相关
            "画", "图", "图形", "图像", "示意图", "作图",
            "三角形", "圆", "正方形", "长方形", "平行四边形", "梯形",
            "直线", "射线", "线段", "角", "垂直", "平行",
            "坐标", "坐标系", "点", "原点",
            
            # 函数相关
            "函数", "图像", "曲线", "抛物线", "直线", "双曲线", "椭圆",
            "一次函数", "二次函数", "反比例函数", "三角函数",
            "正弦", "余弦", "正切", "sin", "cos", "tan",
            
            # 统计图表
            "柱状图", "条形图", "折线图", "饼图", "散点图", "直方图",
            "频率", "频数", "统计", "数据",
            
            # 立体几何
            "立体", "空间", "正方体", "长方体", "圆柱", "圆锥", "球",
            "投影", "截面", "三视图",
            
            # 解析几何
            "解析几何", "向量", "距离", "斜率", "截距"
        ]
        
        # 强制需要可视化的关键词
        self.force_viz_keywords = [
            "画出", "作出", "绘制", "画图", "作图", "图解",
            "画函数图像", "画图形", "作示意图"
        ]
    
    async def check_need(self, request: CheckRequest) -> bool:
        """检查是否需要可视化"""
        try:
            # 检查学科是否支持可视化
            if not self._subject_supports_viz(request.subject):
                return False
            
            # 检查强制可视化关键词
            if self._has_force_viz_keywords(request.text):
                logger.info("Found force visualization keywords")
                return True
            
            # 检查一般可视化关键词
            if self._has_viz_keywords(request.text):
                logger.info("Found visualization keywords")
                return True
            
            # 检查数学表达式模式
            if self._has_math_patterns(request.text):
                logger.info("Found math patterns that may need visualization")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking visualization need: {e}")
            return False
    
    def _subject_supports_viz(self, subject: SubjectType) -> bool:
        """检查学科是否支持可视化"""
        subject_config = SUBJECT_CONFIG.get(subject)
        return subject_config and subject_config.get("supports_visualization", False)
    
    def _has_force_viz_keywords(self, text: str) -> bool:
        """检查是否包含强制可视化关键词"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.force_viz_keywords)
    
    def _has_viz_keywords(self, text: str) -> bool:
        """检查是否包含可视化关键词"""
        text_lower = text.lower()
        keyword_count = sum(1 for keyword in self.math_viz_keywords if keyword in text_lower)
        
        # 如果包含2个或以上关键词，认为需要可视化
        return keyword_count >= 2
    
    def _has_math_patterns(self, text: str) -> bool:
        """检查是否包含数学模式"""
        patterns = [
            r'[xy]\s*=\s*[^=]+',  # 函数表达式 y = ...
            r'f\([xy]\)\s*=\s*[^=]+',  # 函数定义 f(x) = ...
            r'[xy]²|[xy]\^2',  # 二次项
            r'sin|cos|tan',  # 三角函数
            r'√|sqrt',  # 根号
            r'∠|角[A-Z]',  # 角度
            r'△|三角形[A-Z]',  # 三角形
            r'⊙|圆[A-Z]',  # 圆
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False 