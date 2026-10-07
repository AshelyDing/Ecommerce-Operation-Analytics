-- ============================================================
-- 模块1: 日常运营指标监控 (01_daily_monitoring.sql)
-- ============================================================
-- 数据源: data/raw/ 下 CSV 导入数据库后的同名表
--   涉及表: seller_info / activity_signup / live_record
-- 适用数据库: MySQL 8.0+ / SQLite 3.25+ (标准 SQL 语法)
-- 业务场景: 运营日报/周报的每日监控, 供晨会复盘与日常巡检
-- 口径说明: "近7天" = live_record 中最近 7 个有直播数据的日期
--   (以数据最新日期为锚点动态计算, 不写死具体日期, 数据重跑后依然有效)
-- ============================================================


-- ------------------------------------------------------------
-- 查询1: 各品类活动报名率与审核通过率
-- 运营工作: 每日巡检各品类招商健康度——
--   报名率偏低的品类 → 运营侧加强招商触达与激励宣导;
--   审核通过率过高/过低 → 排查审核口径是否过松/过严,
--   避免低质商家入场或误伤优质商家
-- 口径: 报名率 = 报名商家数 / 品类商家总数 (商家去重);
--       审核通过率 = 审核通过记录数 / 报名记录总数
-- ------------------------------------------------------------
SELECT
    s.category                                                                AS 一级品类,
    COUNT(DISTINCT s.seller_id)                                               AS 商家总数,
    COUNT(DISTINCT a.seller_id)                                               AS 报名商家数,
    ROUND(COUNT(DISTINCT a.seller_id) * 100.0 / COUNT(DISTINCT s.seller_id), 2) AS 报名率_pct,
    COUNT(*)                                                                  AS 报名记录数,
    SUM(CASE WHEN a.audit_status = '审核通过' THEN 1 ELSE 0 END)              AS 审核通过数,
    ROUND(SUM(CASE WHEN a.audit_status = '审核通过' THEN 1 ELSE 0 END) * 100.0
          / NULLIF(COUNT(*), 0), 2)                                           AS 审核通过率_pct
FROM seller_info s
LEFT JOIN activity_signup a
    ON s.seller_id = a.seller_id
GROUP BY s.category
ORDER BY 报名率_pct DESC;


-- ------------------------------------------------------------
-- 查询2: 近7天各品类日均开播场次、总GMV、订单量、场均观看人次
-- 运营工作: 每日监控各品类内容供给量(开播场次)与转化效率(GMV/观看)——
--   供给不足的品类 → 联动商家运营团队做开播动员与流量扶持;
--   场均观看低的品类 → 排查选品/直播间装修/投流策略
-- 口径: 日均开播场次 = 场次 / 窗口内实际活跃天数;
--       场均观看人次 = 总观看 / 总场次 (衡量直播间引流能力)
-- ------------------------------------------------------------
SELECT
    s.category                                               AS 一级品类,
    COUNT(*)                                                 AS 开播场次,
    COUNT(DISTINCT l.live_date)                              AS 活跃天数,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT l.live_date), 2)   AS 日均开播场次,
    ROUND(SUM(l.gmv), 2)                                     AS 总GMV,
    SUM(l.orders)                                            AS 总订单量,
    ROUND(SUM(l.views) * 1.0 / NULLIF(COUNT(*), 0), 2)       AS 场均观看人次
FROM live_record l
JOIN seller_info s
    ON l.seller_id = s.seller_id
WHERE l.live_date >= (
    -- 近7天锚点: 取直播表最近 7 个有数据日期的第一天
    SELECT MIN(d)
    FROM (
        SELECT DISTINCT live_date AS d
        FROM live_record
        ORDER BY live_date DESC
        LIMIT 7
    ) t
)
GROUP BY s.category
ORDER BY 总GMV DESC;


-- ------------------------------------------------------------
-- 查询3: 近7天低开播商家清单 (开播天数 < 2 天)
-- 运营工作: 输出给商家社群运营做定向触达——
--   已入群商家 (is_community = 1) 走社群私聊/群公告唤醒;
--   未入群商家走客服/招商同学一对一跟进, 同时可顺带推进入群;
--   优先联系粉丝量大、层级高的商家 (沉睡高价值商家)
-- 口径: 开播天数 = 近7天窗口内该商家的开播天数 (0 或 1 天视为低开播)
-- ------------------------------------------------------------
SELECT
    s.seller_id,
    s.seller_name,
    s.category                                               AS 一级品类,
    s.seller_level                                           AS 商家层级,
    s.fans_count                                             AS 粉丝数,
    s.is_community                                           AS 是否入群,
    COUNT(DISTINCT l.live_date)                              AS 近7天开播天数
FROM seller_info s
LEFT JOIN live_record l
    ON s.seller_id = l.seller_id
    AND l.live_date >= (
        SELECT MIN(d)
        FROM (
            SELECT DISTINCT live_date AS d
            FROM live_record
            ORDER BY live_date DESC
            LIMIT 7
        ) t
    )
GROUP BY s.seller_id, s.seller_name, s.category, s.seller_level,
         s.fans_count, s.is_community
HAVING COUNT(DISTINCT l.live_date) < 2
ORDER BY s.fans_count DESC;
