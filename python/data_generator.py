# -*- coding: utf-8 -*-
"""
=====================================================
 电商运营数据分析 —— 仿真业务数据生成器
=====================================================

【业务背景】
    通用内容电商平台运营数据分析项目, 覆盖 5 大一级品类:
        服饰鞋包 / 美妆个护 / 家居百货 / 食品饮料 / 3C数码
    每个一级品类下各有 5 个二级子品类, 共 25 个细分赛道。

【表间关系】(全部通过 ID 互相关联, 可复现)
    seller_info  (商家)    1─n  product_info   (商品)
    seller_info  (商家)    1─n  activity_signup(活动报名) ── 审核通过 → 直播记为"大促直播"
    seller_info  (商家)    1─n  live_record    (直播)
    product_info (商品) ──n─n── talent_match   (达人撮合) ──n─n── talent_info (达人)
    product_info (商品)    1─n  buyer_reviews  (买家秀评论)

【生成内容】(7 张表, 固定随机种子 42, 每次运行结果完全一致)
    seller_info       商家信息表     200 条
    product_info      商品信息表     1000 条
    activity_signup   活动报名表     约 270 条 (整体商家报名率 65%)
    live_record       直播记录表     约 2400 条 (最近 30 天, 日开播率 40%)
    talent_info       达人信息表     80 条
    talent_match      达人撮合表     1500 条
    buyer_reviews     买家秀评论表   5000 条

【依赖库】
    pandas / numpy / faker

【运行方式】
    python data_generator.py

【输出】
    ../data/raw/ 目录下 7 个 CSV 文件, 编码 utf-8-sig (兼容 Excel 直接打开不乱码)
"""

import os
import sys
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

# ============================================================
# 0. 全局配置
# ============================================================

RANDOM_SEED = 42                       # 固定随机种子, 保证每次运行结果完全一致
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

fake = Faker('zh_CN')                  # 中文假数据生成器 (用于生成达人昵称等人名类数据)
Faker.seed(RANDOM_SEED)

# 控制台输出统一 UTF-8, 避免 Windows GBK 控制台打印中文乱码
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# 数据参考日期 = 运行当天零点; 所有时间窗口均相对该日期推算, 保证"最近30天"数据始终新鲜
DATA_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

# 输出目录: 基于脚本自身位置推导 ../data/raw, 不写死绝对路径, 换机器可直接运行
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'data', 'raw'))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# 1. 品类体系与行业参数
# ============================================================

# 一级品类 → 二级子品类 (共 25 个细分赛道)
CATEGORY_SUB = {
    '服饰鞋包': ['女装', '男装', '女鞋', '箱包', '运动服饰'],
    '美妆个护': ['面部护肤', '彩妆', '洗发护发', '身体护理', '口腔护理'],
    '家居百货': ['厨房用品', '收纳整理', '家纺布艺', '清洁工具', '装饰摆件'],
    '食品饮料': ['休闲零食', '冲调饮品', '粮油调味', '生鲜水果', '酒水饮料'],
    '3C数码':   ['手机配件', '电脑外设', '智能穿戴', '影音设备', '摄影摄像'],
}
ALL_SUB_CATEGORIES = [sub for subs in CATEGORY_SUB.values() for sub in subs]
SUB_TO_CAT = {sub: cat for cat, subs in CATEGORY_SUB.items() for sub in subs}

# 各二级品类商品价格区间 (元) —— 贴合行业常识
PRICE_RANGE = {
    '女装': (59, 599), '男装': (69, 699), '女鞋': (89, 499), '箱包': (99, 899), '运动服饰': (79, 599),
    '面部护肤': (59, 899), '彩妆': (29, 399), '洗发护发': (29, 199), '身体护理': (19, 299), '口腔护理': (9.9, 129),
    '厨房用品': (19, 399), '收纳整理': (9.9, 199), '家纺布艺': (39, 499), '清洁工具': (9.9, 159), '装饰摆件': (15, 299),
    '休闲零食': (9.9, 99), '冲调饮品': (19, 199), '粮油调味': (15, 159), '生鲜水果': (19, 299), '酒水饮料': (29, 499),
    '手机配件': (9.9, 299), '电脑外设': (29, 699), '智能穿戴': (99, 1999), '影音设备': (59, 1599), '摄影摄像': (199, 5999),
}

