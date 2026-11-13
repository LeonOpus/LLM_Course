import requests
from datetime import datetime

API_HOST = "https://nk4d92xupx.re.qweatherapi.com"
API_KEY = ""

def get_weather_by_date_range(location: str, start_date: str, num_days: int, query_range: str = "30d"):
    """
    查询指定地点和时间段的天气情况

    :param location: 地点 (城市ID如 101010100，或 '116.41,39.92')
    :param start_date: 开始日期 (格式 'YYYY-MM-DD')
    :param num_days: 查询天数（从开始日期算起几天）
    :param query_range: API查询范围，可选: 3d / 7d / 10d / 15d / 30d，默认30d
    :return: 时间段内的天气情况列表（list of dict），未找到则返回 []
    """
    from datetime import datetime, timedelta
    
    url = f"{API_HOST}/v7/weather/{query_range}"
    params = {"location": location, "key": API_KEY}
    resp = requests.get(url, params=params)
    data = resp.json()

    if "daily" not in data:
        print("❌ 未获取到天气数据:", data)
        return []

    # 计算目标日期范围
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    target_dates = []
    for i in range(num_days):
        target_date = start_dt + timedelta(days=i)
        target_dates.append(target_date.strftime("%Y-%m-%d"))

    # 收集目标时间段内的天气数据
    weather_list = []
    for d in data["daily"]:
        if d["fxDate"] in target_dates:
            weather_info = {
                "日期": d["fxDate"],
                "日出": d["sunrise"],
                "日落": d["sunset"],
                "白天天气": d["textDay"],
                "夜间天气": d["textNight"],
                "最高温": d["tempMax"] + "℃",
                "最低温": d["tempMin"] + "℃",
            }
            weather_list.append(weather_info)
    
    # 按日期排序
    weather_list.sort(key=lambda x: x["日期"])
    return weather_list


def get_weather_by_date(location: str, date: str, days: str = "30d"):
    """
    查询指定地点和日期的天气情况（兼容原有接口）

    :param location: 地点 (城市ID如 101010100，或 '116.41,39.92')
    :param date: 日期 (格式 'YYYY-MM-DD')
    :param days: 预报天数，可选: 3d / 7d / 10d / 15d / 30d
    :return: 当日天气情况（dict），未找到则返回 None
    """
    weather_list = get_weather_by_date_range(location, date, 1, days)
    return weather_list[0] if weather_list else None


# 示例调用
if __name__ == "__main__":
    result = get_weather_by_date("101010100", "2025-09-19")
    if result:
        for k, v in result.items():
            print(f"{k}: {v}")
    else:
        print("未找到对应日期的天气数据")


