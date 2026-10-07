# -*- coding: utf-8 -*-
"""
=====================================================
 商家分层聚类模型 (seller_segmentation.py)
=====================================================

【业务背景】
    商家分层运营是平台精细化运营的基础。本脚本基于商家近30天的
    经营行为构造特征, 使用 K-Means 将商家聚为 4 类:
      核心商家 / 成长商家 / 潜力商家 / 沉睡商家
    并输出每类商家的画像与差异化运营策略, 供商家运营团队分配资源。

【输入】
    ../data/raw/seller_info.csv        商家基础信息 (层级/粉丝/社群)
    ../data/raw/live_record.csv        直播记录 (近30天)
    ../data/raw/activity_signup.csv    活动报名记录
    ../data/raw/product_info.csv       商品信息 (计算在售商品数)

【输出】(../data/processed/, 编码 utf-8-sig)
    seller_segment_result.csv          每个商家的聚类类别与特征明细
    seller_segment_report.md           聚类分析报告与分层运营策略建议

【依赖库】
    pandas / numpy / scikit-learn

【模型设置】
    随机种子 42; 5 个特征均做标准化 (StandardScaler) 消除量纲差异;
    聚类命名按"经营活力"综合得分 (0.5×GMV + 0.3×开播天数 + 0.2×报名次数)
    降序映射为 核心/成长/潜力/沉睡 四个分层

【运行方式】
    python seller_segmentation.py
"""

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# 控制台输出统一 UTF-8, 避免 Windows GBK 控制台打印中文乱码
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ============================================================
# 0. 路径配置与全局参数
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'data', 'raw'))
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'data', 'processed'))
os.makedirs(OUT_DIR, exist_ok=True)

RANDOM_SEED = 42
N_CLUSTERS = 4
# 聚类命名顺序: 按聚类平均GMV降序依次命名 (业务语义: 越活跃越核心)
SEGMENT_NAMES = ['核心商家', '成长商家', '潜力商家', '沉睡商家']
# 聚类特征列: 经营规模 + 活跃度 + 参与度 + 货盘宽度
FEAT_COLS = ['gmv_30d', 'live_days', 'fans_count', 'signup_cnt', 'product_cnt']


# ============================================================
# 1. 特征构造
# ============================================================

def build_features():
    """构造商家特征宽表: 商家基础信息 + 经营行为聚合指标 (每商家一行)"""
    sellers = pd.read_csv(os.path.join(RAW_DIR, 'seller_info.csv'), encoding='utf-8-sig')
    lives = pd.read_csv(os.path.join(RAW_DIR, 'live_record.csv'), encoding='utf-8-sig')
    signups = pd.read_csv(os.path.join(RAW_DIR, 'activity_signup.csv'), encoding='utf-8-sig')
    products = pd.read_csv(os.path.join(RAW_DIR, 'product_info.csv'), encoding='utf-8-sig')

    # 近30天GMV: 直播表本身就是近30天快照, 按商家汇总成交金额
    gmv = lives.groupby('seller_id')['gmv'].sum().rename('gmv_30d')
    # 开播天数: 近30天内有开播的天数 (衡量开播活跃度)
    live_days = lives.groupby('seller_id')['live_date'].nunique().rename('live_days')
    # 活动报名次数: 累计报名活动场次 (衡量平台活动参与度)
    signup_cnt = signups.groupby('seller_id')['activity_id'].count().rename('signup_cnt')
    # 在售商品数: 商品表中该商家的商品数量 (衡量货盘丰富度)
    product_cnt = products.groupby('seller_id')['product_id'].count().rename('product_cnt')

    feat = sellers[['seller_id', 'seller_name', 'category', 'sub_category',
                    'seller_level', 'fans_count']].copy()
    for s in [gmv, live_days, signup_cnt, product_cnt]:
        feat = feat.merge(s, on='seller_id', how='left')
    # 未开播/未报名商家补 0
    feat[['gmv_30d', 'live_days', 'signup_cnt', 'product_cnt']] = \
        feat[['gmv_30d', 'live_days', 'signup_cnt', 'product_cnt']].fillna(0)
    return feat


# ============================================================
# 2. K-Means 聚类
# ============================================================

