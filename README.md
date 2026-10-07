# Ecommerce-Operation-Analytics · 电商运营数据分析框架

<div align="center">

**通用内容电商全链路运营分析工具集 · 数据仿真 → SQL 业务分析 → Python 深度挖掘 三层架构**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![SQL](https://img.shields.io/badge/SQL-MySQL%208.0%2B%20%2F%20SQLite%203.25%2B-orange)
![pandas](https://img.shields.io/badge/pandas-%E2%9C%94-green)
![scikit-learn](https://img.shields.io/badge/scikit--learn-%E2%9C%94-green)
![jieba](https://img.shields.io/badge/jieba-%E2%9C%94-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

</div>

## 一、项目简介

**一句话定位**：一套开箱即用的内容电商运营分析框架——用 7 张仿真业务表还原"商家 → 商品 → 直播 → 活动 → 达人 → 评论"完整经营链路，配套 17 个 SQL 业务查询与 3 个 Python 挖掘模型，覆盖日常监控、社群运营、达人撮合、效果复盘、大促分析五大场景。

**核心价值**

- **零门槛**：数据一键仿真生成（随机种子固定、结果可复现），无需接入真实业务系统即可完整体验运营分析流程
- **业务视角**：每个查询、每个特征都从真实电商运营工作出发（如"低开播商家清单"直接服务于社群定向触达），指标口径统一沉淀在文档中
- **三层可扩展**：SQL 层出标准指标、Python 层出挖掘模型、输出层可直接对接 PowerBI 等看板工具

**适用场景**

- 电商运营团队搭建数据监控与复盘体系的方法论参考
- 数据分析岗位的项目实践 / 面试作品集
- 内容电商（直播带货、达人撮合）业务逻辑的教学与演示

## 二、项目架构

数据从仿真生成开始，依次流经 SQL 业务分析层与 Python 深度分析层，最终落到 `data/processed/` 供看板消费。三层共享同一套数据源与指标口径：

```text
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  ① 数据层            │    │  ② SQL 业务分析层      │    │  ③ Python 深度分析层  │    │  ④ 输出层         │
│  data/raw/          │ ─▶ │  sql/ *.sql           │ ─▶ │  python/ *.py       │ ─▶ │  data/processed/ │
│                     │    │                      │    │                     │    │                  │
│  7 张仿真业务表       │    │  5 大模块 17 个查询     │    │  3 个挖掘模型         │    │  5 个分析结果文件   │
│  10,511 条数据       │    │  日常监控 / 社群 /      │    │  评论情感挖掘 /       │    │  CSV + MD 报告    │
│  商家→商品→直播→     │    │  达人 / 复盘 / 大促     │    │  商家聚类分层 /       │    │  (utf-8-sig,      │
│  活动→达人→评论 全链路 │    │  标准 SQL, 双库兼容     │    │  达人智能推荐         │    │   可直接进 PowerBI)│
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘    └──────────────────┘
        │                            │                            │
        │ 随机种子 42                  │ 比率保留两位小数             │ 特征同源 (与SQL口径一致)
        │ ID 跨表互相关联              │ 口径注释先行                 │ 随机种子 42 / 特征标准化
```

## 三、核心模块（SQL 业务分析层）

5 个业务模块对应 5 个 SQL 脚本，全部为标准 SQL 语法，兼容 **MySQL 8.0+ / SQLite 3.25+**，每个查询前附有运营场景与口径说明：

| # | 模块 | 业务场景 | 核心指标 | 文件 |
|---|------|----------|----------|------|
| 1 | 日常运营指标监控 | 运营日报：全品类经营健康度巡检，识别需要定向触达的商家 | 品类报名率、审核通过率、近7天日均开播场次/总GMV/订单量/场均观看、低开播商家清单 | [01_daily_monitoring.sql](sql/01_daily_monitoring.sql) |
| 2 | 商家社群运营分析 | 社群运营：评估私域社群的覆盖度与拉动力，验证"社群 → 活跃"的经营假设 | 社群渗透率与层级分布、社群内外报名率/开播率对比、各层级社群贡献度（GMV占比/报名占比） | [02_seller_community.sql](sql/02_seller_community.sql) |
| 3 | 达人撮合漏斗分析 | 达人运营：撮合全链路转化诊断，输出达人分层带货效果排行 | 漏斗转化率（选品入库→意向沟通→排期确认→已开播）、品类撮合成功率与平均最终GMV、达人层级场均GMV/ROI、品类×层级矩阵 | [03_talent_match.sql](sql/03_talent_match.sql) |
| 4 | 商家运营效果复盘 | 周/月复盘：商家分层 GMV 结构健康度、商品口碑、开播投入产出比 | 头部/腰部/尾部 GMV 占比、好评率与评分分布、开播频次×GMV 分桶统计 | [04_operation_effect.sql](sql/04_operation_effect.sql) |
| 5 | 大促活动全链路分析 | 大促复盘：多场大促横向对比，沉淀可复用的大促打法 | 报名商家数、开播场次、总GMV、场均订单、品类GMV增长贡献度、各层级商家参与率 | [05_promotion_analysis.sql](sql/05_promotion_analysis.sql) |

## 四、深度分析能力（Python 挖掘层）

| 脚本 | 能力 | 方法 | 输出（data/processed/） |
|------|------|------|--------------------------|
| [review_sentiment.py](python/review_sentiment.py) | 买家秀评论情感与关键词挖掘 | jieba 分词 + 停用词/领域词典；好评（≥4星）/差评（≤2星）Top10 关键词；5星正向加权情感得分 | `review_keywords.csv`（分品类正负向关键词词频）<br>`review_sentiment_summary.csv`（评论数/平均评分/好评率/情感得分） |
| [seller_segmentation.py](python/seller_segmentation.py) | 商家 K-Means 智能分层与运营策略 | 5 特征（近30天GMV/开播天数/粉丝数/报名次数/商品数）标准化后 K-Means 聚 4 类：核心/成长/潜力/沉睡商家，自动生成画像与差异化运营策略 | `seller_segment_result.csv`（每商家分层+特征明细）<br>`seller_segment_report.md`（聚类报告与运营建议） |
| [talent_recommendation.py](python/talent_recommendation.py) | 达人-商品智能匹配推荐 | 三维度打分（品类匹配度 0.45 + 历史ROI 0.35 + 粉丝量级适配 0.20），为每个选品库商品推荐 Top3 达人并生成推荐理由 | `talent_recommendation_result.csv`（每商品 Top3 达人+预估得分+推荐理由） |

## 五、目录结构

```text
Ecommerce-Operation-Analytics/
├── README.md                             # 项目说明文档
├── .gitignore                            # Git 忽略规则
│
├── data/
│   ├── raw/                              # ① 仿真数据层 (7 张业务表, utf-8-sig)
│   │   ├── seller_info.csv               #   商家信息表        200 条
│   │   ├── product_info.csv              #   商品信息表        1,000 条
│   │   ├── activity_signup.csv           #   活动报名表        275 条
│   │   ├── live_record.csv               #   直播记录表        2,456 条
│   │   ├── talent_info.csv               #   达人档案表        80 条
│   │   ├── talent_match.csv              #   达人撮合记录表     1,500 条
│   │   └── buyer_reviews.csv             #   买家秀评论表      5,000 条
│   └── processed/                        # ④ 分析结果输出层
│       ├── review_keywords.csv
│       ├── review_sentiment_summary.csv
│       ├── seller_segment_result.csv
│       ├── seller_segment_report.md
│       └── talent_recommendation_result.csv
│
├── sql/                                  # ② SQL 业务分析层 (MySQL 8.0+ / SQLite 3.25+)
│   ├── 01_daily_monitoring.sql           #   模块1: 日常运营指标监控
│   ├── 02_seller_community.sql           #   模块2: 商家社群运营分析
│   ├── 03_talent_match.sql               #   模块3: 达人撮合漏斗分析
│   ├── 04_operation_effect.sql           #   模块4: 商家运营效果复盘
│   └── 05_promotion_analysis.sql         #   模块5: 大促活动全链路分析
│
├── python/                               # ③ 数据仿真 + Python 深度分析层
│   ├── data_generator.py                 #   仿真数据生成器 (7 张表一键生成)
│   ├── review_sentiment.py               #   买家秀评论情感与关键词分析
│   ├── seller_segmentation.py            #   商家分层聚类模型
│   └── talent_recommendation.py          #   达人-商品智能匹配推荐
│
├── powerbi/
│   └── screenshots/                      # 看板预览截图存放目录
│
└── docs/
    ├── metrics_dict.md                   # 电商运营核心指标词典
    └── business_logic.md                 # 业务逻辑与分析思路说明
```

## 六、快速开始

### 环境要求

- Python 3.10+（本项目在 Python 3.14.8 环境验证通过）
- MySQL 8.0+ 或 SQLite 3.25+（运行 SQL 分析层，二选一即可）

### 1. 安装依赖

```bash
pip install pandas numpy faker jieba scikit-learn
```

### 2. 生成仿真数据（① 数据层）

```bash
python python/data_generator.py
```

> 在项目根目录执行。生成 7 张互相关联的业务表到 `data/raw/`，运行结束会打印各表数据量统计（共 10,511 条）。随机种子固定为 42，任何环境生成的数据完全一致。

### 3. 执行 SQL 分析（② SQL 层）

将 `data/raw/` 下 CSV 导入数据库后，按模块执行 `sql/` 目录下 5 个脚本（表名即 CSV 文件名，无需加前缀）：

```bash
# SQLite 快捷导入示例 (一次性):
python -c "
import pandas as pd, sqlite3, glob, os
conn = sqlite3.connect('ecommerce.db')
for f in glob.glob('data/raw/*.csv'):
    name = os.path.splitext(os.path.basename(f))[0]
    pd.read_csv(f, encoding='utf-8-sig').to_sql(name, conn, index=False, if_exists='replace')
"
# 之后用任意 SQLite 客户端逐条执行 sql/*.sql 中的查询
```

### 4. 运行深度分析（③ Python 层）

```bash
python python/review_sentiment.py        # 评论情感与关键词 → review_keywords.csv / review_sentiment_summary.csv
python python/seller_segmentation.py     # 商家聚类分层 → seller_segment_result.csv / seller_segment_report.md
python python/talent_recommendation.py   # 达人智能推荐 → talent_recommendation_result.csv
```

所有结果输出到 `data/processed/`（utf-8-sig 编码，可直接用 Excel / PowerBI 打开），控制台同步打印完成提示与结果统计。

## 七、数据说明

### 仿真数据口径

| 数据表 | 行数 | 内容与口径 |
|--------|------|------------|
| seller_info | 200 | 商家档案；头部:腰部:尾部 = 1:3:6；约 80% 已入商家社群 |
| product_info | 1,000 | 商品档案；覆盖 5 大一级品类 × 各 5 个二级子品类；约 60% 入选选品库 |
| activity_signup | 275 | 4 场活动（618大促/开学季/双11大促/日常招商）的报名记录；整体商家报名覆盖率 65%；审核通过 85% / 审核中 10% / 审核拒绝 5% |
| live_record | 2,456 | 最近 30 天直播记录；日开播率 40%；含大促直播标记 |
| talent_info | 80 | 达人档案；层级 S:A:B:C ≈ 5%:20%:35%:40% |
| talent_match | 1,500 | 达人撮合记录；状态分布 选品入库20% / 意向沟通25% / 排期确认15% / 已开播30% / 合作终止10%；最终GMV仅已开播记录有值 |
| buyer_reviews | 5,000 | 买家秀评论（最近 90 天）；5 星制，平均评分约 4.3；约 15% 为精选买家秀 |

### 通用约定

- **可复现**：全局随机种子 `42`；`DATA_DATE` 以脚本运行当天为锚点，所有时间窗口（近30天/近90天/大促周期）按天偏移生成
- **ID 互相关联**：7 张表通过 `seller_id / product_id / talent_id / match_id` 串联成完整经营链路，支持任意跨表分析
- **布尔字段存 1/0**：`is_community / is_selected / is_promotion_live / is_showcase` 均以整型 1/0 存储，保证 SQL `= 1` 条件在 MySQL 与 SQLite 下行为一致
- **CSV 编码 utf-8-sig**：兼容 Excel 直接打开，中文不乱码
- **指标口径统一**：好评率 = 评分≥4 占比；差评率 = 评分≤2 占比；ROI = 最终GMV / 合作费；近7天等动态窗口由 SQL 内子查询锚定（详见 [docs/metrics_dict.md](docs/metrics_dict.md)）

### 品类体系

```text
服饰鞋包 ─ 女装 / 男装 / 鞋靴 / 箱包 / 配饰
美妆个护 ─ 护肤 / 彩妆 / 美发 / 身体护理 / 香水
家居百货 ─ 家纺 / 厨具 / 收纳 / 清洁 / 装饰
食品饮料 ─ 休闲零食 / 冲调饮品 / 粮油速食 / 生鲜 / 酒水
3C数码  ─ 手机 / 电脑 / 影音娱乐 / 智能设备 / 配件
```

## 八、许可证与说明

- 本项目代码遵循 **MIT License**，可自由使用、修改与分发
- 全部数据由 `python/data_generator.py` 仿真生成，**不包含任何真实商家、商品或用户信息**，仅用于业务分析学习与演示
- 如需将本框架接入真实业务数据，替换 `data/raw/` 数据源并保持表结构（列名）不变即可复用全部 SQL 与 Python 脚本
