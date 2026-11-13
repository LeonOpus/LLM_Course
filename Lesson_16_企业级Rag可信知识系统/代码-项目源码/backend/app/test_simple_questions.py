#!/usr/bin/env python3
"""
测试优化后的推荐问题生成功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
# cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# revision: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# cache: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# cache: lpf2-18Lb8 lpf2-19A32
sys.path.append(str(Path(__file__).parent))

def test_simple_questions():
    """测试简化后的推荐问题生成"""
    try:
        from service.core.chat import generate_recommended_questions
        
        print("🧪 测试1: 纯问题扩展（无文档）")
        questions1 = generate_recommended_questions("什么是Python？")
        print(f"生成结果: {questions1}")
        
        print("\n🧪 测试2: 有文档上下文")
        mock_content = [
            {"document_name": "Python教程.pdf", "content_with_weight": "..."},
            {"document_name": "编程基础.docx", "content_with_weight": "..."}
        ]
        questions2 = generate_recommended_questions("什么是Python？", mock_content)
        print(f"生成结果: {questions2}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_questions()
    print(f"\n{'✅ 测试通过' if success else '❌ 测试失败'}") 