# 各一级品类平均客单价 (元) —— 用于直播 GMV 仿真
CATEGORY_AOV = {
    '服饰鞋包': 180, '美妆个护': 120, '家居百货': 90, '食品饮料': 60, '3C数码': 320,
}

# 商品命名词库: 每个二级品类的核心商品词 (用于拼接商品名)
PRODUCT_KEYWORDS = {
    '女装':   ['法式连衣裙', '针织开衫', '高腰牛仔裤', '西装外套', '连帽卫衣', '半身裙', '衬衫'],
    '男装':   ['休闲夹克', '纯棉T恤', '商务衬衫', '工装裤', '连帽卫衣', '直筒牛仔裤', '风衣'],
    '女鞋':   ['小白鞋', '马丁靴', '乐福鞋', '高跟凉鞋', '老爹鞋', '玛丽珍鞋', '雪地靴'],
    '箱包':   ['托特包', '双肩背包', '斜挎小包', '行李箱', '通勤手提包', '钱包卡包', '帆布包'],
    '运动服饰': ['速干T恤', '瑜伽裤', '运动卫衣', '跑步鞋', '防晒衣', '运动短裤', '冲锋衣'],
    '面部护肤': ['保湿面霜', '精华液', '氨基酸洁面乳', '补水面膜', '爽肤水', '眼霜', '防晒霜'],
    '彩妆':   ['口红', '粉底液', '眼影盘', '眉笔', '腮红', '定妆散粉', '睫毛膏'],
    '洗发护发': ['控油洗发水', '护发素', '发膜', '护发精油', '蓬松喷雾', '去屑洗发水', '生发精华'],
    '身体护理': ['身体乳', '沐浴露', '磨砂膏', '护手霜', '香氛沐浴盐', '润肤油', '香体喷雾'],
    '口腔护理': ['电动牙刷', '美白牙膏', '漱口水', '牙线', '冲牙器', '牙膏套装', '舌苔刷'],
    '厨房用品': ['不粘锅', '电饭煲', '刀具套装', '保鲜盒', '破壁机', '砧板', '厨房置物架'],
    '收纳整理': ['收纳箱', '真空压缩袋', '衣柜分层架', '桌面收纳盒', '挂钩', '置物架', '鞋盒'],
    '家纺布艺': ['四件套', '乳胶枕', '夏凉被', '窗帘', '床垫', '毛毯', '抱枕'],
    '清洁工具': ['拖把', '扫地机器人配件', '玻璃刮', '除螨仪', '清洁剂', '抹布', '马桶刷'],
    '装饰摆件': ['花瓶', '香薰蜡烛', '挂画', '绿植盆栽', '陶瓷摆件', '相框', '氛围灯'],
    '休闲零食': ['坚果礼盒', '薯片', '辣条', '肉脯', '曲奇饼干', '果干', '巧克力'],
    '冲调饮品': ['速溶咖啡', '燕麦片', '蜂蜜柚子茶', '奶粉', '蛋白粉', '奶茶包', '豆浆粉'],
    '粮油调味': ['橄榄油', '酱油', '火锅底料', '五常大米', '拌饭酱', '香料礼盒', '蚝油'],
    '生鲜水果': ['车厘子', '苹果', '猕猴桃', '榴莲', '脐橙', '草莓', '芒果'],
    '酒水饮料': ['精酿啤酒', '气泡水', '鲜榨果汁', '白酒', '红酒', '茶饮料', '椰子水'],
    '手机配件': ['手机壳', '钢化膜', '快充充电器', '数据线', '充电宝', '手机支架', '蓝牙耳机'],
    '电脑外设': ['机械键盘', '无线鼠标', '显示器支架', 'U盘', '移动硬盘', '摄像头', '扩展坞'],
    '智能穿戴': ['智能手表', '智能手环', '蓝牙耳机', '智能眼镜', '体脂秤', '运动手表', '智能戒指'],
    '影音设备': ['蓝牙音箱', '投影仪', '回音壁', '头戴耳机', '麦克风', '电视盒子', '唱片机'],
    '摄影摄像': ['微单相机', '运动相机', '手持云台', '三脚架', '补光灯', '无人机', '镜头'],
}

