# -*- coding: utf-8 -*-
"""
=====================================================
 达人-商品智能匹配推荐 (talent_recommendation.py)
=====================================================

【业务背景】
    为"入选选品库"的商品推荐最适配的带货达人, 三个维度综合打分:
      1) 品类匹配度: 达人垂类与商品品类一致, 粉丝调性与商品更契合, 转化效率更高
      2) 历史ROI:    基于 talent_match 已开播记录的实际产出 (最终GMV / 合作费),
                     有历史数据的达人优先于仅看标注ROI的达人
      3) 粉丝量级适配: 达人粉丝盘与商品价格带匹配 ——
                     高客单商品需要大粉丝盘撑规模, 低客单商品用中小达人性价比更高

【输入】
    ../data/raw/product_info.csv    商品表 (筛入选品库商品 is_selected=1)
    ../data/raw/talent_info.csv     达人档案 (层级/垂类/粉丝/标注ROI/合作费)
    ../data/raw/talent_match.csv    历史撮合记录 (计算达人实际ROI)

【输出】(../data/processed/, 编码 utf-8-sig)
    talent_recommendation_result.csv  每个选品库商品的 Top3 达人推荐明细

【依赖库】
    pandas / numpy

【运行方式】
    python talent_recommendation.py
"""

import os
import sys

import numpy as np
import pandas as pd

# 控制台输出统一 UTF-8, 避免 Windows GBK 控制台打印中文乱码
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ============================================================
# 0. 路径配置与评分参数
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'data', 'raw'))
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'data', 'processed'))
os.makedirs(OUT_DIR, exist_ok=True)

# 三维度评分权重 (之和为 1)
WEIGHT_CAT = 0.45    # 品类匹配度: 垂类一致是转化的基础
WEIGHT_ROI = 0.35    # 历史ROI: 实际带货产出是最硬的验证指标
WEIGHT_FANS = 0.20   # 粉丝量级适配: 兼顾规模与投产比
TOP_N = 3            # 每个商品推荐的达人数量


def fans_target(price):
    """商品价格带 → 目标粉丝量级 (对数分布中心)"""
    if price < 100:
        return 5e4     # 低客单(<100元): 中小达人即可, 合作费低性价比高
    if price <= 500:
        return 3e5     # 中客单(100-500元): 腰部达人, 兼顾规模与成本
    return 1.5e6       # 高客单(>500元): 头部达人, 需要大流量盘撑GMV


# ============================================================
# 1. 数据加载与达人评分准备
# ============================================================

def load_data():
    """读取商品表 / 达人档案 / 历史撮合记录"""
    products = pd.read_csv(os.path.join(RAW_DIR, 'product_info.csv'), encoding='utf-8-sig')
    talents = pd.read_csv(os.path.join(RAW_DIR, 'talent_info.csv'), encoding='utf-8-sig')
    matches = pd.read_csv(os.path.join(RAW_DIR, 'talent_match.csv'), encoding='utf-8-sig')
    return products, talents, matches


def calc_talent_scores(talents, matches):
    """为每个达人计算: 历史实际ROI、ROI得分(0-1)、粉丝对数"""
    # 历史实际ROI: 仅统计"已开播"且有产出的撮合记录
    # 实际ROI = Σ最终GMV / Σ合作费 (汇总口径, 比逐场平均更稳健)
    b = matches[(matches['match_status'] == '已开播') & (matches['final_gmv'] > 0)]
    b = b.merge(talents[['talent_id', 'cooperation_fee']], on='talent_id', how='left')
    hist = b.groupby('talent_id').agg(
        hist_broadcasts=('final_gmv', 'size'),
        hist_gmv=('final_gmv', 'sum'),
        hist_fee=('cooperation_fee', 'sum'),
    )
    hist['hist_roi'] = hist['hist_gmv'] / hist['hist_fee']

    t = talents.merge(hist[['hist_broadcasts', 'hist_roi']], on='talent_id', how='left')
    # 有效ROI: 有历史数据用实际值, 无历史数据退化为达人档案标注ROI
    t['eff_roi'] = t['hist_roi'].fillna(t['avg_roi'])
    # ROI得分: min-max 归一化到 0-1, 跨达人可比
    rmin, rmax = t['eff_roi'].min(), t['eff_roi'].max()
    t['roi_score'] = (t['eff_roi'] - rmin) / (rmax - rmin) if rmax > rmin else 0.5
    # 粉丝对数: 用于粉丝量级适配的几何距离计算
    t['log_fans'] = np.log10(t['fans_count'])
    return t


# ============================================================
# 2. 三维度匹配打分
# ============================================================

