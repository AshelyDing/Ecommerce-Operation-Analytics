-- ============================================================
-- 模块2: 商家社群运营分析 (02_seller_community.sql)
-- ============================================================
-- 数据源: data/raw/ 下 CSV 导入数据库后的同名表
--   涉及表: seller_info / activity_signup / live_record
-- 适用数据库: MySQL 8.0+ / SQLite 3.25+ (标准 SQL 语法)
-- 业务场景: 商家社群是平台日常触达商家的核心阵地, 本模块回答三个问题:
--   1) 各品类社群覆盖做得怎么样 (渗透率)?
--   2) 入群是否真的带来商家活跃度提升 (对比验证)?
--   3) 各层级商家对社群运营大盘的贡献有多大 (资源该往哪投)?
-- ============================================================


-- ------------------------------------------------------------
-- 查询1: 各品类商家社群渗透率与层级分布
-- 运营工作: 评估各品类社群建设进度——
--   渗透率低的品类优先做拉新入群动作 (入驻即拉群/开播引导入群);
--   结合层级分布判断品类商家结构, 尾部占比过高的品类需重点帮扶
-- 口径: 社群渗透率 = 已入群商家数 / 品类商家总数 × 100%
-- ------------------------------------------------------------
SELECT
    category                                                         AS 一级品类,
    COUNT(*)                                                         AS 商家总数,
    SUM(CASE WHEN is_community = 1 THEN 1 ELSE 0 END)                AS 入群商家数,
    ROUND(SUM(CASE WHEN is_community = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 社群渗透率_pct,
    SUM(CASE WHEN seller_level = '头部' THEN 1 ELSE 0 END)           AS 头部商家数,
    SUM(CASE WHEN seller_level = '腰部' THEN 1 ELSE 0 END)           AS 腰部商家数,
    SUM(CASE WHEN seller_level = '尾部' THEN 1 ELSE 0 END)           AS 尾部商家数
FROM seller_info
GROUP BY category
ORDER BY 社群渗透率_pct DESC;


-- ------------------------------------------------------------
-- 查询2: 社群内商家 vs 社群外商家的活动报名率、开播率对比
-- 运营工作: 验证社群运营的实际价值——入群商家是否更活跃?
--   若入群组显著领先 → 向上汇报社群价值, 争取更多社群运营资源;
--   若差异不明显 → 反思社群内容与触达频次, 优化社群运营策略
-- 口径: 报名率 = 报名商家数 / 组内商家总数 (商家去重);
--       开播商家占比 = 近7天开播过的商家数 / 组内商家总数;
--       近7天 = live_record 中最近 7 个有直播数据的日期
-- ------------------------------------------------------------
WITH live_agg AS (
    -- 近7天每商家的开播场次 (每商家一行, 避免多表连接行数膨胀)
    SELECT
        seller_id,
        COUNT(*) AS live_cnt
    FROM live_record
    WHERE live_date >= (
        SELECT MIN(d)
        FROM (
            SELECT DISTINCT live_date AS d
            FROM live_record
            ORDER BY live_date DESC
            LIMIT 7
        ) t
    )
    GROUP BY seller_id
),
signup_agg AS (
    -- 报名商家去重 (每商家一行)
    SELECT
        seller_id,
        1 AS is_signup
    FROM activity_signup
    GROUP BY seller_id
)
SELECT
    s.is_community                                           AS 是否入群,
    COUNT(*)                                                 AS 商家数,
    SUM(CASE WHEN sa.is_signup = 1 THEN 1 ELSE 0 END)        AS 报名商家数,
    ROUND(SUM(CASE WHEN sa.is_signup = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 报名率_pct,
    SUM(CASE WHEN la.seller_id IS NOT NULL THEN 1 ELSE 0 END) AS 近7天开播商家数,
    ROUND(SUM(CASE WHEN la.seller_id IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 开播商家占比_pct,
    SUM(COALESCE(la.live_cnt, 0))                            AS 近7天开播场次
FROM seller_info s
LEFT JOIN signup_agg sa
    ON s.seller_id = sa.seller_id
LEFT JOIN live_agg la
    ON s.seller_id = la.seller_id
GROUP BY s.is_community
ORDER BY s.is_community DESC;


-- ------------------------------------------------------------
-- 查询3: 各层级商家的社群活跃贡献度 (GMV占比、报名占比)
-- 运营工作: 分析"社群里"各层级商家对平台大盘的贡献——
--   头部入群商家贡献 GMV 大 → 提供 VIP 服务 (专属答疑/流量加白);
--   尾部贡献弱但数量多 → 用标准化社群 SOP 批量运营, 控制服务成本
-- 口径: GMV占全平台比 = 该层级入群商家 GMV / 全平台直播 GMV × 100%;
--       报名占全平台比 = 该层级入群商家报名数 / 全平台报名商家总数 × 100%
-- ------------------------------------------------------------
WITH live_by_seller AS (
    -- 每商家全周期 GMV 汇总 (每商家一行)
    SELECT
        seller_id,
        SUM(gmv) AS seller_gmv
    FROM live_record
    GROUP BY seller_id
),
signup_sellers AS (
    -- 报名商家去重
    SELECT DISTINCT seller_id
    FROM activity_signup
)
SELECT
    s.seller_level                                               AS 商家层级,
    COUNT(DISTINCT s.seller_id)                                  AS 入群商家数,
    ROUND(SUM(COALESCE(lb.seller_gmv, 0)), 2)                    AS 入群商家GMV,
    ROUND(SUM(COALESCE(lb.seller_gmv, 0)) * 100.0
          / NULLIF((SELECT SUM(gmv) FROM live_record), 0), 2)    AS GMV占全平台比_pct,
    SUM(CASE WHEN ss.seller_id IS NOT NULL THEN 1 ELSE 0 END)    AS 报名商家数,
    ROUND(SUM(CASE WHEN ss.seller_id IS NOT NULL THEN 1 ELSE 0 END) * 100.0
          / NULLIF((SELECT COUNT(DISTINCT seller_id) FROM activity_signup), 0), 2) AS 报名占全平台比_pct
FROM seller_info s
LEFT JOIN live_by_seller lb
    ON s.seller_id = lb.seller_id
LEFT JOIN signup_sellers ss
    ON s.seller_id = ss.seller_id
WHERE s.is_community = 1
GROUP BY s.seller_level
ORDER BY CASE s.seller_level WHEN '头部' THEN 1 WHEN '腰部' THEN 2 ELSE 3 END;