# 商品名拼接词库: 品牌词 + 店铺后缀 + 修饰词 + 商品名后缀
BRAND_WORDS = ['优选', '悦享', '匠心', '素然', '慕白', '青柠', '山丘', '拾光', '暖阳', '云朵',
               '星野', '北岛', '初见', '良品', '极简', '灵动', '悠然', '原野', '拾贝', '半糖',
               '微光', '桔子', '麦田', '溪谷', '沐风', '简白', '森屿', '南栀', '青禾', '花间',
               '湖光', '晨露', '浅秋', '蜜语', '未迟', '拾荒', '白鹿', '野行', '谷雨', '清欢']
SHOP_SUFFIX = ['旗舰店', '官方店', '专营店', '工厂店', '严选店', '优选店', '自营店', '小店']
NAME_ADJ = ['轻奢', '经典', '简约', '复古', '高颜值', '限定', '人气', '爆款', '新款', '升级']
NAME_SUFFIX = ['款', '系列', '套装', '礼盒装', '升级版', '组合装']

# 活动定义: (活动ID, 活动名称, 报名开始/报名结束/活动开始/活动结束 相对 DATA_DATE 的天数)
# 业务说明: 618 已结束(留历史报名数据); 开学季活动期与近30天窗口有重叠;
#           双11 报名期尚未截止(会出现未来报名→审核中), 预售预热已启动;
#           日常招商为常态化招商, 无固定活动期
ACTIVITIES = [
    ('A001', '618大促',  -160, -140, -120, -108),
    ('A002', '开学季',   -45,  -35,  -33,  -25),
    ('A003', '双11大促', -17,  8,    -5,   25),
    ('A004', '日常招商', -90,  0,    None, None),
]

# 达人撮合漏斗状态: 状态 → (占比, 创建时间距今区间天数)
# 业务说明: 漏斗越靠后的状态创建时间越早, 符合"选品入库→意向沟通→排期确认→已开播"的推进节奏
MATCH_STATUS = {
    '选品入库': (0.20, (0, 14)),
    '意向沟通': (0.25, (5, 35)),
    '排期确认': (0.15, (15, 60)),
    '已开播':   (0.30, (25, 90)),
    '合作终止': (0.10, (40, 90)),
}

# 达人层级配置: 层级 → (数量, 粉丝量级范围, 平均ROI范围, 合作费用范围)
# 业务说明: 头部达人粉丝多但费用高、ROI 相对平稳; 中小达人坑位费低、ROI 普遍更高
TIER_CONFIG = {
    'S': (4,  (5e6, 2e7), (1.2, 2.2), (50000, 300000)),
    'A': (16, (8e5, 5e6), (1.5, 3.0), (10000, 60000)),
    'B': (28, (1e5, 8e5), (2.0, 4.0), (3000, 15000)),
    'C': (32, (1e4, 1e5), (2.5, 5.5), (500, 3000)),
}

# 买家秀评论词库: 好评/差评两套通用电商评论词
GOOD_WORDS = ['质量很好', '做工精细', '和描述完全一致', '颜值很高', '性价比超高', '物流很快',
              '包装很用心', '效果非常明显', '手感很好', '客服态度特别好']
GOOD_EXTRAS = ['家人很喜欢', '朋友看到也想要链接', '已经回购第二次了', '比实体店划算多了',
               '超出预期', '推荐入手']
BAD_WORDS = ['质量一般般', '有色差', '物流太慢了', '尺寸不太合适', '有点异味', '包装破损了',
             '做工粗糙', '和图片差距有点大', '掉色严重', '客服回复太慢']
BAD_EXTRAS = ['不推荐购买', '退货太麻烦', '有点失望', '凑合用吧', '和预期差距大']


# ============================================================
# 2. 通用工具函数
# ============================================================

def write_csv(df, filename):
    """统一写盘: utf-8-sig 编码(兼容 Excel), 不带行索引, 并打印条数"""
    path = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(path, index=False, encoding='utf-8-sig')
    print(f'  ✔ {filename:<22s} {len(df):>6,} 条 → {path}')
    return df


# ============================================================
# 3. 各表生成函数
# ============================================================

