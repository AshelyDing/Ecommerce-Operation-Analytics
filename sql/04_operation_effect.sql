-- ============================================================
-- 模块4: 商家运营效果复盘 (04_operation_effect.sql)
-- ============================================================
-- 数据源: data/raw/ 下 CSV 导入数据库后的同名表
--   涉及表: seller_info / live_record / buyer_reviews / product_info
-- 适用数据库: MySQL 8.0+ / SQLite 3.25+ (标准 SQL 语法)
-- 业务场景: 周期性(周/月)的运营效果复盘——
--   商家分层 GMV 贡献是否健康、商品口碑如何、开播投入是否带来产出
-- ============================================================


-- ------------------------------------------------------------
-- 查询1: 各品类商家GMV分层排行 (头部/腰部/尾部商家GMV占比)
-- 运营工作: 复盘"二八结构"是否失衡——
--   头部占比过重 → 平台风险集中, 需扶持腰部商家做梯队建设;
--   尾部占比极低 → 评估尾部商家扶持资源(流量券/培训)的投产比
-- 口径: 分层GMV占比 = 该层级商家 GMV / 品类总 GMV × 100%
-- ------------------------------------------------------------
WITH seller_gmv AS (
    -- 每商家全周期 GMV 汇总 (每商家一行)
    SELECT
        seller_id,
        SUM(gmv) AS gmv_total
    FROM live_record
    GROUP BY seller_id
)
SELECT
    s.category                                                      AS 一级品类,
    SUM(CASE WHEN s.seller_level = '头部' THEN COALESCE(sg.gmv_total, 0) ELSE 0 END) AS 头部GMV,
    SUM(CASE WHEN s.seller_level = '腰部' THEN COALESCE(sg.gmv_total, 0) ELSE 0 END) AS 腰部GMV,
    SUM(CASE WHEN s.seller_level = '尾部' THEN COALESCE(sg.gmv_total, 0) ELSE 0 END) AS 尾部GMV,
    ROUND(SUM(COALESCE(sg.gmv_total, 0)), 2)                        AS 品类总GMV,
    ROUND(SUM(CASE WHEN s.seller_level = '头部' THEN COALESCE(sg.gmv_total, 0) ELSE 0 END) * 100.0
          / NULLIF(SUM(COALESCE(sg.gmv_total, 0)), 0), 2)           AS 头部GMV占比_pct,
    ROUND(SUM(CASE WHEN s.seller_level = '腰部' THEN COALESCE(sg.gmv_total, 0) ELSE 0 END) * 100.0
          / NULLIF(SUM(COALESCE(sg.gmv_total, 0)), 0), 2)           AS 腰部GMV占比_pct,
    ROUND(SUM(CASE WHEN s.seller_level = '尾部' THEN COALESCE(sg.gmv_total, 0) ELSE 0 END) * 100.0
          / NULLIF(SUM(COALESCE(sg.gmv_total, 0)), 0), 2)           AS 尾部GMV占比_pct
FROM seller_info s
LEFT JOIN seller_gmv sg
    ON s.seller_id = sg.seller_id
GROUP BY s.category
ORDER BY 品类总GMV DESC;


-- ------------------------------------------------------------
-- 查询2: 买家秀好评率与评分分布 (分品类)
-- 运营工作: 商品口碑复盘——
--   差评率高的品类 → 联动品控/供应链排查质量问题, 收紧选品标准;
--   好评率与评分分布 → 评估该品类买家秀素材供给能力 (可反哺商详页)
-- 口径: 好评率 = 4星及以上评论占比 × 100%;
--       差评率 = 2星及以下评论占比 × 100%
-- ------------------------------------------------------------
SELECT
    p.category                                                      AS 一级品类,
    COUNT(*)                                                        AS 评论总数,
    ROUND(AVG(r.rating), 2)                                         AS 平均评分,
    SUM(CASE WHEN r.rating >= 4 THEN 1 ELSE 0 END)                  AS 好评数,
    ROUND(SUM(CASE WHEN r.rating >= 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 好评率_pct,
    SUM(CASE WHEN r.rating <= 2 THEN 1 ELSE 0 END)                  AS 差评数,
    ROUND(SUM(CASE WHEN r.rating <= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS 差评率_pct,
    SUM(CASE WHEN r.rating = 5 THEN 1 ELSE 0 END)                   AS 五星数,
    SUM(CASE WHEN r.rating = 4 THEN 1 ELSE 0 END)                   AS 四星数,
    SUM(CASE WHEN r.rating = 3 THEN 1 ELSE 0 END)                   AS 三星数,
    SUM(CASE WHEN r.rating = 2 THEN 1 ELSE 0 END)                   AS 二星数,
    SUM(CASE WHEN r.rating = 1 THEN 1 ELSE 0 END)                   AS 一星数
FROM buyer_reviews r
JOIN product_info p
    ON r.product_id = p.product_id
GROUP BY p.category
ORDER BY 好评率_pct DESC;


-- ------------------------------------------------------------
-- 查询3: 商家开播频次与GMV的相关性统计
-- 运营工作: 验证"勤开播 = 高产出"的运营假设——
--   若场均GMV随频次上升 → 激励商家提高开播频次 (开播任务/流量券);
--   "0场"商家数量多 → 联动社群做开播冷启动培训, 降低开播门槛
-- 口径: 开播频次 = 近30天累计开播场次 (数据快照本身为最近30天);
--       商家平均GMV = 该组商家 GMV 总和 / 商家数;
--       场均GMV = 该组 GMV 总和 / 开播场次总和
-- ------------------------------------------------------------
WITH seller_stats AS (
    SELECT
        seller_id,
        COUNT(*) AS live_cnt,
        SUM(gmv) AS gmv_total
    FROM live_record
    GROUP BY seller_id
)
SELECT
    CASE
        WHEN ss.live_cnt IS NULL OR ss.live_cnt = 0 THEN '0场'
        WHEN ss.live_cnt <= 5  THEN '1-5场'
        WHEN ss.live_cnt <= 10 THEN '6-10场'
        WHEN ss.live_cnt <= 20 THEN '11-20场'
        ELSE '20场以上'
    END                                                          AS 开播频次分层,
    COUNT(*)                                                     AS 商家数,
    ROUND(AVG(COALESCE(ss.live_cnt, 0)), 2)                      AS 平均开播场次,
    ROUND(AVG(COALESCE(ss.gmv_total, 0)), 2)                     AS 商家平均GMV,
    ROUND(SUM(COALESCE(ss.gmv_total, 0))
          / NULLIF(SUM(COALESCE(ss.live_cnt, 0)), 0), 2)         AS 场均GMV
FROM seller_info s
LEFT JOIN seller_stats ss
    ON s.seller_id = ss.seller_id
GROUP BY 开播频次分层
ORDER BY MIN(COALESCE(ss.live_cnt, 0));
