-- ============================================================
-- 模块3: 达人撮合漏斗分析 (03_talent_match.sql)
-- ============================================================
-- 数据源: data/raw/ 下 CSV 导入数据库后的同名表
--   涉及表: talent_match / talent_info / product_info
-- 适用数据库: MySQL 8.0+ / SQLite 3.25+ (标准 SQL 语法)
-- 业务场景: 平台达人撮合业务 (商家选品库 → 达人建联 → 排期 → 开播带货),
--   本模块监控撮合漏斗转化、评估不同层级达人的带货效果与品类匹配效率
-- 口径说明: match_status 为撮合记录当前所处环节 (互斥状态);
--   漏斗采用累计口径 = "已进入该环节及之后环节"的记录占比;
--   final_gmv 仅"已开播"状态有值, 其余状态为空
-- ============================================================


-- ------------------------------------------------------------
-- 查询1: 达人撮合全链路漏斗转化率
-- 运营工作: 周度复盘撮合漏斗, 定位卡点环节——
--   入库→沟通掉量多 → 选品库商品不够吸引达人, 优化选品结构与佣金;
--   排期→开播掉量多 → 达人档期管理或样品物流拖后腿, 排查履约;
--   合作终止率走高 → 排查合作体验与纠纷, 完善合作保障条款
-- 口径: 累计漏斗——已进入当前环节及后续环节的撮合记录计入当前环节;
--       转化率 = 下一环节累计数 / 上一环节累计数 × 100%
-- ------------------------------------------------------------
SELECT
    COUNT(*) AS 选品入库数,
    SUM(CASE WHEN match_status IN ('意向沟通', '排期确认', '已开播', '合作终止')
             THEN 1 ELSE 0 END) AS 意向沟通数,
    SUM(CASE WHEN match_status IN ('排期确认', '已开播', '合作终止')
             THEN 1 ELSE 0 END) AS 排期确认数,
    SUM(CASE WHEN match_status = '已开播' THEN 1 ELSE 0 END)     AS 已开播数,
    SUM(CASE WHEN match_status = '合作终止' THEN 1 ELSE 0 END)   AS 合作终止数,
    ROUND(SUM(CASE WHEN match_status IN ('意向沟通', '排期确认', '已开播', '合作终止')
                   THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2)     AS 入库到沟通转化率_pct,
    ROUND(SUM(CASE WHEN match_status IN ('排期确认', '已开播', '合作终止')
                   THEN 1 ELSE 0 END) * 100.0
          / NULLIF(SUM(CASE WHEN match_status IN ('意向沟通', '排期确认', '已开播', '合作终止')
                            THEN 1 ELSE 0 END), 0), 2)           AS 沟通到排期转化率_pct,
    ROUND(SUM(CASE WHEN match_status = '已开播' THEN 1 ELSE 0 END) * 100.0
          / NULLIF(SUM(CASE WHEN match_status IN ('排期确认', '已开播', '合作终止')
                            THEN 1 ELSE 0 END), 0), 2)           AS 排期到开播转化率_pct,
    ROUND(SUM(CASE WHEN match_status = '已开播' THEN 1 ELSE 0 END) * 100.0
          / COUNT(*), 2)                                         AS 整体开播成功率_pct
FROM talent_match;


-- ------------------------------------------------------------
-- 查询2: 各品类达人撮合成功率与平均最终GMV对比
-- 运营工作: 识别"好撮合、好产出"的优势品类与"难撮合"品类——
--   成功率低 + GMV 低的品类 → 该垂类达人供给不足, 引入更多达人;
--   GMV 高但成功率低的品类 → 聚焦头部达人合作, 提高单品产出
-- 口径: 撮合成功率 = 已开播记录数 / 撮合记录总数 × 100%;
--       平均最终GMV 仅统计已开播记录 (其余状态 final_gmv 为空)
-- ------------------------------------------------------------
SELECT
    p.category                                                       AS 一级品类,
    COUNT(*)                                                         AS 撮合次数,
    SUM(CASE WHEN m.match_status = '已开播' THEN 1 ELSE 0 END)       AS 已开播次数,
    ROUND(SUM(CASE WHEN m.match_status = '已开播' THEN 1 ELSE 0 END) * 100.0
          / COUNT(*), 2)                                             AS 撮合成功率_pct,
    ROUND(AVG(CASE WHEN m.match_status = '已开播' THEN m.final_gmv END), 2) AS 平均最终GMV,
    ROUND(SUM(COALESCE(m.final_gmv, 0)), 2)                          AS 最终GMV合计
FROM talent_match m
JOIN product_info p
    ON m.product_id = p.product_id
GROUP BY p.category
ORDER BY 撮合成功率_pct DESC;


-- ------------------------------------------------------------
-- 查询3: 不同层级达人带货效果排行 (场均GMV、平均ROI、合作次数)
-- 运营工作: 评估达人分层运营策略——
--   对比"实际ROI"与达人档案"标注平均ROI"的差异, 校准达人评级;
--   ROI 高且档期多的层级 → 加大撮合投放; 头部费用高需算清投产比
-- 口径: 场均GMV = 已开播记录最终GMV合计 / 已开播场次;
--       实际平均ROI = AVG(单场最终GMV / 该达人合作费), 仅统计已开播
-- ------------------------------------------------------------
SELECT
    t.tier                                                           AS 达人层级,
    COUNT(*)                                                         AS 合作次数,
    SUM(CASE WHEN m.match_status = '已开播' THEN 1 ELSE 0 END)       AS 已开播场次,
    ROUND(SUM(COALESCE(m.final_gmv, 0))
          / NULLIF(SUM(CASE WHEN m.match_status = '已开播' THEN 1 ELSE 0 END), 0), 2) AS 场均GMV,
    ROUND(AVG(CASE WHEN m.match_status = '已开播'
                   THEN m.final_gmv / NULLIF(t.cooperation_fee, 0) END), 2) AS 实际平均ROI,
    ROUND(AVG(t.avg_roi), 2)                                         AS 达人标注平均ROI
FROM talent_match m
JOIN talent_info t
    ON m.talent_id = t.talent_id
GROUP BY t.tier
ORDER BY 场均GMV DESC;


-- ------------------------------------------------------------
-- 查询4: 品类 × 达人层级 匹配效果矩阵 (撮合成功率维度)
-- 运营工作: 输出品类×层级的匹配效果热力矩阵 (可导入 BI 透视)——
--   高成功率组合 (如 食品饮料×B级) → 沉淀为撮合策略模板批量复制;
--   低成功率组合 → 调整佣金/坑位费政策或暂停该类撮合
-- 说明: 本查询输出长表, 在 Power BI / Excel 中以"一级品类"为行、
--       "达人层级"为列做透视, 即得成功率矩阵热力图
-- ------------------------------------------------------------
SELECT
    p.category                                                       AS 一级品类,
    t.tier                                                           AS 达人层级,
    COUNT(*)                                                         AS 撮合次数,
    SUM(CASE WHEN m.match_status = '已开播' THEN 1 ELSE 0 END)       AS 已开播次数,
    ROUND(SUM(CASE WHEN m.match_status = '已开播' THEN 1 ELSE 0 END) * 100.0
          / COUNT(*), 2)                                             AS 撮合成功率_pct
FROM talent_match m
JOIN product_info p
    ON m.product_id = p.product_id
JOIN talent_info t
    ON m.talent_id = t.talent_id
GROUP BY p.category, t.tier
ORDER BY p.category, CASE t.tier WHEN 'S' THEN 1 WHEN 'A' THEN 2 WHEN 'B' THEN 3 ELSE 4 END;