def gen_seller_info():
    """1. 商家信息表 (200 条)"""
    n = 200
    # 商家层级: 头部:腰部:尾部 = 1:3:6 → 20:60:120
    levels = np.array(['头部'] * 20 + ['腰部'] * 60 + ['尾部'] * 120)
    np.random.shuffle(levels)
    # 25 个二级品类均分 8 家商家, 保证全品类覆盖, 且与层级随机配对(消除相关性)
    sub_cats = np.array(ALL_SUB_CATEGORIES * 8)
    np.random.shuffle(sub_cats)

    # 各层级粉丝量级范围 (下限, 上限)
    fans_range = {'头部': (5e5, 3e6), '腰部': (8e4, 6e5), '尾部': (2e3, 6e4)}

    rows, used_names = [], set()
    for i in range(n):
        level, sub = levels[i], sub_cats[i]
        # 入驻时间: 头部商家多为老商家(3~5年前入驻), 尾部多为近两年新入驻
        days_ago = {
            '头部': int(np.random.uniform(1080, 1800)),
            '腰部': int(np.random.uniform(365, 1080)),
            '尾部': int(np.random.uniform(30, 730)),
        }[level]
        entry = DATA_DATE - timedelta(days=days_ago)

        # 粉丝数: 按层级对数均匀抽取 (粉丝量级跨度大, 对数分布更符合现实)
        lo, hi = fans_range[level]
        fans = int(10 ** np.random.uniform(np.log10(lo), np.log10(hi)))

        # 店铺名: 品牌词 + 店铺后缀; 出现重名时追加数字编号去重
        name = f"{np.random.choice(BRAND_WORDS)}{np.random.choice(SHOP_SUFFIX)}"
        while name in used_names:
            name = (f"{np.random.choice(BRAND_WORDS)}{np.random.choice(SHOP_SUFFIX)}"
                    f"{np.random.randint(10, 99)}")
        used_names.add(name)

        rows.append({
            'seller_id': f'S{i+1:04d}',
            'seller_name': name,
            'category': SUB_TO_CAT[sub],
            'sub_category': sub,
            'seller_level': level,
            'entry_date': entry.strftime('%Y-%m-%d'),
            'fans_count': int(fans),
            'is_community': int(np.random.random() < 0.8),    # 80% 商家加入官方商家社群 (1/0)
        })
    return pd.DataFrame(rows)


def gen_product_info(sellers):
    """2. 商品信息表 (1000 条) —— 每个商家固定 5 个商品, 品类随商家"""
    rows, pid = [], 1
    for _, s in sellers.iterrows():
        sub = s['sub_category']
        for _ in range(5):
            # 价格: 在该二级品类行业常识区间内均匀抽取
            lo, hi = PRICE_RANGE[sub]
            price = round(float(np.random.uniform(lo, hi)), 2)
            # 商品名: 品牌词 + 品类核心词 + 修饰词 + 后缀, 如 "良品坚果礼盒 人气礼盒装"
            name = (f"{np.random.choice(BRAND_WORDS)}{np.random.choice(PRODUCT_KEYWORDS[sub])} "
                    f"{np.random.choice(NAME_ADJ)}{np.random.choice(NAME_SUFFIX)}")
            rows.append({
                'product_id': f'P{pid:05d}',
                'seller_id': s['seller_id'],
                'product_name': name,
                'category': s['category'],
                'sub_category': sub,
                'price': price,
                'is_selected': int(np.random.random() < 0.6),    # 60% 入选平台选品库 (1/0)
                'on_shelf_date': (DATA_DATE - timedelta(days=int(np.random.uniform(7, 365)))
                                  ).strftime('%Y-%m-%d'),
            })
            pid += 1
    return pd.DataFrame(rows)


def gen_activity_signup(sellers):
    """3. 活动报名表 (约 270 条, 覆盖 4 场平台活动, 整体商家报名率 65%)"""
    seller_ids = sellers['seller_id'].values
    # 整体报名率 65%: 随机抽取 130 家商家参与过至少 1 场活动报名
    n_sign = int(len(seller_ids) * 0.65)
    signup_sellers = np.random.choice(seller_ids, size=n_sign, replace=False)

    rows = []
    for sid in signup_sellers:
        # 每商家报名 1~4 场活动 (多数报 1~2 场, 符合实际招商节奏)
        n_act = int(np.random.choice([1, 2, 3, 4], p=[0.35, 0.35, 0.20, 0.10]))
        for act in random.sample(ACTIVITIES, n_act):
            act_id, act_name, ss, se, es, ee = act
            # 报名时间落在该活动报名窗口内 (双11 窗口跨当前日期, 允许出现未来报名)
            signup_time = DATA_DATE + timedelta(
                days=int(np.random.uniform(ss, se)),
                hours=int(np.random.uniform(0, 24)),
                minutes=int(np.random.uniform(0, 60)),
            )
            # 审核状态: 未来报名必然还在"审核中"; 历史报名按 通过85%/审核中10%/拒绝5% 分布
            if signup_time > DATA_DATE:
                audit = '审核中'
            else:
                audit = np.random.choice(['审核通过', '审核中', '审核拒绝'],
                                         p=[0.85, 0.10, 0.05])
            rows.append({
                'activity_id': act_id,
                'activity_name': act_name,
                'seller_id': sid,
                'signup_time': signup_time.strftime('%Y-%m-%d %H:%M:%S'),
                'audit_status': audit,
                'signup_products': int(np.random.randint(1, 16)),   # 报名商品数 1~15
            })
    # 按报名时间升序排列, 便于按时间线分析
    return pd.DataFrame(rows).sort_values('signup_time').reset_index(drop=True)


