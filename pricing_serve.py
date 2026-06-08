import requests
from mcp.server.fastmcp import FastMCP

# 初始化 FastMCP 服务器
mcp = FastMCP("SmartTransportPricingServer")

# ==========================================
# 百度地图 API 配置
# ==========================================
BAIDU_AK = "lZ2Uv8MTsu9mV2KDHSIcLeBhsi8krMvu"  # 请替换为你的真实AK

def get_location_info(address: str):
    """
    调用百度地图API,获取地址的经纬度和所属城市
    """
    # 1. 正向地理编码：地址 -> 经纬度
    geo_url = f"https://api.map.baidu.com/geocoding/v3/?address={address}&output=json&ak={BAIDU_AK}"
    geo_res = requests.get(geo_url).json()
    
    if geo_res.get("status") != 0:
        raise ValueError(f"无法解析地址：{address},百度API返回状态码:{geo_res.get('status')}")
        
    location = geo_res["result"]["location"]
    lat, lng = location["lat"], location["lng"]
    
    # 2. 逆地理编码：经纬度 -> 详细地址信息（提取城市名）
    rev_url = f"https://api.map.baidu.com/reverse_geocoding/v3/?location={lat},{lng}&output=json&ak={BAIDU_AK}"
    rev_res = requests.get(rev_url).json()
    
    if rev_res.get("status") != 0:
        raise ValueError(f"无法获取城市信息：{address}")
        
    city = rev_res["result"]["addressComponent"]["city"]
    
    return {"lat": lat, "lng": lng, "city": city}

def get_driving_distance(lat1, lng1, lat2, lng2) -> float:
    """
    调用百度地图轻量级驾车路线规划API,获取距离（公里）
    """
    # 注意：百度API要求的坐标格式是 "纬度,经度" (lat,lng)
    direction_url = f"https://api.map.baidu.com/directionlite/v1/driving?origin={lat1},{lng1}&destination={lat2},{lng2}&ak={BAIDU_AK}"
    res = requests.get(direction_url).json()
    
    if res.get("status") != 0:
        raise ValueError(f"路线规划失败,百度API返回状态码:{res.get('status')}")
        
    # 获取第一条推荐路线的距离（单位：米）
    distance_meters = res["result"]["routes"][0]["distance"]
    
    # 转换为公里并保留两位小数
    return round(distance_meters / 1000.0, 2)

# ==========================================
# MCP 工具定义
# ==========================================

@mcp.tool()
def smart_calculate_single_trip(
    origin: str, 
    destination: str, 
    base_price: float, 
    mileage_rate: float, 
    out_of_city_base_price: float = 0.0
) -> str:
    """
    智能计算单程报价（自动调用百度地图查询里程和判断跨市）。
    :param origin: 出发地名称 (如 "杭州市西湖区黄龙体育中心")
    :param destination: 目的地名称 (如 "上海市浦东机场")
    :param base_price: 市内起步价
    :param mileage_rate: 里程费单价 (元/KM)
    :param out_of_city_base_price: 市外起步价 (跨市时使用)
    """
    
    try:
        # 1. 获取起点和终点的信息
        start_info = get_location_info(origin)
        end_info = get_location_info(destination)
        
        # 2. 判断是否跨市
        is_out_of_city = (start_info["city"] != end_info["city"])
        
        # 3. 计算实际驾车里程
        distance = get_driving_distance(
            start_info["lat"], start_info["lng"], 
            end_info["lat"], end_info["lng"]
        )
        
        # 4. 执行报价逻辑
        price = 0.0
        calc_detail = ""
        trip_type = ""
        
        if distance > 100 and is_out_of_city:
            price = out_of_city_base_price + (distance - 100) * mileage_rate
            trip_type = "单程-跨市长途"
            calc_detail = f"市外起步价({out_of_city_base_price}) + 超出100km部分({distance-100:.2f}km) * 里程费({mileage_rate})"
        elif distance > 20:
            price = base_price + (distance - 20) * mileage_rate
            trip_type = "单程-普通"
            calc_detail = f"市内起步价({base_price}) + 超出20km部分({distance-20:.2f}km) * 里程费({mileage_rate})"
        else:
            price = base_price
            trip_type = "单程-短途"
            calc_detail = f"仅收起步价({base_price})，里程<=20KM"
            
        # 5. 组装返回给 AI 的结果
        result = (
            f"📍 行程解析成功：\n"
            f"- 起点：{origin} ({start_info['city']})\n"
            f"- 终点：{destination} ({end_info['city']})\n"
            f"- 实际驾车里程：{distance} KM\n"
            f"- 是否跨市：{'是' if is_out_of_city else '否'}\n"
            f"------------------------\n"
            f"💰 报价结果：\n"
            f"- 匹配类型：【{trip_type}】\n"
            f"- 最终报价：{price:.2f} 元\n"
            f"- 计算公式：{calc_detail}"
        )
        return result

    except Exception as e:
        # 如果网络请求失败或地址找不到，把错误信息返回给 AI
        return f"调用地图数据失败，原因：{str(e)}。请让用户提供更准确的地址，或手动提供里程数。"

if __name__ == "__main__":
    mcp.run()