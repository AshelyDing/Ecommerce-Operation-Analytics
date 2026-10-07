-- ============================================================
-- 模块5: 大促活动全链路分析 (05_promotion_analysis.sql)
-- ============================================================
-- 数据源: data/raw/ 下 CSV 导入数据库后的同名表
--   涉及表: activity_signup / live_record / seller_info
-- 适用数据库: MySQL 8.0+ / SQLite 3.25+ (标准 SQL 语法)
-- 业务场景: 大促(618/开学季/双11/日常招商)全链路复盘——
--   报名 → 审核 → 大促开播 → GMV 产出, 沉淀可复用的大促打法
-- 数据口径说明: activity_signup 保留每场活动的报名与审核明细;
--   live_record.is_promotion_live 标记该场直播是否处于大促活动期。
--   直播表不区分具体哪场大促, 因此"分活动"指标从报名表出,
--   "大促 vs 日常"效果对比从直播表出, 两者互补还原大促全链路
-- ============================================================


-- ------------------------------------------------------------
-- 查询1: 多场大促核心指标横向对比
-- 运营工作: 每场大促结束后复盘对比, 评估活动 IP 的号召力与执行质量
-- 口径: 报名商家数按商家去重; 审核通过率 = 通过记录 / 报名记录 × 100%
-- ------------------------------------------------------------

-- 1-1) 报名侧: 各场活动的招商报名情况
SELECT
    activity_id                                                   AS 活动ID,
    activity_name                                                 AS 活动名称,
    COUNT(DISTINCT seller_id)                                     AS 报名商家数,
    COUNT(*)                                                      AS 报名记录数,
    SUM(CASE WHEN audit_status = '审核通过' THEN 1 ELSE 0 END)    AS 审核通过数,
    ROUND(SUM(CASE WHEN audit_status = '审核通过' THEN 1 ELSE 0 END) * 100.0
          / NULLIF(COUNT(*), 0), 2)                               AS 审核通过率_pct,
    ROUND(AVG(signup_products), 2)                                AS 平均报名商品数
FROM activity_signup
GROUP BY activity_id, activity_name
ORDER BY activity_id;


-- 1-2) 直播侧: 大促直播 vs 日常直播的核心产出对比
SELECT
    is_promotion_live                                             AS 是否大促直播,
    COUNT(*)                                                      AS 开播场次,
    ROUND(SUM(gmv), 2)                                            AS 总GMV,
    SUM(orders)                                                   AS 总订单量,
    ROUND(SUM(orders) * 1.0 / NULLIF(COUNT(*), 0), 2)             AS 场均订单,
    ROUND(SUM(views) * 1.0 / NULLIF(COUNT(*), 0), 2)              AS 场均观看人次
FROM live_record
GROUP BY is_promotion_live
ORDER BY is_promotion_live DESC;


