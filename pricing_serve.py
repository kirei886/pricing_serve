from mcp.server.fastmcp import FastMCP

# 初始化 FastMCP 服务器
# 这里的名称会显示在 AI 客户端的工具列表中
mcp = FastMCP("TransportPricingServer")

@mcp.tool()
def calculate_single_trip(
    distance: float, 
    is_out_of_city: bool, 
    base_price: float, 
    mileage_rate: float, 
    out_of_city_base_price: float = 0.0
) -> str:
    """
    计算单程报价。
    :param distance: 行程里程 (KM)
    :param is_out_of_city: 终点是否在市外 (True/False)
    :param base_price: 市内起步价
    :param mileage_rate: 里程费单价 (元/KM)
    :param out_of_city_base_price: 市外起步价 (跨市时使用)
    """
    if distance > 100 and is_out_of_city:
        price = out_of_city_base_price + (distance - 100) * mileage_rate
        return f"【单程-跨市长途】报价: {price:.2f} 元 (计算: 市外起步价 + 超出100km部分的里程费)"
    elif distance > 20:
        price = base_price + (distance - 20) * mileage_rate
        return f"【单程-普通】报价: {price:.2f} 元 (计算: 起步价 + 超出20km部分的里程费)"
    else:
        price = base_price
        return f"【单程-短途】报价: {price:.2f} 元 (计算: 仅收起步价，里程<=20KM)"

@mcp.tool()
def calculate_sameday_return(
    time_hours: float,
    distance: float,
    is_out_of_city: bool,
    base_price: float,
    price_4h: float,
    price_8h: float,
    overtime_fee: float = 0.0,
    overdistance_fee: float = 0.0
) -> str:
    """
    计算当天往返报价。
    :param time_hours: 用车时间(小时)
    :param distance: 总里程(KM)
    :param is_out_of_city: 终点是否在市外
    :param base_price: 基础起步价
    :param price_4h: 4小时包车基本价
    :param price_8h: 8小时包车基本价
    :param overtime_fee: 超时费总额 (若无则填0)
    :param overdistance_fee: 超里程费总额 (若无则填0)
    """
    if time_hours <= 4 and distance <= 50:
        return f"【当天往返-短途短时】报价: {base_price:.2f} 元 (计算: 仅收起步价)"
    
    if distance > 100 and is_out_of_city:
        price = price_8h + overtime_fee + overdistance_fee
        return f"【当天往返-跨市长途】报价: {price:.2f} 元 (计算: 8小时基本价 + 超时费 + 超里程费)"
    
    # 超时或超里程的情况，取 4小时套餐和8小时套餐的最小值
    cost_4h_plan = price_4h + overtime_fee + overdistance_fee
    cost_8h_plan = price_8h + overtime_fee + overdistance_fee
    
    if cost_4h_plan <= cost_8h_plan:
        return f"【当天往返-超时/超里程】报价: {cost_4h_plan:.2f} 元 (计算: 采用4小时套餐更划算)"
    else:
        return f"【当天往返-超时/超里程】报价: {cost_8h_plan:.2f} 元 (计算: 采用8小时套餐更划算)"

@mcp.tool()
def calculate_charter_daily(
    days: int,
    price_8h_per_day: float,
    total_overtime_fee: float = 0.0,
    total_overdistance_fee: float = 0.0
) -> str:
    """
    计算包天报价（支持单日或多日）。
    :param days: 包天总天数
    :param price_8h_per_day: 每天的8小时基本价
    :param total_overtime_fee: 所有天数累加的超时费
    :param total_overdistance_fee: 所有天数累加的超里程费
    """
    base_total = days * price_8h_per_day
    total_price = base_total + total_overtime_fee + total_overdistance_fee
    return f"【包天】报价: {total_price:.2f} 元 (计算: {days}天基本价 + 总超时费 + 总超里程费)"

@mcp.tool()
def calculate_nextday_return(
    charter_daily_price: float,
    waiting_days: int,
    driving_days: int,
    single_trip_total: float,
    total_overtime_overdistance: float = 0.0
) -> str:
    """
    计算隔天往返报价。逻辑：min(∑包天一天, ∑单程)。
    :param charter_daily_price: 包天一天的基本价
    :param waiting_days: 空等待的天数（包天计算时需计入基本价）
    :param driving_days: 实际行车的天数
    :param single_trip_total: 如果按“两次单程”计算的总价
    :param total_overtime_overdistance: 包天方案中产生的超时/超里程费
    """
    # 计算包天方案总价：(行车天数 + 等待天数) * 日基本价 + 额外费用
    total_charter_days = driving_days + waiting_days
    charter_plan_price = (total_charter_days * charter_daily_price) + total_overtime_overdistance
    
    if charter_plan_price <= single_trip_total:
        return f"【隔天往返】报价: {charter_plan_price:.2f} 元 (计算: 按包天计算更划算，包含{waiting_days}天空等待期)"
    else:
        return f"【隔天往返】报价: {single_trip_total:.2f} 元 (计算: 按多次单程累加计算更划算)"

if __name__ == "__main__":
    # 启动 MCP 服务器
    mcp.run()