def gen_live_record(sellers, signups):
    """4. 直播记录表 (最近 30 天, 日开播率 40%, 约 2400 条)"""
    # 审核通过的报名: 卖家 → 已通过活动集合 (用于判断是否"大促直播")
    passed = signups[signups['audit_status'] == '审核通过']
    seller_passed = passed.groupby('seller_id')['activity_id'].apply(set).to_dict()

    # 大促日历: 日期 → 活动ID (开学季活动期 + 双11预售预热期, 与近30天窗口有重叠)
    promo_calendar = {}
    for act_id, act_name, ss, se, es, ee in ACTIVITIES:
        if es is None:
            continue
        for d in range(es, ee + 1):
            promo_calendar[(DATA_DATE + timedelta(days=d)).date()] = act_id

    fans_map = dict(zip(sellers['seller_id'], sellers['fans_count']))
    cat_map = dict(zip(sellers['seller_id'], sellers['category']))

    rows = []
    for d in range(29, -1, -1):                    # 遍历最近 30 天 (从早到晚)
        live_date = DATA_DATE - timedelta(days=d)
        for _, s in sellers.iterrows():
            if np.random.random() >= 0.4:          # 日开播率 40%
                continue
            fans = fans_map[s['seller_id']]
            # 直播时长: 30~360 分钟, 三角分布使大多数直播集中在 1~3 小时
            duration = int(np.random.triangular(30, 90, 360))
            # 观看人次: 粉丝基数 × 曝光率 × 时长系数
            views = max(50, int(fans * np.random.uniform(0.003, 0.06) * (0.6 + duration / 200)))
            # 转化率: 观看 → 下单; 大促直播转化率更高
            conv = np.random.uniform(0.003, 0.05)
            # 是否大促直播: 当天处于活动期 且 商家该活动报名审核通过
            act_today = promo_calendar.get(live_date.date())
            is_promo = bool(act_today and act_today in seller_passed.get(s['seller_id'], set()))
            if is_promo:
                conv *= 1.6
            orders = max(1, int(views * conv))
            # GMV = 订单数 × 品类客单价 × 波动系数 (大促期间客单价上浮)
            aov = CATEGORY_AOV[cat_map[s['seller_id']]]
            promo_mult = np.random.uniform(1.2, 1.8) if is_promo else 1.0
            gmv = round(orders * aov * np.random.uniform(0.8, 1.2) * promo_mult, 2)
            rows.append({
                'live_date': live_date.strftime('%Y-%m-%d'),
                'seller_id': s['seller_id'],
                'live_duration': duration,
                'views': views,
                'gmv': gmv,
                'orders': orders,
                'is_promotion_live': int(is_promo),             # 是否大促直播 (1/0)
            })
    return pd.DataFrame(rows)


