"""
Deep Research Agent 种子问题 V2
================================

设计原则：
1. 问题具有真实性和实用性，模拟对公客户经理的咨询场景
2. 覆盖 4 行业 × 6 问题类型 = 24 种组合
3. 每个问题设计时考虑需要的工具链和多步骤能力
4. 问题复杂度分级：简单(1步)、中等(2步)、复杂(3+步)
"""

from typing import Dict, List

# =============================================================================
# 种子问题定义
# =============================================================================

SEED_QUESTIONS: List[Dict] = [
    # =========================================================================
    # 金融行业 (finance)
    # =========================================================================

    # 政策法规 (policy)
    {
        "id": "finance_policy_001",
        "question": "最近央行对小微企业贷款有什么新政策？我们银行想调整普惠金融产品。",
        "industry": "finance",
        "question_type": "policy",
        "complexity": "medium",  # search → finish
        "expected_tools": ["search", "finish"],
        "key_points": ["央行政策", "普惠金融", "贷款利率", "考核指标"]
    },
    {
        "id": "finance_policy_002",
        "question": "2025年跨境支付有什么新规定？我们有客户做外贸需要了解。",
        "industry": "finance",
        "question_type": "policy",
        "complexity": "complex",  # search → visit → finish
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["外汇管理", "跨境支付", "反洗钱", "申报要求"]
    },

    # 市场分析 (market)
    {
        "id": "finance_market_001",
        "question": "供应链金融市场现在规模有多大？未来几年的增长趋势怎么样？",
        "industry": "finance",
        "question_type": "market",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["市场规模", "增长率", "渗透率", "发展趋势"]
    },
    {
        "id": "finance_market_002",
        "question": "消费金融行业目前的坏账率情况如何？不同平台之间有什么差异？",
        "industry": "finance",
        "question_type": "market",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["坏账率", "不良贷款", "风控水平", "行业对比"]
    },

    # 竞争情报 (competitor)
    {
        "id": "finance_competitor_001",
        "question": "微众银行的小微企业贷款产品有什么特点？和我们传统银行相比有什么优势？",
        "industry": "finance",
        "question_type": "competitor",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["产品特点", "利率", "申请流程", "风控模式"]
    },
    {
        "id": "finance_competitor_002",
        "question": "蚂蚁集团的网商贷和京东金融的京东金条，在小微企业服务上有什么差异？",
        "industry": "finance",
        "question_type": "competitor",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["产品对比", "服务模式", "客户定位", "技术优势"]
    },

    # 数据计算 (calculation)
    {
        "id": "finance_calculation_001",
        "question": "一家企业想贷款500万，年化利率5.6%，分3年等额本息还款，每月需要还多少？总利息是多少？",
        "industry": "finance",
        "question_type": "calculation",
        "complexity": "simple",
        "expected_tools": ["calculator", "finish"],
        "key_points": ["月供计算", "总利息", "还款计划"]
    },
    {
        "id": "finance_calculation_002",
        "question": "客户企业年营收2000万，净利润率8%，想申请流动资金贷款。按照银行通常的授信倍数(净利润的3-5倍)，大概能贷多少？",
        "industry": "finance",
        "question_type": "calculation",
        "complexity": "simple",
        "expected_tools": ["calculator", "finish"],
        "key_points": ["净利润计算", "授信额度", "风险评估"]
    },

    # 风险评估 (risk)
    {
        "id": "finance_risk_001",
        "question": "一家做房地产中介的小微企业申请贷款，现在这个行业有什么风险需要关注？",
        "industry": "finance",
        "question_type": "risk",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["行业风险", "政策风险", "市场风险", "经营风险"]
    },
    {
        "id": "finance_risk_002",
        "question": "P2P清退后，很多借款人征信受损，如果这类客户来申请贷款，应该怎么评估风险？",
        "industry": "finance",
        "question_type": "risk",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["征信评估", "还款能力", "担保措施", "风控策略"]
    },

    # 扩张建议 (expansion)
    {
        "id": "finance_expansion_001",
        "question": "我们银行想拓展新能源汽车供应链金融业务，应该从哪些环节切入？",
        "industry": "finance",
        "question_type": "expansion",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["产业链分析", "核心企业", "融资需求", "业务模式"]
    },
    {
        "id": "finance_expansion_002",
        "question": "县域市场的普惠金融该怎么做？有什么成功的案例可以参考？",
        "industry": "finance",
        "question_type": "expansion",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["县域金融", "普惠模式", "成功案例", "实施策略"]
    },

    # =========================================================================
    # 餐饮行业 (catering)
    # =========================================================================

    # 政策法规 (policy)
    {
        "id": "catering_policy_001",
        "question": "餐饮行业最近有什么食品安全方面的新规定？我们客户开连锁餐厅需要注意什么？",
        "industry": "catering",
        "question_type": "policy",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["食品安全法", "卫生许可", "进货查验", "明厨亮灶"]
    },
    {
        "id": "catering_policy_002",
        "question": "外卖平台佣金最近有没有政策限制？商家能从中获得什么保护？",
        "industry": "catering",
        "question_type": "policy",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["平台佣金", "反垄断", "商家权益", "监管政策"]
    },

    # 市场分析 (market)
    {
        "id": "catering_market_001",
        "question": "预制菜市场现在发展得怎么样？对传统餐饮企业有什么影响？",
        "industry": "catering",
        "question_type": "market",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["市场规模", "增长趋势", "消费场景", "企业布局"]
    },
    {
        "id": "catering_market_002",
        "question": "咖啡市场目前的竞争格局是怎样的？瑞幸和库迪的价格战对行业有什么影响？",
        "industry": "catering",
        "question_type": "market",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["市场格局", "价格竞争", "盈利模式", "行业影响"]
    },

    # 竞争情报 (competitor)
    {
        "id": "catering_competitor_001",
        "question": "海底捞最近的经营状况怎么样？它的服务模式还有竞争力吗？",
        "industry": "catering",
        "question_type": "competitor",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["财务状况", "门店数量", "服务特色", "竞争优势"]
    },
    {
        "id": "catering_competitor_002",
        "question": "霸王茶姬和喜茶在新式茶饮市场的定位有什么不同？各自的优势是什么？",
        "industry": "catering",
        "question_type": "competitor",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["品牌定位", "产品策略", "门店分布", "目标客群"]
    },

    # 数据计算 (calculation)
    {
        "id": "catering_calculation_001",
        "question": "开一家100平米的奶茶店，如果月租金2万，人工4万，物料成本占营收40%，日均需要多少营业额才能保本？",
        "industry": "catering",
        "question_type": "calculation",
        "complexity": "simple",
        "expected_tools": ["calculator", "finish"],
        "key_points": ["盈亏平衡", "固定成本", "变动成本", "日均营业额"]
    },
    {
        "id": "catering_calculation_002",
        "question": "一家火锅店单桌翻台3次，客单价150元，有50张桌子。如果毛利率60%，租金占15%，人工占20%，月净利润大概多少？",
        "industry": "catering",
        "question_type": "calculation",
        "complexity": "simple",
        "expected_tools": ["calculator", "finish"],
        "key_points": ["营收计算", "成本结构", "净利润", "经营效率"]
    },

    # 风险评估 (risk)
    {
        "id": "catering_risk_001",
        "question": "网红餐厅投资有什么风险？我们有客户想加盟一个网红品牌。",
        "industry": "catering",
        "question_type": "risk",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["品牌生命周期", "加盟陷阱", "选址风险", "运营风险"]
    },
    {
        "id": "catering_risk_002",
        "question": "中央厨房投资建设有哪些风险点？食品安全和资金方面分别需要注意什么？",
        "industry": "catering",
        "question_type": "risk",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["建设投资", "食品安全", "供应链风险", "经营风险"]
    },

    # 扩张建议 (expansion)
    {
        "id": "catering_expansion_001",
        "question": "一家地方小吃品牌想走出本地市场，应该怎么规划扩张路径？",
        "industry": "catering",
        "question_type": "expansion",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["市场选择", "标准化", "供应链", "品牌建设"]
    },
    {
        "id": "catering_expansion_002",
        "question": "传统中餐企业想做数字化转型，有什么成功案例？应该从哪些方面入手？",
        "industry": "catering",
        "question_type": "expansion",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["数字化方向", "成功案例", "实施路径", "投入产出"]
    },

    # =========================================================================
    # 创业行业 (startup)
    # =========================================================================

    # 政策法规 (policy)
    {
        "id": "startup_policy_001",
        "question": "科技型中小企业现在有什么税收优惠政策？研发费用加计扣除比例是多少？",
        "industry": "startup",
        "question_type": "policy",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["税收优惠", "研发加计扣除", "认定条件", "申报流程"]
    },
    {
        "id": "startup_policy_002",
        "question": "大学生创业有什么补贴政策？创业失败后贷款怎么处理？",
        "industry": "startup",
        "question_type": "policy",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["创业补贴", "创业贷款", "失败保障", "社保补贴"]
    },

    # 市场分析 (market)
    {
        "id": "startup_market_001",
        "question": "现在AI创业赛道有哪些热门方向？投资人比较看好什么类型的项目？",
        "industry": "startup",
        "question_type": "market",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["热门赛道", "投资趋势", "估值水平", "竞争格局"]
    },
    {
        "id": "startup_market_002",
        "question": "硬科技创业（芯片、新材料）目前的融资环境怎么样？和互联网项目相比有什么不同？",
        "industry": "startup",
        "question_type": "market",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["融资环境", "估值逻辑", "投资周期", "退出渠道"]
    },

    # 竞争情报 (competitor)
    {
        "id": "startup_competitor_001",
        "question": "国内做大模型的创业公司有哪些？它们和OpenAI相比有什么差距？",
        "industry": "startup",
        "question_type": "competitor",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["主要玩家", "技术路线", "融资情况", "产品落地"]
    },
    {
        "id": "startup_competitor_002",
        "question": "低空经济（无人机配送）领域现在有哪些代表性企业？它们的商业模式是什么？",
        "industry": "startup",
        "question_type": "competitor",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["代表企业", "商业模式", "技术壁垒", "政策环境"]
    },

    # 数据计算 (calculation)
    {
        "id": "startup_calculation_001",
        "question": "一个创业项目融资500万出让20%股份，公司估值是多少？如果下轮融资1000万出让10%，估值增长了多少？",
        "industry": "startup",
        "question_type": "calculation",
        "complexity": "simple",
        "expected_tools": ["calculator", "finish"],
        "key_points": ["估值计算", "股权稀释", "融资进展"]
    },
    {
        "id": "startup_calculation_002",
        "question": "SaaS公司月收入50万，获客成本(CAC)5000元，客户生命周期价值(LTV)20000元，LTV/CAC比值健康吗？",
        "industry": "startup",
        "question_type": "calculation",
        "complexity": "simple",
        "expected_tools": ["calculator", "finish"],
        "key_points": ["SaaS指标", "LTV/CAC", "健康标准", "优化建议"]
    },

    # 风险评估 (risk)
    {
        "id": "startup_risk_001",
        "question": "投资一个种子期的AI创业项目，主要有哪些风险需要考虑？",
        "industry": "startup",
        "question_type": "risk",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["技术风险", "市场风险", "团队风险", "资金风险"]
    },
    {
        "id": "startup_risk_002",
        "question": "一家做跨境电商的创业公司想申请贷款，这个行业目前有什么特殊风险？",
        "industry": "startup",
        "question_type": "risk",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["政策风险", "汇率风险", "平台风险", "库存风险"]
    },

    # 扩张建议 (expansion)
    {
        "id": "startup_expansion_001",
        "question": "一家做企业服务SaaS的创业公司，从北京向其他城市扩张应该怎么规划？",
        "industry": "startup",
        "question_type": "expansion",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["市场选择", "销售模式", "服务体系", "成本控制"]
    },
    {
        "id": "startup_expansion_002",
        "question": "创业公司什么时候应该考虑国际化？出海东南亚和欧美有什么不同？",
        "industry": "startup",
        "question_type": "expansion",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["出海时机", "市场选择", "本地化策略", "合规要求"]
    },

    # =========================================================================
    # 智慧交通行业 (smart_transport)
    # =========================================================================

    # 政策法规 (policy)
    {
        "id": "transport_policy_001",
        "question": "自动驾驶商业化运营目前有什么政策规定？哪些城市已经开放了？",
        "industry": "smart_transport",
        "question_type": "policy",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["试点城市", "运营资质", "安全要求", "责任划分"]
    },
    {
        "id": "transport_policy_002",
        "question": "新能源物流车有什么补贴政策？城市配送方面有没有特殊的路权优惠？",
        "industry": "smart_transport",
        "question_type": "policy",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["购置补贴", "运营补贴", "路权优惠", "充电设施"]
    },

    # 市场分析 (market)
    {
        "id": "transport_market_001",
        "question": "智慧停车市场现在规模有多大？停车位缺口有多少？",
        "industry": "smart_transport",
        "question_type": "market",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["市场规模", "停车缺口", "智能化率", "商业模式"]
    },
    {
        "id": "transport_market_002",
        "question": "网约车市场的竞争格局怎么样？滴滴之外还有哪些主要玩家？",
        "industry": "smart_transport",
        "question_type": "market",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["市场份额", "主要玩家", "盈利情况", "发展趋势"]
    },

    # 竞争情报 (competitor)
    {
        "id": "transport_competitor_001",
        "question": "蔚来和理想的换电/充电策略有什么不同？各自的优劣势是什么？",
        "industry": "smart_transport",
        "question_type": "competitor",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["技术路线", "成本对比", "用户体验", "网络布局"]
    },
    {
        "id": "transport_competitor_002",
        "question": "华为和百度在智能驾驶解决方案上有什么区别？它们的主要客户分别是谁？",
        "industry": "smart_transport",
        "question_type": "competitor",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["技术方案", "合作车企", "市场定位", "商业模式"]
    },

    # 数据计算 (calculation)
    {
        "id": "transport_calculation_001",
        "question": "一辆新能源货车购置价30万，每天跑200公里，电费比油费省多少？多久能收回多花的购车成本？",
        "industry": "smart_transport",
        "question_type": "calculation",
        "complexity": "simple",
        "expected_tools": ["calculator", "finish"],
        "key_points": ["能源成本", "回收周期", "运营效率"]
    },
    {
        "id": "transport_calculation_002",
        "question": "建设一个10个桩位的充电站，投资大概需要多少？日均充电多少度才能实现盈利？",
        "industry": "smart_transport",
        "question_type": "calculation",
        "complexity": "medium",
        "expected_tools": ["search", "calculator", "finish"],
        "key_points": ["建设成本", "运营成本", "盈亏平衡", "投资回报"]
    },

    # 风险评估 (risk)
    {
        "id": "transport_risk_001",
        "question": "投资一家做城市配送的物流创业公司，主要风险点有哪些？",
        "industry": "smart_transport",
        "question_type": "risk",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["运营风险", "政策风险", "竞争风险", "人员风险"]
    },
    {
        "id": "transport_risk_002",
        "question": "自动驾驶卡车公司的投资风险主要有哪些？技术成熟度和商业化路径怎么评估？",
        "industry": "smart_transport",
        "question_type": "risk",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["技术风险", "政策风险", "商业化挑战", "资金需求"]
    },

    # 扩张建议 (expansion)
    {
        "id": "transport_expansion_001",
        "question": "一家做智慧公交的企业想从一线城市拓展到二三线，应该怎么调整策略？",
        "industry": "smart_transport",
        "question_type": "expansion",
        "complexity": "medium",
        "expected_tools": ["search", "finish"],
        "key_points": ["市场差异", "产品适配", "成本控制", "政府关系"]
    },
    {
        "id": "transport_expansion_002",
        "question": "车路协同(V2X)企业的发展路径应该怎么规划？先做哪些场景比较容易落地？",
        "industry": "smart_transport",
        "question_type": "expansion",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["应用场景", "技术路线", "商业模式", "政策机遇"]
    },

    # =========================================================================
    # 跨行业复杂问题 (综合/多步骤)
    # =========================================================================
    {
        "id": "cross_001",
        "question": "我们有个客户做餐饮连锁，想用供应链金融来优化资金周转，应该怎么设计方案？",
        "industry": "catering",  # 主行业
        "question_type": "expansion",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "calculator", "finish"],
        "key_points": ["供应链金融", "餐饮特点", "融资方案", "风控要点"]
    },
    {
        "id": "cross_002",
        "question": "一家新能源汽车充电桩运营商想申请贷款扩张，我们应该从哪些维度评估它的信用风险？",
        "industry": "smart_transport",
        "question_type": "risk",
        "complexity": "complex",
        "expected_tools": ["search", "visit", "finish"],
        "key_points": ["行业分析", "经营指标", "现金流", "抵押物"]
    },
]