-- ------------------------------------------------------------
-- 查询2: 大促期间各品类GMV增长贡献度
-- 运营工作: 大促复盘时看"谁撑起了大促"——
--   贡献度高的品类 → 下场大促优先给流量/坑位资源;
--   增幅为负的品类 → 大促玩法与该品类不适配 (如客单价过低),
--   调整活动设计或单独设计品类日
-- 口径: 大促GMV贡献度 = 品类大促GMV / 全平台大促GMV × 100%;
--       增幅 = (大促场均GMV - 日常场均GMV) / 日常场均GMV × 100%
--       (用场均口径消除大促/日常开播场次不同的影响)
-- ------------------------------------------------------------
WITH cat_stats AS (
    -- 每品类: 大促与日常的 GMV、场次 (一行一品类)
    SELECT
        s.category                                                AS category,
        SUM(CASE WHEN l.is_promotion_live = 1 THEN l.gmv ELSE 0 END) AS promo_gmv,
        SUM(CASE WHEN l.is_promotion_live = 1 THEN 1 ELSE 0 END)  AS promo_cnt,
        SUM(CASE WHEN l.is_promotion_live = 0 THEN l.gmv ELSE 0 END) AS daily_gmv,
        SUM(CASE WHEN l.is_promotion_live = 0 THEN 1 ELSE 0 END)  AS daily_cnt
    FROM live_record l
    JOIN seller_info s
        ON l.seller_id = s.seller_id
    GROUP BY s.category
)
SELECT
    category                                                      AS 一级品类,
    ROUND(promo_gmv, 2)                                           AS 大促GMV,
    ROUND(promo_gmv * 100.0
          / NULLIF((SELECT SUM(promo_gmv) FROM cat_stats), 0), 2) AS 大促GMV贡献度_pct,
    ROUND(promo_gmv / NULLIF(promo_cnt, 0), 2)                    AS 大促场均GMV,
    ROUND(daily_gmv / NULLIF(daily_cnt, 0), 2)                    AS 日常场均GMV,
    ROUND((promo_gmv / NULLIF(promo_cnt, 0) - daily_gmv / NULLIF(daily_cnt, 0)) * 100.0
          / NULLIF(daily_gmv / NULLIF(daily_cnt, 0), 0), 2)       AS 场均GMV增幅_pct
FROM cat_stats
ORDER BY promo_gmv DESC;


-- ------------------------------------------------------------
-- 查询3: 大促商家参与度分层统计 (各层级商家参与率)
-- 运营工作: 评估大促对各层级商家的渗透——
--   头部参与率低 → 活动利益点不够, 升级专属玩法 (S级会场/独家权益);
--   尾部参与率低 → 报名门槛或理解成本高, 用简化版玩法 + 社群宣导覆盖
-- 口径: 报名参与率 = 报过活动名的商家数 / 该层级商家总数 × 100%;
--       开播参与率 = 大促期间开播过的商家数 / 该层级商家总数 × 100%
-- ------------------------------------------------------------
WITH level_total AS (
    -- 各层级商家总数
    SELECT
        seller_level,
        COUNT(*) AS total_cnt
    FROM seller_info
    GROUP BY seller_level
),
signup_by_level AS (
    -- 各层级报名商家数 (去重)
    SELECT
        s.seller_level,
        COUNT(DISTINCT s.seller_id) AS signup_cnt
    FROM seller_info s
    JOIN activity_signup a
        ON s.seller_id = a.seller_id
    GROUP BY s.seller_level
),
promo_live_by_level AS (
    -- 各层级大促开播商家数与产出
    SELECT
        s.seller_level,
        COUNT(DISTINCT l.seller_id) AS promo_live_cnt,
        COUNT(*)                    AS promo_live_sessions,
        ROUND(SUM(l.gmv), 2)        AS promo_gmv
    FROM live_record l
    JOIN seller_info s
        ON l.seller_id = s.seller_id
    WHERE l.is_promotion_live = 1
    GROUP BY s.seller_level
)
SELECT
    t.seller_level                                                AS 商家层级,
    t.total_cnt                                                   AS 商家总数,
    COALESCE(sb.signup_cnt, 0)                                    AS 报名商家数,
    ROUND(COALESCE(sb.signup_cnt, 0) * 100.0 / t.total_cnt, 2)    AS 报名参与率_pct,
    COALESCE(pl.promo_live_cnt, 0)                                AS 大促开播商家数,
    ROUND(COALESCE(pl.promo_live_cnt, 0) * 100.0 / t.total_cnt, 2) AS 大促开播参与率_pct,
    COALESCE(pl.promo_live_sessions, 0)                           AS 大促开播场次,
    COALESCE(pl.promo_gmv, 0)                                     AS 大促GMV
FROM level_total t
LEFT JOIN signup_by_level sb
    ON t.seller_level = sb.seller_level
LEFT JOIN promo_live_by_level pl
    ON t.seller_level = pl.seller_level
ORDER BY CASE t.seller_level WHEN '头部' THEN 1 WHEN '腰部' THEN 2 ELSE 3 END;
