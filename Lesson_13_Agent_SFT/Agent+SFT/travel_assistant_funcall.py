#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基于Function Call的旅行助手
使用qwen-plus模型自主判断并调用工具
"""

import json
import sys
import os
import requests
from typing import Dict, List, Any, Optional
from openai import OpenAI

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.get_route import query_routes, geocode
from tools.get_weather import get_weather_by_date
from tools.get_hotel import get_hotel_recommendations, get_hotel_reviews


class TravelAssistantFuncCall:
    """基于Function Call的旅行助手"""
    
    def __init__(self, model_name: str = "qwen-plus", user_name: str = "用户", user_city_id: str = "101010100", 
                 travel_date_range: str = "2025-09-15~2025-10-05", start_coordinates: str = "116.481028,39.989643"):
        self.model_name = model_name
        self.conversation_history = []
        self.rag_api_url = "http://127.0.0.1:8010"
        
        # 城市ID到城市名映射
        city_name_map = {
            "101010100": "北京",
            "101020100": "上海", 
            "101280101": "广州",
            "101280601": "深圳",
            "101210101": "杭州",
            "101190101": "南京"
        }
        
        # 用户信息
        self.user_info = {
            "name": user_name,
            "city_id": user_city_id,  # 城市ID，如北京101010100
            "current_city": city_name_map.get(user_city_id, "北京"),  # 当前城市名称
            "travel_date_range": travel_date_range,  # 出发日期范围 2025-09-15～2025-10-05
            "start_coordinates": start_coordinates,  # 起点坐标 116.481028,39.989643
            "current_date": self._get_current_date()
        }
        
        # 解析出发日期范围
        self._parse_travel_dates()
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key="",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        # 定义工具函数
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_travel_guide",
                    "description": "搜索旅行攻略信息，获取目的地的详细旅游信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "用户的完整查询内容，如'我想去成都'、'北京怎么玩'、'成都有什么好玩的'"
                            },
                            "search_type": {
                                "type": "string",
                                "description": "搜索模式：vector(向量搜索)、keyword(关键词搜索)、hybrid(混合搜索)",
                                "enum": ["vector", "keyword", "hybrid"],
                                "default": "hybrid"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_weather_info",
                    "description": "查询指定地点和时间段的天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "城市名称，如'北京'、'上海'，或城市ID如'101010100'"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "开始日期，格式YYYY-MM-DD，如'2025-09-15'"
                            },
                            "num_days": {
                                "type": "integer",
                                "description": "查询天数，默认1天。根据旅行攻略中的行程天数确定"
                            }
                        },
                        "required": ["location", "start_date"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_route",
                    "description": "查询两地之间的路线，包括步行、公交、驾车路线",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_location": {
                                "type": "string",
                                "description": "起点坐标，如'116.481028,39.989643'"
                            },
                            "end_location": {
                                "type": "string",
                                "description": "终点地址，如'颐和园'"
                            },
                            "city_code": {
                                "type": "string",
                                "description": "城市代码，默认'110000'(北京)",
                                "default": "110000"
                            }
                        },
                        "required": ["end_location"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "recommend_hotels",
                    "description": "根据用户需求推荐酒店",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "requirements": {
                                "type": "string",
                                "description": "用户对酒店的需求描述，包括地点、预算、设施等"
                            }
                        },
                        "required": ["requirements"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_hotel_reviews",
                    "description": "获取指定酒店的用户评价信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hotel_name": {
                                "type": "string",
                                "description": "酒店名称或用户问题，如'北京假日酒店怎么样'"
                            }
                        },
                        "required": ["hotel_name"]
                    }
                }
            }
        ]
    
    def _get_current_date(self) -> str:
        """获取当前日期"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")
    
    def _parse_travel_dates(self):
        """解析出发日期范围"""
        try:
            if "~" in self.user_info["travel_date_range"]:
                start_str, end_str = self.user_info["travel_date_range"].split("~")
                self.user_info["travel_start_date"] = start_str.strip()
                self.user_info["travel_end_date"] = end_str.strip()
            else:
                # 如果没有范围，就作为单一日期
                self.user_info["travel_start_date"] = self.user_info["travel_date_range"]
                self.user_info["travel_end_date"] = self.user_info["travel_date_range"]
        except Exception as e:
            print(f"解析出发日期出错: {e}")
            # 使用默认值
            self.user_info["travel_start_date"] = "2025-09-15"
            self.user_info["travel_end_date"] = "2025-10-05"
    
    def add_to_history(self, role: str, content: str):
        """添加对话历史"""
        self.conversation_history.append({"role": role, "content": content})
        # 保持对话历史在合理长度内
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def search_travel_guide(self, query: str, search_type: str = "hybrid") -> str:
        """搜索旅行攻略"""
        try:
            url = f"{self.rag_api_url}/search"
            data = {
                "query": query,
                "search_type": search_type,
                "vector_weight": 0.7,
                "keyword_weight": 1.5,
                "limit": 1
            }
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if "results" in result and result["results"]:
                    guides = []
                    for item in result["results"]:
                        if "content" in item:
                            guides.append(item["content"])
                    return "\n\n".join(guides)
                else:
                    return "未找到相关旅行攻略信息"
            else:
                return "旅行攻略查询服务暂时不可用"
        except Exception as e:
            return f"旅行攻略查询出错: {e}"
    
    def get_weather_info(self, location: str, start_date: str, num_days: int = 1) -> str:
        """获取天气信息"""
        # 直接返回模拟天气数据，不实际调用外部API
        import random
        from datetime import datetime, timedelta
        
        # 20%概率返回查询失败
        if random.random() < 0.2:
            return f"无法获取{location}在{start_date}起{num_days}天的天气信息"
        
        # 80%概率返回正常天气数据
        # 定义合理的天气类型
        day_weather_types = ["晴", "多云", "阴", "小雨", "中雨", "雷阵雨", "雾", "霾"]
        night_weather_types = ["晴", "多云", "阴", "小雨", "中雨", "雷阵雨", "雾"]
        
        # 生成天气数据
        weather_list = []
        base_date = datetime.strptime(start_date, "%Y-%m-%d")
        
        for i in range(num_days):
            current_date = base_date + timedelta(days=i)
            
            # 生成合理的温度范围（根据季节调整）
            month = current_date.month
            if month in [12, 1, 2]:  # 冬季
                min_temp = random.randint(-5, 8)
                max_temp = min_temp + random.randint(5, 12)
            elif month in [3, 4, 5]:  # 春季
                min_temp = random.randint(8, 18)
                max_temp = min_temp + random.randint(6, 15)
            elif month in [6, 7, 8]:  # 夏季
                min_temp = random.randint(20, 28)
                max_temp = min_temp + random.randint(5, 12)
            else:  # 秋季
                min_temp = random.randint(10, 20)
                max_temp = min_temp + random.randint(6, 15)
            
            # 生成天气情况
            day_weather = random.choice(day_weather_types)
            night_weather = random.choice(night_weather_types)
            
            weather_data = {
                '日期': current_date.strftime("%Y-%m-%d"),
                '白天天气': day_weather,
                '夜间天气': night_weather,
                '最低温': f"{min_temp}°C",
                '最高温': f"{max_temp}°C"
            }
            weather_list.append(weather_data)
        
        # 构建原格式的响应
        weather_text = f"天气信息({location} - {start_date}起{num_days}天):\n"
        for i, weather in enumerate(weather_list, 1):
            weather_text += f"\n第{i}天 ({weather['日期']}):\n"
            weather_text += f"  白天: {weather['白天天气']}，夜间: {weather['夜间天气']}\n"
            weather_text += f"  温度: {weather['最低温']} ~ {weather['最高温']}\n"
        
        return weather_text
        
        # 原来的代码保留作为注释：
        # try:
        #     from tools.get_weather import get_weather_by_date_range
        #     
        #     # 转换城市名到城市ID的映射
        #     city_id_map = {
        #         "北京": "101010100",
        #         "上海": "101020100",
        #         "广州": "101280101",
        #         "深圳": "101280601",
        #         "杭州": "101210101",
        #         "南京": "101190101"
        #     }
        #     
        #     # 确定城市ID
        #     if location in city_id_map:
        #         location_id = city_id_map[location]
        #     elif location.isdigit():
        #         location_id = location
        #     else:
        #         # 默认使用用户城市ID
        #         location_id = self.user_info["city_id"]
        #     
        #     weather_list = get_weather_by_date_range(location_id, start_date, num_days)
        #     
        #     if weather_list:
        #         weather_text = f"天气信息({location} - {start_date}起{num_days}天):\n"
        #         for i, weather in enumerate(weather_list, 1):
        #             weather_text += f"\n第{i}天 ({weather['日期']}):\n"
        #             weather_text += f"  白天: {weather['白天天气']}，夜间: {weather['夜间天气']}\n"
        #             weather_text += f"  温度: {weather['最低温']} ~ {weather['最高温']}\n"
        #         return weather_text
        #     else:
        #         return f"无法获取{location}在{start_date}起{num_days}天的天气信息"
        # except Exception as e:
        #     return f"天气查询出错: {e}"
    
    def query_route(self, start_location: str, end_location: str, city_code: str = "110000") -> str:
        """查询路线"""
        # 直接返回模拟路线数据，不实际调用外部工具
        import random
        
        # 20%概率返回查询失败
        if random.random() < 0.2:
            return f"抱歉，无法查询到从 {start_location} 到 {end_location} 的路线信息。可能是因为地点名称不准确或者该路线暂时无法规划，请稍后再试或提供更准确的地点信息。"
        
        # 80%概率返回正常路线数据
        # 生成合理的随机数据
        walking_time = random.randint(15, 60)
        walking_distance = walking_time * random.randint(50, 80)
        
        bus_time = random.randint(25, 45) 
        bus_routes = [
            ["地铁1号线", "地铁2号线", "公交123路"],
            ["地铁3号线", "公交456路", "地铁4号线"],
            ["公交789路", "地铁5号线", "公交321路"],
            ["地铁6号线", "公交654路", "地铁7号线"]
        ]
        selected_route = random.choice(bus_routes)
        bus_price = random.choice([3, 4, 5, 6])
        
        car_time = random.randint(20, 35)
        car_distance = car_time * random.randint(800, 1200)
        toll_fee = random.choice([0, 5, 10, 15])
        
        # 构建原格式的响应
        route_text = f"从 {start_location} 到 {end_location} 的路线:\n\n"
        
        route_text += f"【步行】\n"
        route_text += f"总时间: {walking_time}分钟\n"
        route_text += f"总距离: {walking_distance}米\n\n"
        
        route_text += f"【公交】\n"
        route_text += f"总时间: {bus_time}分钟\n"
        route_text += f"票价: {bus_price}元\n"
        route_text += "路线: " + " → ".join(selected_route) + "\n\n"
        
        route_text += f"【驾车/打车】\n"
        route_text += f"总时间: {car_time}分钟\n"
        route_text += f"总距离: {car_distance}米\n"
        if toll_fee > 0:
            route_text += f"过路费: {toll_fee}元\n"
        route_text += "\n"
        
        return route_text
        
        # 原来的代码保留作为注释：
        # try:
        #     # 处理起点坐标
        #     if "," in start_location and len(start_location.split(",")) == 2:
        #         start_coords = start_location
        #     elif start_location == "当前位置":
        #         start_coords = self.user_info["start_coordinates"]
        #     else:
        #         try:
        #             start_coords = geocode(start_location)
        #         except:
        #             # 使用用户默认坐标
        #             start_coords = self.user_info["start_coordinates"]
        #     
        #     routes = query_routes(start_coords, end_location, city_code)
        #     
        #     route_text = f"从 {start_location} 到 {end_location} 的路线:\n\n"
        #     
        #     for mode, info in routes.items():
        #         route_text += f"【{mode}】\n"
        #         if info:
        #             if mode == "步行":
        #                 route_text += f"总时间: {info['总时间(分钟)']}分钟\n"
        #                 route_text += f"总距离: {info['总距离(米)']}米\n"
        #             elif mode == "公交":
        #                 route_text += f"总时间: {info['总时间(分钟)']}分钟\n"
        #                 if info['票价(元)'] != "未知":
        #                     route_text += f"票价: {info['票价(元)']}元\n"
        #                 route_text += "路线: " + " → ".join(info['详细路线'][:3]) + "\n"
        #             elif mode == "驾车/打车":
        #                 route_text += f"总时间: {info['总时间(分钟)']}分钟\n"
        #                 route_text += f"总距离: {info['总距离(米)']}米\n"
        #                 if info['过路费(元)'] != "0":
        #                     route_text += f"过路费: {info['过路费(元)']}元\n"
        #         else:
        #             route_text += "暂无路线信息\n"
        #         route_text += "\n"
        #     
        #     return route_text
        # except Exception as e:
        #     return f"路线查询出错: {e}"
    
    def recommend_hotels(self, requirements: str) -> str:
        """推荐酒店"""
        try:
            hotels = get_hotel_recommendations(requirements)
            if hotels:
                hotel_text = "根据您的需求，推荐以下酒店:\n\n"
                for i, hotel in enumerate(hotels[:3], 1):
                    hotel_text += f"酒店{i}: {hotel['hotel_name']}\n"
                    hotel_text += f"位置: {hotel['location']}\n"
                    # 由于新的JSON格式可能只包含hotel_name和location，需要安全地获取其他字段
                    if hotel.get('price_range'):
                        hotel_text += f"价格: {hotel['price_range']}\n"
                    if hotel.get('rating'):
                        hotel_text += f"评分: {hotel['rating']}/5\n"
                    if hotel.get('amenities'):
                        hotel_text += f"设施: {', '.join(hotel['amenities'][:4])}\n"
                    if hotel.get('distance_to_transport'):
                        hotel_text += f"交通: {hotel['distance_to_transport']}\n"
                    hotel_text += "\n"
                return hotel_text
            else:
                return "暂时没有找到符合您需求的酒店推荐"
        except Exception as e:
            return f"酒店推荐出错: {e}"
    
    def get_hotel_reviews_func(self, hotel_name: str) -> str:
        """获取酒店评价"""
        try:
            reviews = get_hotel_reviews(hotel_name)
            if reviews:
                review_text = f"{hotel_name}的用户评价:\n\n"
                for i, review in enumerate(reviews[:2], 1):
                    review_text += f"评价{i}:\n"
                    # 适配新的简化格式
                    if review.get('rating'):
                        review_text += f"评分: {review.get('rating')}/5\n"
                    review_text += f"评论: {review.get('review_content', '')}\n\n"
                return review_text
            else:
                return f"暂时没有找到{hotel_name}的用户评价信息"
        except Exception as e:
            return f"酒店评价查询出错: {e}"
    
    def _integrate_hotel_results(self, hotel_outputs, review_outputs) -> str:
        """手动整合酒店推荐和评价结果"""
        try:
            result = "根据您的需求，我为您推荐以下酒店：\n\n"
            
            # 获取酒店推荐结果
            hotel_info = ""
            for output in hotel_outputs:
                if "酒店" in output["output"]:
                    hotel_info = output["output"]
                    break
            
            # 获取酒店评价结果  
            review_info = ""
            for output in review_outputs:
                if "评价" in output["output"] or "评论" in output["output"]:
                    review_info = output["output"]
                    break
            
            # 整合信息
            if hotel_info:
                result += hotel_info
                if review_info:
                    result += "\n\n【用户评价】\n" + review_info
            else:
                result = "抱歉，暂时无法获取酒店推荐信息，请稍后再试。"
                
            return result
            
        except Exception as e:
            return f"整合酒店信息时出现错误: {e}"
    
    def _should_continue_tool_chain(self, function_name: str, result: str) -> bool:
        """判断是否需要继续工具调用链"""
        if function_name == "recommend_hotels":
            # 如果酒店推荐返回了有效结果，需要继续调用评价工具
            try:
                # 检查结果是否包含有效的酒店信息
                if "酒店" in result and ("位置" in result or "价格" in result):
                    return True
                # 检查是否是空结果
                if "没有找到" in result or "暂时没有" in result or len(result.strip()) < 20:
                    return False
            except:
                pass
            return False
        elif function_name == "search_travel_guide":
            # 如果旅行攻略返回了有效结果，需要继续调用天气工具
            try:
                if "未找到" in result or "不可用" in result or len(result.strip()) < 50:
                    return False
                return True
            except:
                pass
            return False
        else:
            return False
    
    def call_function(self, function_name: str, arguments: dict) -> str:
        """调用函数"""
        if function_name == "search_travel_guide":
            return self.search_travel_guide(
                arguments.get("query"),
                arguments.get("search_type", "hybrid")
            )
        elif function_name == "get_weather_info":
            return self.get_weather_info(
                arguments.get("location"),
                arguments.get("start_date"),
                arguments.get("num_days", 1)
            )
        elif function_name == "query_route":
            return self.query_route(
                arguments.get("start_location"),
                arguments.get("end_location"),
                arguments.get("city_code", "110000")
            )
        elif function_name == "recommend_hotels":
            return self.recommend_hotels(arguments.get("requirements"))
        elif function_name == "get_hotel_reviews":
            return self.get_hotel_reviews_func(arguments.get("hotel_name"))
        else:
            return f"未知函数: {function_name}"
    
    def process_user_input(self, user_input: str) -> str:
        """处理用户输入"""
        # 添加用户输入到对话历史
        self.add_to_history("user", user_input)
        
        # 构建消息列表
        user_info_text = f"""
## 用户信息
- 用户名: {self.user_info['name']}
- 当前城市ID: {self.user_info['city_id']}
- 出发日期: {self.user_info['travel_date_range']}
- 起点坐标: {self.user_info['start_coordinates']}
- 当前日期: {self.user_info['current_date']}

请在处理用户请求时考虑这些信息，比如：
- 问路时如果没有明确起点，使用起点坐标{self.user_info['start_coordinates']}
- 旅行规划时根据用户的出发日期范围提供建议
- 天气查询时根据旅行攻略中的天数来确定查询天数，使用时间段查询
- 路线查询时起点优先使用起点坐标
"""

        messages = [
            {
                "role": "system", 
                "content": user_info_text + """
你是一个专业的旅行助手，严格按照以下工作流程处理用户请求：

## 工作流1: 旅行规划
**触发条件**: 用户想制定旅行计划、询问某地旅游攻略、景点推荐等
**处理流程**:
1. 从用户输入中提取目的地信息：
   - 如果用户说"北京怎么玩"、"去上海玩什么"、"成都有什么好玩的"，直接识别城市名作为目的地
   - 如果用户问"附近有什么好玩的"、"本地旅游"，使用用户当前城市作为目的地
   - 只有当完全无法从输入中识别目的地时，才反问："请告诉我您想去哪个城市旅行？"
2. 如果有明确的目的地，检查是否有出行日期
   - 如果没有明确日期，可以基于用户的旅行日期范围{self.user_info['travel_date_range']}提供建议
   - 完全没有时间信息也可以继续，使用用户设置的默认日期
3. 有目的地信息后，必须**按照顺序**调用以下两个工具：
   - `search_travel_guide`: 搜索目的地旅行攻略（传递用户的完整查询内容，如"成都怎么玩"）
   - `get_weather_info`: 查询出行日期的天气信息（如果攻略查询成功）
4. 综合天气和攻略信息，制定详细的旅行计划。如果search_travel_guide返回结果为空，则不调用天气工具，直接返回"暂时没有找到该城市的旅行攻略"
5、在工作流1最终仅需要输出每天规划+天气信息即可，不需要输出预算、贴士、酒店、餐厅等内容

## 工作流2: 问路/地图导航
**触发条件**: 用户询问路线、问路、导航、"怎么走"、"如何到达"等
**处理流程**:
1. 检查起点和终点信息，起点信息在起点坐标获得，无需询问，也无需询问城市，城市就是当前城市ID
   - 如果用户说"从X到Y"、"X到Y怎么走"，则X是起点，Y是终点，直接调用工具，如果说了火车站、医院等公共设施的信息则无需追问，直接调用工具查询即可
   - 如果用户说"怎么回家"，可以提醒用户提供具体地址
   - 如果没有明确的终点，必须反问："请问您要去哪里？"
2. 信息完整后，调用`query_route`工具获取路线
3. 为用户提供步行、公交、驾车等多种路线选择，如果query_route这个工具返回的结果为空，则直接返回查询不到对应路线

## 工作流3: 酒店查询
**触发条件**: 用户询问酒店推荐、酒店预订、住宿等
**处理流程**:
### 3A: 酒店推荐
1. 检查必要信息：目的地、预算、入住时间、特殊需求（如果用户说了城市，就不需要再追问了，调用查询工具查询即可，追问一定只有一轮，只要有了城市信息，就要触发工具调用）
   - 缺少目的地：反问"请问您要在哪个城市找酒店？"
   - 如果用户说"本地酒店"或"附近酒店"，使用当前城市{self.user_info['current_city']}
   - 缺少预算：反问"请问您的预算范围是多少？"
   - 可选信息：入住时间、房型偏好、特殊设施需求
2. 信息收集完毕后，**必须按顺序执行**：
   - 第一步：调用`recommend_hotels`工具获取酒店推荐
   - 第二步：**立即**为推荐的酒店调用`get_hotel_reviews`工具获取评价
   - **重要**：不要在第一步后就返回结果，必须完成所有工具调用，如果第一步没有推荐结果，则直接返回"暂时没有找到符合您需求的酒店推荐"，无需进行第二步工具调用
3. 整合酒店信息和评价，生成完整的推荐结果（包含酒店详情+用户评价）

### 3B: 酒店评价查询
**触发条件**: 询问某酒店"怎么样"、"评价"、"好不好"等
1. 提取酒店名称
   - 如果没有明确酒店名称，反问："请问您想了解哪家酒店的评价？"
2. 调用`get_hotel_reviews`获取评价信息

## 工作流4: 闲聊
**触发条件**: 旅行相关的一般性问题、打招呼等
**处理流程**:
1. 判断是否与旅行相关
   - 如果是旅行相关话题，直接回答，不调用工具
   - 如果完全无关（如数学、编程等），礼貌拒绝："抱歉，我是专门的旅行助手，只能回答旅行相关的问题。"

## 重要原则:
1. **信息不足时必须反问，不要猜测**
2. **一次只问一个关键信息，避免一次问太多，一定只追问一次，用户不管怎么回答，都只追问一次。用户回答后开始调用工具，或者生成回复**
3. **工具调用顺序很重要，旅行规划时必须先调用攻略，再根据返回情况决定是否调用天气**
4. **酒店推荐工作流特别重要**：
   - 先调用`recommend_hotels`获取酒店列表
   - 然后为推荐酒店调用`get_hotel_reviews`
   - 最后整合所有信息统一回复
   - 绝不在获得酒店推荐后立即回复，必须获取评价后才能给最终答案
5. **非旅行相关问题要礼貌拒绝**

## 反问示例:
- "请告诉我您想去哪个城市旅行？"
- "请问您计划什么时候出行？（请提供具体日期）"
- "请问您要去哪里？"
- "请问您要在哪个城市找酒店？"
- "请问您的预算范围是多少？"

严格按照以上流程处理用户请求，确保信息完整后再调用相应工具。"""
            }
        ]
        
        # 添加对话历史
        messages.extend(self.conversation_history)
        
        try:
            # 第一轮调用：检查是否需要工具调用
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # 如果不需要工具调用，直接返回
            if not message.tool_calls:
                content = message.content
                self.add_to_history("assistant", content)
                return content
            
            # 处理工具调用
            tool_calls_info = []
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                print(f"🔧 调用工具: {function_name}")
                print(f"参数: {arguments}")
                
                # 调用工具并记录结果
                result = self.call_function(function_name, arguments)
                print(f"🔧 工具结果: {result[:200]}{'...' if len(result) > 200 else ''}")
                
                tool_calls_info.append({
                    "call": tool_call,
                    "result": result,
                    "should_continue": self._should_continue_tool_chain(function_name, result)
                })
            
            # 将第一轮工具调用添加到messages
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [{
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments
                    }
                } for tool_call in message.tool_calls]
            })
            
            # 添加工具结果
            for info in tool_calls_info:
                messages.append({
                    "role": "tool",
                    "tool_call_id": info["call"].id,
                    "content": info["result"]
                })
            
            # 决定是否需要继续调用工具
            needs_more_tools = any(info["should_continue"] for info in tool_calls_info)
            
            if needs_more_tools:
                # 第二轮调用：可能触发更多工具调用
                second_response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto"
                )
                
                second_message = second_response.choices[0].message
                
                if second_message.tool_calls:
                    # 处理第二轮工具调用
                    for tool_call in second_message.tool_calls:
                        function_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        print(f"🔧 继续调用工具: {function_name}")
                        print(f"参数: {arguments}")
                        
                        result = self.call_function(function_name, arguments)
                        print(f"🔧 工具结果: {result[:200]}{'...' if len(result) > 200 else ''}")
                    
                    # 添加第二轮工具调用到messages
                    messages.append({
                        "role": "assistant",
                        "content": second_message.content,
                        "tool_calls": [{
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        } for tool_call in second_message.tool_calls]
                    })
                    
                    # 添加第二轮工具结果
                    for tool_call in second_message.tool_calls:
                        function_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        result = self.call_function(function_name, arguments)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result
                        })
            
            # 最终调用：生成最终回复
            final_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            
            final_content = final_response.choices[0].message.content
            self.add_to_history("assistant", final_content)
            
            return final_content
                
        except Exception as e:
            error_msg = f"处理请求时出错: {e}"
            self.add_to_history("assistant", error_msg)
            return error_msg