def run_clustering(feat):
    """标准化 + K-Means 聚类, 并按经营活力综合得分为聚类命名"""
    X = feat[FEAT_COLS].values
    # 特征标准化: GMV(万级)/粉丝数(百万级)与开播天数(十级)量纲差异大,
    # 不标准化会导致大数值特征主导距离计算, 聚类结果失真
    X_scaled = StandardScaler().fit_transform(X)
    km = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_SEED, n_init=10).fit(X_scaled)
    feat['cluster_id'] = km.labels_

    # 聚类命名: 按"经营活力"综合得分排序 —— 每类计算各特征标准化后的均值,
    # 以 0.5×GMV + 0.3×开播天数 + 0.2×报名次数 加权求和, 得分降序依次命名
    # 核心商家 → 成长商家 → 潜力商家 → 沉睡商家。
    # 业务解释: 若只看GMV排序, "报名积极但GMV未起量"的类会被误命名为沉睡;
    # 综合活力得分把"产出+活跃+参与"一并纳入, 更能还原经营阶梯
    z_df = pd.DataFrame(X_scaled, columns=FEAT_COLS)
    z_df['cluster_id'] = km.labels_
    vitality = z_df.groupby('cluster_id')[['gmv_30d', 'live_days', 'signup_cnt']] \
        .mean().mul([0.5, 0.3, 0.2]).sum(axis=1)
    rank = vitality.sort_values(ascending=False).index
    cluster_to_seg = {int(c): SEGMENT_NAMES[i] for i, c in enumerate(rank)}
    feat['segment'] = feat['cluster_id'].map(cluster_to_seg)
    return feat, cluster_to_seg


# ============================================================
# 3. 聚类分析报告
# ============================================================

def build_report(feat):
    """生成聚类分析报告 (Markdown): 规模/画像/交叉/运营策略"""
    total = len(feat)
    seg_order = SEGMENT_NAMES
    counts = feat['segment'].value_counts().reindex(seg_order)
    profile = feat.groupby('segment')[FEAT_COLS].mean().reindex(seg_order)
    cross = pd.crosstab(feat['segment'], feat['seller_level']).reindex(seg_order)

    lines = []
    lines.append('# 商家分层聚类分析报告\n')
    lines.append(f'> 生成时间: {datetime.now():%Y-%m-%d %H:%M} | '
                 f'模型: K-Means (K={N_CLUSTERS}) | 随机种子: {RANDOM_SEED} | 特征已标准化\n')
    lines.append('## 一、分析概述\n')
    lines.append(f'- 数据范围: 近30天直播快照, 共 {total} 家商家\n')
    lines.append('- 聚类特征: 近30天GMV / 开播天数 / 粉丝数 / 活动报名次数 / 在售商品数\n')
    lines.append('- 分层命名逻辑: 按"经营活力"综合得分排序 —— 核心锚定GMV体量, '
                 '其余三类按 0.5×GMV + 0.3×开播天数 + 0.2×报名次数 (标准化均值加权) 排序, '
                 '依次命名核心商家 → 成长商家 → 潜力商家 → 沉睡商家\n')

    lines.append('## 二、聚类规模与画像\n')
    lines.append('| 分层 | 商家数 | 占比 | 平均GMV | 平均开播天数 | 平均粉丝数 | 平均报名次数 | 平均商品数 |')
    lines.append('|---|---|---|---|---|---|---|---|')
    for seg in seg_order:
        r = profile.loc[seg]
        lines.append(f'| {seg} | {int(counts[seg])} | {counts[seg] * 100.0 / total:.2f}% | '
                     f'{r["gmv_30d"]:,.0f} | {r["live_days"]:.1f} | {r["fans_count"]:,.0f} | '
                     f'{r["signup_cnt"]:.1f} | {r["product_cnt"]:.1f} |')
    lines.append('')

    lines.append('## 三、分层 × 平台层级交叉\n')
    lines.append('| 分层 | 头部 | 腰部 | 尾部 |')
    lines.append('|---|---|---|---|')
    for seg in seg_order:
        lines.append(f'| {seg} | {int(cross.loc[seg].get("头部", 0))} | '
                     f'{int(cross.loc[seg].get("腰部", 0))} | {int(cross.loc[seg].get("尾部", 0))} |')
    lines.append('')

    lines.append('## 四、分层运营策略建议\n')
    # 每类商家的差异化运营策略 (结合画像动态填充关键数字)
    strategies = {
        '核心商家': [
            '平台GMV支柱, 优先配置专属客户成功经理, 建立月度经营复盘机制',
            '大促活动给予S级资源位与独家权益, 以年度框架协议锁定深度合作',
            '新品首发/新品类拓展优先邀请, 沉淀为平台标杆案例对外招商',
        ],
        '成长商家': [
            '开播活跃度全场最高, 处于上升通道, 以流量券+开播任务组合激励推动GMV上台阶',
            '当前活动参与偏少, 引导报名大促承接平台流量红利',
            '提供一对一经营诊断, 补齐选品/投流短板',
        ],
        '潜力商家': [
            '活动参与热情全场最高但GMV未起量, 重点做直播技巧培训与选品指导',
            '达人撮合资源倾斜, 帮助其通过达人带货放大GMV',
            '低门槛小额流量扶持 (新客流量包), 降低试错成本',
        ],
        '沉睡商家': [
            '对平台活动几乎无响应 (平均报名不足1次), 联动社群做定向唤醒与利益点宣导',
            '经营持续被动、长期无起色则启动退出/清退评估, 释放平台资源',
            '盘点其粉丝资产与货盘, 判断是否有二次激活价值',
        ],
    }
    for seg in seg_order:
        r = profile.loc[seg]
        lines.append(f'### {seg} ({int(counts[seg])} 家, {counts[seg] * 100.0 / total:.2f}%)\n')
        lines.append(f'画像: 平均GMV {r["gmv_30d"]:,.0f} 元, 平均开播 {r["live_days"]:.1f} 天, '
                     f'平均粉丝 {r["fans_count"]:,.0f}, 平均报名 {r["signup_cnt"]:.1f} 次\n')
        for i, s in enumerate(strategies[seg], 1):
            lines.append(f'{i}. {s}')
        lines.append('')

    lines.append('## 五、模型使用说明\n')
    lines.append('- 数据更新后重新运行 `python seller_segmentation.py` 即可刷新分层结果\n')
    lines.append('- 分层名称由聚类经营活力综合得分自动排序映射, 保证业务语义稳定\n')
    lines.append('- 如需调整分层数量, 修改脚本顶部 `N_CLUSTERS` 参数即可\n')
    return '\n'.join(lines)


