from enum import Enum
from typing import Dict, List


class SubjectType(str, Enum):
    """学科类型枚举"""
    GENERAL = "general"  # 通用学科
    MATH = "math"
    CHINESE = "chinese"
    ENGLISH = "english"


class GradeLevel(str, Enum):
    """年级枚举"""
    PRIMARY_1 = "小学一年级"
    PRIMARY_2 = "小学二年级"
    PRIMARY_3 = "小学三年级"
    PRIMARY_4 = "小学四年级"
    PRIMARY_5 = "小学五年级"
    PRIMARY_6 = "小学六年级"
    MIDDLE_1 = "初中一年级"
    MIDDLE_2 = "初中二年级"
    MIDDLE_3 = "初中三年级"
    HIGH_1 = "高中一年级"
    HIGH_2 = "高中二年级"
    HIGH_3 = "高中三年级"


class DifficultyLevel(str, Enum):
    """难度等级枚举"""
    EASY = "简单"
    MEDIUM = "中等"
    HARD = "困难"


# 学科配置
SUBJECT_CONFIG: Dict[SubjectType, Dict] = {
    SubjectType.GENERAL: {
        "name": "通用",
        "supports_visualization": False,
        "visualization_keywords": []
    },
    SubjectType.MATH: {
        "name": "数学",
        "supports_visualization": True,
        "visualization_keywords": [
            "画", "图", "函数", "几何", "三角形", "圆", "直线", "坐标",
            "图像", "图形", "曲线", "抛物线", "椭圆", "双曲线"
        ]
    },
    SubjectType.CHINESE: {
        "name": "语文",
        "supports_visualization": False,
        "visualization_keywords": []
    },
    SubjectType.ENGLISH: {
        "name": "英语",
        "supports_visualization": False,
        "visualization_keywords": []
    }
} 