def main():
    """主函数 - 交互式对话"""
    print("🌍 欢迎使用智能旅行助手！")
    print("我可以帮您：")
    print("1. 制定旅行计划（会自动查询天气和攻略）")
    print("2. 查询路线（问路导航）")
    print("3. 推荐酒店和查看评价")
    print("4. 回答旅行相关问题")
    
    # 获取用户信息
    user_name = input("\n请输入您的姓名（默认：旅行者）：").strip() or "旅行者"
    user_city_input = input("请输入您所在的城市（默认：北京）：").strip() or "北京"
    
    # 城市ID映射
    city_id_map = {
        "北京": "101010100", "上海": "101020100", "广州": "101280101",
        "深圳": "101280601", "杭州": "101210101", "南京": "101190101"
    }
    user_city_id = city_id_map.get(user_city_input, "101010100")
    
    travel_range = input("请输入出发日期范围（默认：2025-09-15~2025-10-05）：").strip() or "2025-09-15~2025-10-05"
    start_coords = input("请输入起点坐标（默认：116.481028,39.989643）：").strip() or "116.481028,39.989643"
    
    print(f"✅ 用户信息设置完成:")
    print(f"   姓名: {user_name}")
    print(f"   城市: {user_city_input} (ID: {user_city_id})")
    print(f"   出发范围: {travel_range}")
    print(f"   起点坐标: {start_coords}")
    print("输入 'quit' 或 'exit' 退出\n")
    
    assistant = TravelAssistantFuncCall(
        user_name=user_name,
        user_city_id=user_city_id,
        travel_date_range=travel_range,
        start_coordinates=start_coords
    )
    
    while True:
        try:
            user_input = input("您: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出', '再见']:
                print("🌍 感谢使用旅行助手，祝您旅途愉快！")
                break
            
            if not user_input:
                continue
            
            print("\n正在处理您的请求...")
            response = assistant.process_user_input(user_input)
            print(f"\n助手: {response}\n")
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\n\n🌍 感谢使用旅行助手，祝您旅途愉快！")
            break
        except Exception as e:
            print(f"\n❌ 出现错误: {e}")
            print("请重新输入您的问题。\n")


if __name__ == "__main__":
    main()