def recommend_for_product(p, t):
    """单个商品: 对全体达人打分并返回 Top3"""
    p_cat = p['category']
    target = fans_target(p['price'])

    # 维度1: 品类匹配度 — 同垂类 1.0, 跨品类 0.3 (跨类合作转化打折)
    cat_score = np.where(t['category'].values == p_cat, 1.0, 0.3)
    # 维度2: 历史ROI得分 (已在达人维度归一化)
    roi_score = t['roi_score'].values
    # 维度3: 粉丝量级适配 — 对数空间高斯衰减, 越接近目标量级得分越高
    fans_score = np.exp(-0.5 * ((t['log_fans'].values - np.log10(target)) / 0.8) ** 2)
    # 综合匹配得分 (0-1, 输出时放大为百分制)
    total = WEIGHT_CAT * cat_score + WEIGHT_ROI * roi_score + WEIGHT_FANS * fans_score

    top_idx = np.argsort(-total)[:TOP_N]
    rows = []
    for rank, idx in enumerate(top_idx, 1):
        row = t.iloc[idx]
        rows.append({
            'product_id': p['product_id'],
            'product_name': p['product_name'],
            'category': p_cat,
            'price': p['price'],
            'rank': rank,
            'talent_id': row['talent_id'],
            'talent_name': row['talent_name'],
            'tier': row['tier'],
            'talent_category': row['category'],
            'fans_count': int(row['fans_count']),
            'eff_roi': round(row['eff_roi'], 2),
            'cooperation_fee': int(row['cooperation_fee']),
            'cat_score': round(cat_score[idx], 2),
            'roi_score': round(roi_score[idx], 2),
            'fans_score': round(fans_score[idx], 2),
            'match_score': round(total[idx] * 100, 2),
            'recommend_reason': build_reason(row, p_cat, p['price']),
        })
    return rows


def build_reason(row, p_cat, price):
    """拼装推荐理由: 说明三个维度上该达人的适配情况"""
    parts = ['垂类同品类' if row['category'] == p_cat else '跨品类达人']
    if pd.notna(row['hist_roi']):
        parts.append(f"历史开播{int(row['hist_broadcasts'])}场实际ROI {row['hist_roi']:.2f}")
    else:
        parts.append(f"暂无历史数据, 参考标注ROI {row['avg_roi']:.2f}")
    if price < 100:
        band = '低客单(百元内)'
    elif price <= 500:
        band = '中客单'
    else:
        band = '高客单'
    parts.append(f'粉丝量级与{band}商品适配')
    return '；'.join(parts)


# ============================================================
# 3. 主流程
# ============================================================

def main():
    print('=' * 64)
    print('  达人-商品智能匹配推荐')
    print(f'  评分权重: 品类匹配 {WEIGHT_CAT} + 历史ROI {WEIGHT_ROI} + 粉丝适配 {WEIGHT_FANS}')
    print('=' * 64)

    products, talents, matches = load_data()
    # 仅对"入选选品库"的商品做达人推荐 (选品库商品才有撮合场景)
    selected = products[products['is_selected'] == 1].reset_index(drop=True)
    print(f'入选选品库商品: {len(selected):,} 个 / 全量 {len(products):,} 个')
    print(f'达人池: {len(talents):,} 人')

    t = calc_talent_scores(talents, matches)
    print(f'有历史开播数据的达人: {int(t["hist_roi"].notna().sum())} 人')

    # 逐商品对全体达人打分, 取 Top3
    all_rows = []
    for _, p in selected.iterrows():
        all_rows.extend(recommend_for_product(p, t))
    result = pd.DataFrame(all_rows)

    path = os.path.join(OUT_DIR, 'talent_recommendation_result.csv')
    result.to_csv(path, index=False, encoding='utf-8-sig')
    print(f'\n  ✔ talent_recommendation_result.csv  {len(result):>6,} 条 → {path}')

    # 完成提示与结果统计: 按品类汇总推荐达人池
    print('\n' + '=' * 64)
    print('  推荐完成! 按品类汇总推荐达人池:')
    for cat, grp in result.groupby('category'):
        n_prod = len(selected[selected['category'] == cat])
        pool = grp['talent_id'].nunique()
        top_talents = (grp.groupby('talent_name')['talent_id'].size()
                       .sort_values(ascending=False).head(3))
        top_str = ', '.join(f'{name}({cnt}次)' for name, cnt in top_talents.items())
        print(f'  {cat:<6s} 商品 {n_prod:>3d} 个 | 推荐 {len(grp):>4d} 条 | '
              f'达人池 {pool:>2d} 人 | 平均得分 {grp["match_score"].mean():.2f}')
        print(f'        池内热门: {top_str}')
    print(f'\n  整体: {len(selected)} 个商品 × Top{TOP_N} = {len(result):,} 条推荐记录, '
          f'平均预估匹配得分 {result["match_score"].mean():.2f}')
    print('=' * 64)


if __name__ == '__main__':
    main()
