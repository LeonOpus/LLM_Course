#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试基于Function Call的旅行助手
"""

import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from travel_assistant_funcall import TravelAssistantFuncCall


def test_assistant():
    """测试旅行助手的各种功能"""
    print("🌍 测试基于Function Call的旅行助手")
    print("=" * 50)
    
    # 测试用户信息功能
    assistant = TravelAssistantFuncCall(
        user_name="测试用户",
        user_city_id="101020100",  # 上海的城市ID
        travel_date_range="2025-09-15",
        start_coordinates="121.472644,31.231706"  # 上海坐标
    )
    print(f"测试用户信息 - 城市ID: {assistant.user_info['city_id']}, 日期范围: {assistant.user_info['travel_date_range']}")
    print("-" * 50)
    
    # 测试用例 - 包含完整信息和缺少信息的情况
    test_cases = [
        # 利用用户信息的测试
        "重庆怎么玩",           # 应该基于用户当前城市上海
        # "想体验现代都市生活",                   # 应该从上海出发
        # "推荐本地酒店，预算500元",        # 应该推荐上海的酒店
        
        # # 传统测试用例
        # "从天安门到颐和园怎么走",          # 明确起终点的问路
        # "我要出去，怎么走？",             # 缺少终点的问路
        # "推荐商务酒店，预算800元以内",     # 缺少城市的酒店推荐
        # "北京假日酒店怎么样",             # 酒店评价查询
        # "1+1等于几"                      # 非旅行相关问题
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test_input}")
        print("-" * 30)
        
        try:
            print("处理过程:")
            response = assistant.process_user_input(test_input)
            print(f"\n最终回复: {response}")
        except Exception as e:
            print(f"❌ 测试失败: {e}")
        
        print()


if __name__ == "__main__":
    test_assistant()