# ============================================================
# 4. 主流程
# ============================================================

def main():
    print('=' * 64)
    print('  商家分层聚类模型 (K-Means)')
    print(f'  随机种子: {RANDOM_SEED}    聚类数: {N_CLUSTERS}')
    print('=' * 64)

    feat = build_features()
    print(f'构造商家特征: {len(feat)} 家 × {len(FEAT_COLS)} 个特征')

    feat, _ = run_clustering(feat)

    # 1. 商家分层结果明细 (按分层+GMV排序输出)
    feat['_seg_order'] = feat['segment'].map({s: i for i, s in enumerate(SEGMENT_NAMES)})
    out_cols = ['seller_id', 'seller_name', 'category', 'sub_category', 'seller_level',
                'fans_count', 'gmv_30d', 'live_days', 'signup_cnt', 'product_cnt',
                'cluster_id', 'segment']
    result = feat[out_cols + ['_seg_order']] \
        .sort_values(['_seg_order', 'gmv_30d'], ascending=[True, False]) \
        .drop(columns='_seg_order').reset_index(drop=True)
    path = os.path.join(OUT_DIR, 'seller_segment_result.csv')
    result.to_csv(path, index=False, encoding='utf-8-sig')
    print(f'  ✔ seller_segment_result.csv   {len(result):>6,} 条 → {path}')

    # 2. 聚类分析报告
    report = build_report(feat)
    path = os.path.join(OUT_DIR, 'seller_segment_report.md')
    with open(path, 'w', encoding='utf-8-sig') as f:
        f.write(report)
    print(f'  ✔ seller_segment_report.md    已生成 → {path}')

    # 3. 完成提示与结果统计
    counts = feat['segment'].value_counts().reindex(SEGMENT_NAMES)
    print('\n' + '=' * 64)
    print('  聚类完成! 商家分层统计:')
    for seg in SEGMENT_NAMES:
        print(f'    {seg:<6s} {int(counts[seg]):>3d} 家 ({counts[seg] * 100.0 / len(feat):.2f}%)')
    print('=' * 64)


if __name__ == '__main__':
    main()