def gen_talent_info():
    """5. 达人信息表 (80 个, 层级 S:A:B:C = 5:20:35:40)"""
    # 层级: S:A:B:C = 5:20:35:40 → 4:16:28:32
    tiers = []
    for tier, (cnt, *_rest) in TIER_CONFIG.items():
        tiers += [tier] * cnt
    np.random.shuffle(tiers)
    # 垂类分布: 美妆/服饰类达人占比更高 (符合内容电商达人生态)
    cats = np.random.choice(list(CATEGORY_SUB.keys()), size=80,
                            p=[0.22, 0.26, 0.16, 0.18, 0.18])

    rows, used_names = [], set()
    for i, (tier, cat) in enumerate(zip(tiers, cats)):
        _cnt, fans_rng, roi_rng, fee_rng = TIER_CONFIG[tier]
        # 粉丝数/合作费: 按层级量级对数均匀抽取
        fans = int(10 ** np.random.uniform(np.log10(fans_rng[0]), np.log10(fans_rng[1])))
        fee = int(10 ** np.random.uniform(np.log10(fee_rng[0]), np.log10(fee_rng[1])))
        fee = int(round(fee / 100.0)) * 100                     # 合作费取整到百元
        # 平均ROI: 中小达人坑位费低、性价比高, ROI 普遍更高
        avg_roi = round(float(np.random.uniform(*roi_rng)), 2)
        # 达人昵称: Faker 生成中文姓名, 重名时加数字后缀去重
        name = fake.name()
        while name in used_names:
            name = fake.name() + str(np.random.randint(10, 99))
        used_names.add(name)

        rows.append({
            'talent_id': f'T{i+1:03d}',
            'talent_name': name,
            'tier': tier,
            'category': cat,
            'fans_count': int(fans),
            'avg_roi': avg_roi,
            'cooperation_fee': int(fee),
        })
    return pd.DataFrame(rows)


def gen_talent_match(products, talents):
    """6. 达人撮合表 (1500 条) —— 模拟 选品入库→意向沟通→排期确认→已开播 的撮合漏斗"""
    n = 1500

    # --- 商品池: 优先撮合"入选选品库"的商品 (85%), 少量库外商品 ---
    selected = products[products['is_selected'] == 1]
    unselected = products[products['is_selected'] == 0]
    n_sel = int(n * 0.85)
    prod = pd.concat([
        selected.sample(n_sel, replace=True, random_state=RANDOM_SEED),
        unselected.sample(n - n_sel, replace=True, random_state=RANDOM_SEED),
    ]).reset_index(drop=True)

    # --- 撮合状态: 按漏斗各环节占比抽取 ---
    statuses = np.random.choice(
        list(MATCH_STATUS.keys()), size=n,
        p=[v[0] for v in MATCH_STATUS.values()],
    )

    # 达人被撮合概率按层级加权 (A/B 级达人性价比高、档期多, 被撮合最多)
    tier_w = {'S': 0.15, 'A': 0.30, 'B': 0.35, 'C': 0.20}

    rows = []
    for i in range(n):
        status = statuses[i]
        prod_cat = prod.iloc[i]['category']
        # 75% 为垂类匹配 (达人垂类 = 商品一级品类), 25% 为跨类合作
        if np.random.random() < 0.75:
            pool = talents[talents['category'] == prod_cat]
        else:
            pool = talents[talents['category'] != prod_cat]
        w = pool['tier'].map(tier_w).values
        talent = pool.sample(1, weights=w).iloc[0]

        # 创建时间: 漏斗越靠后的状态创建越早, 符合业务推进节奏
        lo, hi = MATCH_STATUS[status][1]
        create_time = DATA_DATE - timedelta(
            days=int(np.random.uniform(lo, hi)),
            hours=int(np.random.uniform(0, 24)),
            minutes=int(np.random.uniform(0, 60)),
        )

        # 最终GMV: 仅"已开播"状态有值 = 合作费 × 实际ROI (围绕 avg_roi 正态波动);
        # 约 8% 的直播翻车无产出 (GMV=0)
        final_gmv = np.nan
        if status == '已开播':
            if np.random.random() < 0.08:
                final_gmv = 0.0
            else:
                roi_real = max(0.5, np.random.normal(talent['avg_roi'], talent['avg_roi'] * 0.25))
                final_gmv = round(talent['cooperation_fee'] * roi_real, 2)

        rows.append({
            'match_id': f'M{i+1:04d}',
            'product_id': prod.iloc[i]['product_id'],
            'seller_id': prod.iloc[i]['seller_id'],
            'talent_id': talent['talent_id'],
            'match_status': status,
            'create_time': create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'final_gmv': final_gmv,
        })
    return pd.DataFrame(rows)