# =============================================================================
# 辅助函数
# =============================================================================

def get_questions_by_industry(industry: str) -> List[Dict]:
    """获取指定行业的所有问题"""
    return [q for q in SEED_QUESTIONS if q["industry"] == industry]


def get_questions_by_type(question_type: str) -> List[Dict]:
    """获取指定类型的所有问题"""
    return [q for q in SEED_QUESTIONS if q["question_type"] == question_type]


def get_questions_by_complexity(complexity: str) -> List[Dict]:
    """获取指定复杂度的所有问题"""
    return [q for q in SEED_QUESTIONS if q["complexity"] == complexity]


def get_question_by_id(question_id: str) -> Dict:
    """根据ID获取问题"""
    for q in SEED_QUESTIONS:
        if q["id"] == question_id:
            return q
    return None


def print_statistics():
    """打印种子问题统计信息"""
    print("=" * 60)
    print("种子问题统计")
    print("=" * 60)
    print(f"总问题数: {len(SEED_QUESTIONS)}")

    # 按行业统计
    print("\n按行业:")
    industries = {}
    for q in SEED_QUESTIONS:
        ind = q["industry"]
        industries[ind] = industries.get(ind, 0) + 1
    for ind, count in sorted(industries.items()):
        print(f"  {ind}: {count}")

    # 按问题类型统计
    print("\n按问题类型:")
    types = {}
    for q in SEED_QUESTIONS:
        t = q["question_type"]
        types[t] = types.get(t, 0) + 1
    for t, count in sorted(types.items()):
        print(f"  {t}: {count}")

    # 按复杂度统计
    print("\n按复杂度:")
    complexities = {}
    for q in SEED_QUESTIONS:
        c = q["complexity"]
        complexities[c] = complexities.get(c, 0) + 1
    for c, count in sorted(complexities.items()):
        print(f"  {c}: {count}")

    # 行业×类型矩阵覆盖
    print("\n行业×类型覆盖矩阵:")
    matrix = {}
    for q in SEED_QUESTIONS:
        key = (q["industry"], q["question_type"])
        matrix[key] = matrix.get(key, 0) + 1

    industries_list = ["finance", "catering", "startup", "smart_transport"]
    types_list = ["policy", "market", "competitor", "calculation", "risk", "expansion"]

    print("         " + "  ".join([t[:6].ljust(6) for t in types_list]))
    for ind in industries_list:
        row = [str(matrix.get((ind, t), 0)).center(6) for t in types_list]
        print(f"{ind[:8].ljust(8)} " + "  ".join(row))


if __name__ == "__main__":
    print_statistics()

    print("\n" + "=" * 60)
    print("示例问题预览")
    print("=" * 60)
    for q in SEED_QUESTIONS[:5]:
        print(f"\n[{q['id']}]")
        print(f"问题: {q['question']}")
        print(f"行业: {q['industry']} | 类型: {q['question_type']} | 复杂度: {q['complexity']}")
        print(f"预期工具: {q['expected_tools']}")
