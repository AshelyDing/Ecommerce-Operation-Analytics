# -*- coding: utf-8 -*-
"""
=====================================================
 买家秀评论情感与关键词分析 (review_sentiment.py)
=====================================================

【业务背景】
    买家秀评论是商品口碑与内容素材的重要来源。本脚本对买家秀评论做
    情感与关键词挖掘, 回答三个问题:
      1) 好评/差评都在说什么?   → 分品类正负向 Top10 关键词
      2) 各品类口碑健康度如何?   → 情感得分 (5星正向加权)
      3) 差评集中在哪些环节?     → 差评关键词 → 供品控/供应链整改参考

【输入】
    ../data/raw/buyer_reviews.csv   买家秀评论表 (product_id / rating / content)
    ../data/raw/product_info.csv    商品信息表 (用于映射一级品类)

【输出】(../data/processed/, 编码 utf-8-sig, 兼容 Excel)
    review_keywords.csv             分品类正负向关键词及词频
    review_sentiment_summary.csv    分品类评论数/平均评分/好评率/情感得分

【依赖库】
    pandas / jieba / collections

【运行方式】
    python review_sentiment.py
"""

import os
import re
import sys
from collections import Counter

import jieba
import pandas as pd

# 控制台输出统一 UTF-8, 避免 Windows GBK 控制台打印中文乱码
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# jieba 仅输出警告以上日志, 屏蔽 "Building prefix dict" 等初始化提示
jieba.setLogLevel(60)

# ============================================================
# 0. 路径配置 (基于脚本自身位置推导, 不写死绝对路径)
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'data', 'raw'))
OUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'data', 'processed'))
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# 1. 词库配置
# ============================================================

# 电商领域词: 加入 jieba 自定义词典, 避免被错误切分 (如 "性价比" 被切成 性/价比)
DOMAIN_WORDS = [
    '性价比', '物超所值', '回购', '色差', '掉色', '物流', '客服', '包装',
    '做工', '手感', '颜值', '买家秀', '质量', '尺寸', '异味', '破损',
    '粗糙', '退货', '种草', '超值', '描述', '一致',
]
for w in DOMAIN_WORDS:
    jieba.add_word(w)

# 停用词表: 无业务含义的虚词/代词/语气词 + 评论模板通用套话
# 说明: 数据模板中每条评论都带"非常满意/好评推荐"等固定结尾, 属通用套话,
#       剔除后关键词统计才能突出"质量/物流/性价比"等差异化内容
STOPWORDS = set("""
的 了 是 我 你 他 她 它 我们 你们 他们 这 那 这些 那些 这个 那个
什么 怎么 这样 那样 一个 一些 有 没 没有 不 不是 就 都 也 还 又 再
很 太 挺 真 真的 有点 有些 比较 非常 特别 超级 更 最 只 才 刚 已经
曾经 会 能 可以 应该 需要 让 把 被 给 对 和 与 及 或者 或 但 但是
而 而且 因为 所以 如果 虽然 然后 之后 之 其 于 呢 吗 吧 啊 呀 哦
哈哈 呵呵 觉得 感觉 一次 一下 这次 下次 东西 里面 整体 还是 就是
不错 好的 收到 购买 时候 值得 来说 大家 好评 推荐 满意 非常 不太
很好 很喜欢 很满意 挺好 超好 失望 有点失望 一般般 一般 勉强 凑合 中规中矩
""".split())

# 中文词过滤规则: 仅保留 2 字及以上的纯中文词 (过滤单字虚词/数字/字母)
ZH_TOKEN = re.compile(r'^[一-龥]{2,}$')


# ============================================================
# 2. 数据加载与处理
# ============================================================

def load_data():
    """读取评论表并关联商品表获得一级品类"""
    reviews = pd.read_csv(os.path.join(RAW_DIR, 'buyer_reviews.csv'), encoding='utf-8-sig')
    products = pd.read_csv(os.path.join(RAW_DIR, 'product_info.csv'), encoding='utf-8-sig')
    df = reviews.merge(products[['product_id', 'category']], on='product_id', how='left')
    return df


def cut_words(text):
    """jieba 分词 + 停用词/规则过滤, 返回有效业务词列表"""
    return [w for w in jieba.cut(text) if ZH_TOKEN.match(w) and w not in STOPWORDS]


def analyze_keywords(df):
    """分品类统计正/负向评论的 Top10 关键词及词频"""
    # 情感方向划分: 4-5星 → 正向; 1-2星 → 负向; 3星中性不参与关键词统计
    df['sentiment'] = df['rating'].map(lambda r: '正向' if r >= 4 else ('负向' if r <= 2 else '中性'))
    rows = []
    for (cat, sent), grp in df[df['sentiment'] != '中性'].groupby(['category', 'sentiment']):
        counter = Counter()
        for content in grp['content']:
            counter.update(cut_words(content))
        for rank, (word, freq) in enumerate(counter.most_common(10), 1):
            rows.append({'category': cat, 'sentiment': sent,
                         'keyword': word, 'frequency': freq, 'rank': rank})
    return pd.DataFrame(rows)


def analyze_sentiment(df):
    """分品类计算评论数/平均评分/好评率/情感得分"""
    # 情感得分 = Σ(星数×评论数) / (5 × 评论总数) × 100, 满分100(全5星),
    # 即 5星正向加权后归一化到百分制, 分数越高口碑越健康
    rows = []
    for cat, grp in df.groupby('category'):
        n = len(grp)
        good = int((grp['rating'] >= 4).sum())
        bad = int((grp['rating'] <= 2).sum())
        rows.append({
            'category': cat,
            'review_cnt': n,
            'avg_rating': round(grp['rating'].mean(), 2),
            'good_cnt': good,
            'good_rate_pct': round(good * 100.0 / n, 2),
            'bad_cnt': bad,
            'bad_rate_pct': round(bad * 100.0 / n, 2),
            'sentiment_score': round(grp['rating'].sum() * 100.0 / (5.0 * n), 2),
        })
    return pd.DataFrame(rows).sort_values('sentiment_score', ascending=False).reset_index(drop=True)


def write_csv(df, filename):
    """统一写盘: utf-8-sig 编码, 不带行索引"""
    path = os.path.join(OUT_DIR, filename)
    df.to_csv(path, index=False, encoding='utf-8-sig')
    print(f'  ✔ {filename:<28s} {len(df):>6,} 条 → {path}')


# ============================================================
# 3. 主流程
# ============================================================

def main():
    print('=' * 64)
    print('  买家秀评论情感与关键词分析')
    print('=' * 64)

    df = load_data()
    print(f'\n加载评论数据: {len(df):,} 条')

    # 1. 分品类正负向关键词统计
    kw_df = analyze_keywords(df)
    write_csv(kw_df, 'review_keywords.csv')

    # 2. 分品类情感汇总
    sent_df = analyze_sentiment(df)
    write_csv(sent_df, 'review_sentiment_summary.csv')

    # 3. 完成提示与结果统计
    print('\n' + '=' * 64)
    print('  分析完成! 分品类情感得分统计:')
    print(sent_df.to_string(index=False))
    print('-' * 64)
    print('  各品类好评 Top3 关键词预览:')
    for cat, grp in kw_df[kw_df['sentiment'] == '正向'].groupby('category'):
        top = grp.sort_values('rank').head(3)['keyword'].tolist()
        print(f'    {cat:<6s} {" / ".join(top)}')
    print('=' * 64)


if __name__ == '__main__':
    main()