def gen_buyer_reviews(products):
    """7. 买家秀评论表 (5000 条, 好评/差评两套通用电商评论词库)"""
    n = 5000
    # 评分分布: 电商评论整体偏正面, 1~5星加权, 均值约 4.3 星
    ratings = np.random.choice([1, 2, 3, 4, 5], size=n,
                               p=[0.02, 0.04, 0.09, 0.33, 0.52])
    # 评论商品: 入选选品库的商品热度更高, 评论数加权 3 倍
    w = np.where(products['is_selected'].values, 3, 1).astype(float)
    pids = np.random.choice(products['product_id'].values, size=n, p=w / w.sum())

    rows = []
    for i in range(n):
        r = ratings[i]
        # 评论内容: 4~5星用好评词库, 1~2星用差评词库, 3星中性随机
        if r >= 4:
            content = (f"{np.random.choice(GOOD_WORDS)}, {np.random.choice(GOOD_EXTRAS)}, "
                       f"非常满意, 好评推荐!")
        elif r <= 2:
            content = (f"{np.random.choice(BAD_WORDS)}, {np.random.choice(BAD_EXTRAS)}, "
                       f"有点失望, 不太推荐。")
        else:
            if np.random.random() < 0.5:
                content = f"{np.random.choice(GOOD_WORDS)}, 整体还行, 中规中矩。"
            else:
                content = f"{np.random.choice(BAD_WORDS)}, 勉强能用, 一般般吧。"
        # 精选买家秀: 仅高评分评论有资格入选, 整体比例控制在 15% (85% × 17.6%)
        is_show = bool(r >= 4 and np.random.random() < 0.176)
        rows.append({
            'review_id': f'R{i+1:05d}',
            'product_id': pids[i],
            'rating': int(r),
            'content': content,
            'review_date': (DATA_DATE - timedelta(days=int(np.random.uniform(0, 90)))
                            ).strftime('%Y-%m-%d'),
            'is_showcase': int(is_show),                         # 是否精选买家秀 (1/0)
        })
    return pd.DataFrame(rows)


# ============================================================
# 4. 主流程
# ============================================================

def main():
    print('=' * 64)
    print('  电商运营仿真数据生成器')
    print(f'  随机种子: {RANDOM_SEED}    数据参考日期: {DATA_DATE:%Y-%m-%d}')
    print(f'  输出目录: {OUTPUT_DIR}')
    print('=' * 64)

    # ---- 按表间依赖顺序生成 (商家→商品→报名→直播→达人→撮合→评论) ----
    print('\n[1/7] 生成商家信息表 seller_info ...')
    sellers = gen_seller_info()
    write_csv(sellers, 'seller_info.csv')

    print('[2/7] 生成商品信息表 product_info ...')
    products = gen_product_info(sellers)
    write_csv(products, 'product_info.csv')

    print('[3/7] 生成活动报名表 activity_signup ...')
    signups = gen_activity_signup(sellers)
    write_csv(signups, 'activity_signup.csv')

    print('[4/7] 生成直播记录表 live_record ...')
    lives = gen_live_record(sellers, signups)
    write_csv(lives, 'live_record.csv')

    print('[5/7] 生成达人信息表 talent_info ...')
    talents = gen_talent_info()
    write_csv(talents, 'talent_info.csv')

    print('[6/7] 生成达人撮合表 talent_match ...')
    matches = gen_talent_match(products, talents)
    write_csv(matches, 'talent_match.csv')

    print('[7/7] 生成买家秀评论表 buyer_reviews ...')
    reviews = gen_buyer_reviews(products)
    write_csv(reviews, 'buyer_reviews.csv')

    # ---- 完成提示与各表数据量统计 ----
    tables = [
        ('seller_info       商家信息表', sellers),
        ('product_info      商品信息表', products),
        ('activity_signup   活动报名表', signups),
        ('live_record       直播记录表', lives),
        ('talent_info       达人信息表', talents),
        ('talent_match      达人撮合表', matches),
        ('buyer_reviews     买家秀评论表', reviews),
    ]
    print('\n' + '=' * 64)
    print('  全部 7 张表生成完毕! 数据量统计:')
    total = 0
    for name, df in tables:
        print(f'  · {name:<38s} {len(df):>6,} 条')
        total += len(df)
    print(f'  · {"合计":<38s} {total:>6,} 条')
    sign_rate = signups['seller_id'].nunique() / len(sellers)
    print(f'  · 商家报名覆盖率: {signups["seller_id"].nunique()}/{len(sellers)}'
          f' = {sign_rate:.1%} (目标 65%)')
    print('=' * 64)


if __name__ == '__main__':
    main()
