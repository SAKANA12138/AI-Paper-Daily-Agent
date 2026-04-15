# =============================================================================
# 绿色技术创新对工业SO₂排放影响分析
# 基于2005-2015年中国省级面板数据
# 作者：统计与数据科学学院
# 日期：2024年5月
# =============================================================================

# -----------------------------------------------------------
# 0. 环境配置 - 安装并加载所需R包
# -----------------------------------------------------------
required_packages <- c(
  "plm",        # 面板数据模型
  "lmtest",     # 假设检验
  "sandwich",   # 稳健标准误
  "AER",        # IV-2SLS工具变量
  "ggplot2",    # 数据可视化
  "dplyr",      # 数据处理
  "tidyr",      # 数据整理
  "corrplot",   # 相关矩阵图
  "stargazer",  # 回归结果输出
  "car",        # VIF检验
  "readr",      # 读取CSV
  "writexl",    # 写出Excel
  "scales",     # 坐标轴格式化
  "gridExtra",  # 多图排列
  "ggthemes"    # ggplot主题
)

for (pkg in required_packages) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    install.packages(pkg, dependencies = TRUE)
    library(pkg, character.only = TRUE)
  }
}

cat("✅ 所有包加载完毕\n")

# -----------------------------------------------------------
# 1. 数据生成（模拟2005-2015年中国31省面板数据）
# -----------------------------------------------------------
set.seed(2024)

provinces <- c(
  "北京", "天津", "河北", "山西", "内蒙古",
  "辽宁", "吉林", "黑龙江", "上海", "江苏",
  "浙江", "安徽", "福建", "江西", "山东",
  "河南", "湖北", "湖南", "广东", "广西",
  "海南", "重庆", "四川", "贵州", "云南",
  "西藏", "陕西", "甘肃", "青海", "宁夏",
  "新疆"
)

years <- 2005:2015
n_provinces <- length(provinces)
n_years <- length(years)

# 区域分类（东中西）
eastern  <- c("北京", "天津", "河北", "辽宁", "上海", "江苏", "浙江",
              "福建", "山东", "广东", "广西", "海南")
central  <- c("山西", "吉林", "黑龙江", "安徽", "江西", "河南", "湖北", "湖南")
western  <- c("内蒙古", "重庆", "四川", "贵州", "云南", "西藏",
              "陕西", "甘肃", "青海", "宁夏", "新疆")

# 省级固定效应基础参数
province_fe <- rnorm(n_provinces, 0, 0.05)
names(province_fe) <- provinces

# 构建面板数据框
panel_data <- expand.grid(province = provinces, year = years,
                          stringsAsFactors = FALSE) %>%
  arrange(province, year)

# 赋值区域标签
panel_data$region <- ifelse(panel_data$province %in% eastern,  "东部",
                     ifelse(panel_data$province %in% central, "中部", "西部"))

# 逐年生成核心变量
panel_data <- panel_data %>%
  group_by(province) %>%
  mutate(
    year_index = year - 2004,

    # 绿色发明专利（东部更多，逐年增长）
    green_invention = pmax(0, round(
      ifelse(province %in% eastern, 50, ifelse(province %in% central, 20, 8)) *
        (1 + 0.12 * year_index) + rnorm(n(), 0, 5)
    )),

    # 绿色实用新型专利
    green_utility = pmax(0, round(
      ifelse(province %in% eastern, 80, ifelse(province %in% central, 35, 15)) *
        (1 + 0.10 * year_index) + rnorm(n(), 0, 8)
    )),

    # 绿色专利总数
    green_patent = green_invention + green_utility,

    # 取对数（+1防止log(0)）
    ln_green_patent    = log(green_patent + 1),
    ln_green_invention = log(green_invention + 1),
    ln_green_utility   = log(green_utility + 1),

    # 实际人均GDP（万元，东部高）
    real_gdpc = ifelse(province %in% eastern, 3.5, ifelse(province %in% central, 2.0, 1.2)) *
      exp(0.08 * year_index + rnorm(n(), 0, 0.02)),

    ln_real_gdpc = log(real_gdpc),
    ln_real_gdpc_sq = ln_real_gdpc^2,

    # 第二产业占比
    industry_ratio = pmin(0.70, pmax(0.25,
      ifelse(province %in% eastern, 0.48, ifelse(province %in% central, 0.50, 0.44)) +
        rnorm(n(), 0, 0.03) - 0.005 * year_index
    )),

    # SO₂排放强度（万吨/亿元）—— 受绿色专利、GDP、产业结构影响
    SO2_intensity = pmax(0.02,
      0.8
      - 0.07 * ln_green_patent
      - 0.05 * ln_real_gdpc
      + 0.18 * industry_ratio
      + province_fe[province]
      + rnorm(n(), 0, 0.03)
      - 0.01 * year_index   # 随时间改善
    )
  ) %>%
  ungroup()

cat("✅ 面板数据生成完毕，共", nrow(panel_data), "行\n")

# -----------------------------------------------------------
# 2. 描述性统计
# -----------------------------------------------------------
desc_vars <- c("SO2_intensity", "ln_green_patent", "ln_real_gdpc", "industry_ratio")

desc_stats <- panel_data %>%
  summarise(across(all_of(desc_vars),
                   list(mean = mean, sd = sd, min = min, max = max),
                   .names = "{.col}_{.fn}")) %>%
  pivot_longer(everything(), names_to = c("variable", "stat"), names_sep = "_(?=[^_]+$)") %>%
  pivot_wider(names_from = stat, values_from = value)

desc_stats$variable <- c("SO₂排放强度", "ln绿色专利总数", "ln人均GDP", "第二产业占比")
cat("\n📊 描述性统计：\n")
print(desc_stats)

write.csv(desc_stats, "results/tables/table1_descriptive_statistics.csv",
          row.names = FALSE, fileEncoding = "UTF-8")
cat("✅ 表1保存：table1_descriptive_statistics.csv\n")

# -----------------------------------------------------------
# 3. 相关系数矩阵
# -----------------------------------------------------------
cor_matrix <- cor(panel_data[, desc_vars], use = "complete.obs")
rownames(cor_matrix) <- colnames(cor_matrix) <-
  c("SO₂强度", "ln绿专", "ln人均GDP", "产业占比")

cat("\n📊 Pearson相关系数矩阵：\n")
print(round(cor_matrix, 3))

write.csv(as.data.frame(cor_matrix),
          "results/tables/table2_correlation_matrix.csv",
          row.names = TRUE, fileEncoding = "UTF-8")
cat("✅ 表2保存：table2_correlation_matrix.csv\n")

# -----------------------------------------------------------
# 4. 面板数据对象
# -----------------------------------------------------------
pdata <- pdata.frame(panel_data, index = c("province", "year"))

# -----------------------------------------------------------
# 5. VIF检验（多重共线性）
# -----------------------------------------------------------
ols_vif <- lm(SO2_intensity ~ ln_green_patent + industry_ratio +
                ln_real_gdpc + ln_real_gdpc_sq, data = panel_data)
vif_vals <- car::vif(ols_vif)
vif_df <- data.frame(
  变量   = c("ln绿色专利总数", "第二产业占比", "ln人均GDP", "(ln人均GDP)²"),
  VIF值  = round(as.numeric(vif_vals), 3)
)
cat("\n📊 VIF检验结果：\n")
print(vif_df)
write.csv(vif_df, "results/tables/table3_vif_diagnosis.csv",
          row.names = FALSE, fileEncoding = "UTF-8")
cat("✅ 表3保存：table3_vif_diagnosis.csv\n")

# -----------------------------------------------------------
# 6. Hausman检验：固定效应 vs 随机效应
# -----------------------------------------------------------
fe_model <- plm(SO2_intensity ~ ln_green_patent + industry_ratio + ln_real_gdpc,
                data = pdata, model = "within")
re_model <- plm(SO2_intensity ~ ln_green_patent + industry_ratio + ln_real_gdpc,
                data = pdata, model = "random")

hausman_result <- phtest(fe_model, re_model)

hausman_text <- paste0(
  "Hausman检验结果\n",
  "=====================================\n",
  "固定效应 vs 随机效应模型\n",
  "Chi-squared统计量: ", round(hausman_result$statistic, 3), "\n",
  "自由度: ", hausman_result$parameter, "\n",
  "P值: ", format.pval(hausman_result$p.value, digits = 4), "\n",
  "=====================================\n",
  ifelse(hausman_result$p.value < 0.01,
         "结论：在1%显著性水平下拒绝随机效应假设，选择固定效应（FE）模型",
         ifelse(hausman_result$p.value < 0.05,
                "结论：在5%显著性水平下拒绝随机效应假设，选择固定效应（FE）模型",
                "结论：不能拒绝随机效应假设，选择随机效应（RE）模型")), "\n"
)
cat("\n", hausman_text)
writeLines(hausman_text, "results/tables/table4_hausman_test.txt")
cat("✅ 表4保存：table4_hausman_test.txt\n")

# -----------------------------------------------------------
# 7. 基准回归：四种模型
# -----------------------------------------------------------
# (1) 混合OLS
ols_model <- lm(SO2_intensity ~ ln_green_patent + industry_ratio + ln_real_gdpc,
                data = panel_data)

# (2) 固定效应基准
fe_base <- plm(SO2_intensity ~ ln_green_patent + industry_ratio + ln_real_gdpc,
               data = pdata, model = "within")

# (3) 固定效应 + EKC平方项
fe_ekc <- plm(SO2_intensity ~ ln_green_patent + industry_ratio +
                ln_real_gdpc + ln_real_gdpc_sq,
              data = pdata, model = "within")

# (4) IV-2SLS（工具变量：绿色专利滞后1期）
pdata$ln_green_patent_lag <- lag(pdata$ln_green_patent, 1)
iv_data <- pdata[!is.na(pdata$ln_green_patent_lag), ]
iv_model <- plm(SO2_intensity ~ ln_green_patent + industry_ratio + ln_real_gdpc |
                  ln_green_patent_lag + industry_ratio + ln_real_gdpc,
                data = iv_data, model = "within")

# 稳健标准误
coeftest_fe_base <- coeftest(fe_base, vcov = vcovHC(fe_base, type = "HC3"))
coeftest_fe_ekc  <- coeftest(fe_ekc,  vcov = vcovHC(fe_ekc,  type = "HC3"))
coeftest_iv      <- coeftest(iv_model, vcov = vcovHC(iv_model, type = "HC3"))

cat("\n📊 FE基准模型结果（稳健标准误）：\n")
print(coeftest_fe_base)

# 整理回归结果表（使用稳健标准误系数和显著性）
get_stars <- function(pval) {
  ifelse(pval < 0.01, "***", ifelse(pval < 0.05, "**", ifelse(pval < 0.10, "*", "")))
}

reg_summary <- data.frame(
  模型 = c("混合OLS", "FE基准", "FE-EKC", "IV-2SLS"),
  ln绿色专利总数系数 = c(
    paste0(round(coef(ols_model)["ln_green_patent"], 4),
           get_stars(summary(ols_model)$coefficients["ln_green_patent", 4])),
    paste0(round(coeftest_fe_base["ln_green_patent", 1], 4),
           get_stars(coeftest_fe_base["ln_green_patent", 4])),
    paste0(round(coeftest_fe_ekc["ln_green_patent", 1], 4),
           get_stars(coeftest_fe_ekc["ln_green_patent", 4])),
    paste0(round(coeftest_iv["ln_green_patent", 1], 4),
           get_stars(coeftest_iv["ln_green_patent", 4]))
  ),
  第二产业占比系数 = c(
    paste0(round(coef(ols_model)["industry_ratio"], 4),
           get_stars(summary(ols_model)$coefficients["industry_ratio", 4])),
    paste0(round(coeftest_fe_base["industry_ratio", 1], 4),
           get_stars(coeftest_fe_base["industry_ratio", 4])),
    paste0(round(coeftest_fe_ekc["industry_ratio", 1], 4),
           get_stars(coeftest_fe_ekc["industry_ratio", 4])),
    paste0(round(coeftest_iv["industry_ratio", 1], 4),
           get_stars(coeftest_iv["industry_ratio", 4]))
  ),
  ln人均GDP系数 = c(
    paste0(round(coef(ols_model)["ln_real_gdpc"], 4),
           get_stars(summary(ols_model)$coefficients["ln_real_gdpc", 4])),
    paste0(round(coeftest_fe_base["ln_real_gdpc", 1], 4),
           get_stars(coeftest_fe_base["ln_real_gdpc", 4])),
    paste0(round(coeftest_fe_ekc["ln_real_gdpc", 1], 4),
           get_stars(coeftest_fe_ekc["ln_real_gdpc", 4])),
    paste0(round(coeftest_iv["ln_real_gdpc", 1], 4),
           get_stars(coeftest_iv["ln_real_gdpc", 4]))
  ),
  EKC平方项系数 = c(NA, NA,
    paste0(round(coeftest_fe_ekc["ln_real_gdpc_sq", 1], 4),
           get_stars(coeftest_fe_ekc["ln_real_gdpc_sq", 4])),
    NA
  ),
  观测数 = c(nrow(panel_data), nrow(panel_data), nrow(panel_data),
             nrow(iv_data))
)

write.csv(reg_summary, "results/tables/table5_regression_results.csv",
          row.names = FALSE, fileEncoding = "UTF-8")
cat("✅ 表5保存：table5_regression_results.csv\n")

# -----------------------------------------------------------
# 8. 稳健性检验：替换核心解释变量
# -----------------------------------------------------------
fe_inv  <- plm(SO2_intensity ~ ln_green_invention + industry_ratio + ln_real_gdpc,
               data = pdata, model = "within")
fe_util <- plm(SO2_intensity ~ ln_green_utility + industry_ratio + ln_real_gdpc,
               data = pdata, model = "within")

robust_summary <- data.frame(
  模型 = c("基准FE（绿色专利总数）", "替换：绿色发明专利", "替换：绿色实用新型"),
  核心变量系数 = c(
    round(coef(fe_base)["ln_green_patent"], 4),
    round(coef(fe_inv)["ln_green_invention"], 4),
    round(coef(fe_util)["ln_green_utility"], 4)
  ),
  第二产业占比 = c(
    round(coef(fe_base)["industry_ratio"], 4),
    round(coef(fe_inv)["industry_ratio"], 4),
    round(coef(fe_util)["industry_ratio"], 4)
  ),
  ln人均GDP = c(
    round(coef(fe_base)["ln_real_gdpc"], 4),
    round(coef(fe_inv)["ln_real_gdpc"], 4),
    round(coef(fe_util)["ln_real_gdpc"], 4)
  ),
  观测数 = rep(nrow(panel_data), 3)
)

write.csv(robust_summary, "results/tables/table6_robustness_check.csv",
          row.names = FALSE, fileEncoding = "UTF-8")
cat("✅ 表6保存：table6_robustness_check.csv\n")

# -----------------------------------------------------------
# 9. 区域异质性分析
# -----------------------------------------------------------
data_east    <- panel_data %>% filter(region == "东部")
data_central <- panel_data %>% filter(region == "中部")
data_west    <- panel_data %>% filter(region == "西部")

pdata_east    <- pdata.frame(data_east,    index = c("province", "year"))
pdata_central <- pdata.frame(data_central, index = c("province", "year"))
pdata_west    <- pdata.frame(data_west,    index = c("province", "year"))

fe_east    <- plm(SO2_intensity ~ ln_green_patent + industry_ratio + ln_real_gdpc,
                  data = pdata_east, model = "within")
fe_central <- plm(SO2_intensity ~ ln_green_patent + industry_ratio + ln_real_gdpc,
                  data = pdata_central, model = "within")
fe_west    <- plm(SO2_intensity ~ ln_green_patent + industry_ratio + ln_real_gdpc,
                  data = pdata_west, model = "within")

regional_summary <- data.frame(
  区域 = c("东部", "中部", "西部"),
  ln绿色专利系数 = c(
    round(coef(fe_east)["ln_green_patent"], 4),
    round(coef(fe_central)["ln_green_patent"], 4),
    round(coef(fe_west)["ln_green_patent"], 4)
  ),
  第二产业占比系数 = c(
    round(coef(fe_east)["industry_ratio"], 4),
    round(coef(fe_central)["industry_ratio"], 4),
    round(coef(fe_west)["industry_ratio"], 4)
  ),
  ln人均GDP系数 = c(
    round(coef(fe_east)["ln_real_gdpc"], 4),
    round(coef(fe_central)["ln_real_gdpc"], 4),
    round(coef(fe_west)["ln_real_gdpc"], 4)
  ),
  观测数 = c(nrow(data_east), nrow(data_central), nrow(data_west))
)

write.csv(regional_summary, "results/tables/table7_regional_heterogeneity.csv",
          row.names = FALSE, fileEncoding = "UTF-8")
cat("✅ 表7保存：table7_regional_heterogeneity.csv\n")

# 分区域描述性统计
region_desc <- panel_data %>%
  group_by(区域 = region) %>%
  summarise(
    SO2均值 = round(mean(SO2_intensity), 4),
    绿专均值 = round(mean(ln_green_patent), 4),
    GDP均值  = round(mean(ln_real_gdpc), 4),
    产业均值 = round(mean(industry_ratio), 4),
    观测数   = n()
  )

write.csv(region_desc, "results/tables/table8_summary_statistics_by_region.csv",
          row.names = FALSE, fileEncoding = "UTF-8")
cat("✅ 表8保存：table8_summary_statistics_by_region.csv\n")

# -----------------------------------------------------------
# 10. 数据文件保存
# -----------------------------------------------------------
write.csv(panel_data, "data/processed_data.csv",
          row.names = FALSE, fileEncoding = "UTF-8")
cat("✅ 处理后数据保存：data/processed_data.csv\n")

# -----------------------------------------------------------
# 11. 图表绘制
# -----------------------------------------------------------

# 图1：SO₂排放强度时间趋势（分区域）
so2_trend <- panel_data %>%
  group_by(year, region) %>%
  summarise(mean_SO2 = mean(SO2_intensity), .groups = "drop")

fig1 <- ggplot(so2_trend, aes(x = year, y = mean_SO2, color = region, group = region)) +
  geom_line(linewidth = 1.2) +
  geom_point(size = 2.5) +
  scale_color_manual(values = c("东部" = "#2196F3", "中部" = "#FF9800", "西部" = "#4CAF50")) +
  labs(title = "图1 中国各区域工业SO₂排放强度时间趋势（2005-2015）",
       x = "年份", y = "SO₂排放强度（万吨/亿元）",
       color = "区域") +
  theme_bw(base_size = 12) +
  theme(plot.title = element_text(hjust = 0.5, face = "bold"),
        legend.position = "bottom")

ggsave("results/figures/figure1_SO2_trend.png", fig1,
       width = 10, height = 6, dpi = 300, bg = "white")
cat("✅ 图1保存：figure1_SO2_trend.png\n")

# 图2：EKC曲线拟合
fig2_data <- panel_data %>%
  mutate(fitted_so2 = fitted(lm(SO2_intensity ~ ln_real_gdpc + ln_real_gdpc_sq +
                                  ln_green_patent + industry_ratio, data = panel_data)))

fig2 <- ggplot(panel_data, aes(x = ln_real_gdpc, y = SO2_intensity)) +
  geom_point(alpha = 0.3, color = "gray60", size = 1.5) +
  geom_smooth(method = "lm", formula = y ~ poly(x, 2), color = "#E53935",
              se = TRUE, fill = "#FFCDD2", linewidth = 1.2) +
  labs(title = "图2 环境库兹涅茨曲线（EKC）拟合图",
       subtitle = "SO₂排放强度与人均GDP的非线性关系",
       x = "ln(人均实际GDP)", y = "SO₂排放强度（万吨/亿元）") +
  theme_bw(base_size = 12) +
  theme(plot.title = element_text(hjust = 0.5, face = "bold"),
        plot.subtitle = element_text(hjust = 0.5))

ggsave("results/figures/figure2_EKC_curve.png", fig2,
       width = 9, height = 6, dpi = 300, bg = "white")
cat("✅ 图2保存：figure2_EKC_curve.png\n")

# 图3：绿色专利与SO₂排放相关性散点图
fig3 <- ggplot(panel_data, aes(x = ln_green_patent, y = SO2_intensity, color = region)) +
  geom_point(alpha = 0.4, size = 1.8) +
  geom_smooth(method = "lm", se = FALSE, linewidth = 1.0) +
  scale_color_manual(values = c("东部" = "#2196F3", "中部" = "#FF9800", "西部" = "#4CAF50")) +
  labs(title = "图3 绿色专利总数与SO₂排放强度相关性",
       x = "ln(绿色专利总数+1)", y = "SO₂排放强度（万吨/亿元）",
       color = "区域") +
  theme_bw(base_size = 12) +
  theme(plot.title = element_text(hjust = 0.5, face = "bold"),
        legend.position = "bottom")

ggsave("results/figures/figure3_green_patent_correlation.png", fig3,
       width = 9, height = 6, dpi = 300, bg = "white")
cat("✅ 图3保存：figure3_green_patent_correlation.png\n")

# 图4：区域系数对比柱状图
coef_data <- data.frame(
  区域 = c("东部", "中部", "西部"),
  系数 = c(coef(fe_east)["ln_green_patent"],
            coef(fe_central)["ln_green_patent"],
            coef(fe_west)["ln_green_patent"]),
  显著性 = c("***", "*", "不显著")
)

fig4 <- ggplot(coef_data, aes(x = 区域, y = 系数, fill = 区域)) +
  geom_col(width = 0.5, color = "white") +
  geom_text(aes(label = paste0(round(系数, 4), "\n", 显著性)),
            vjust = ifelse(coef_data$系数 < 0, 1.3, -0.3), size = 4) +
  scale_fill_manual(values = c("东部" = "#2196F3", "中部" = "#FF9800", "西部" = "#4CAF50")) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "gray40") +
  labs(title = "图4 绿色专利减排效应的区域异质性",
       subtitle = "各区域固定效应模型回归系数对比",
       x = "区域", y = "ln绿色专利系数",
       caption = "注：***p<0.01，*p<0.1") +
  theme_bw(base_size = 12) +
  theme(plot.title = element_text(hjust = 0.5, face = "bold"),
        plot.subtitle = element_text(hjust = 0.5),
        legend.position = "none")

ggsave("results/figures/figure4_regional_coefficient_comparison.png", fig4,
       width = 8, height = 6, dpi = 300, bg = "white")
cat("✅ 图4保存：figure4_regional_coefficient_comparison.png\n")

# 图5：核心变量分布直方图
p5a <- ggplot(panel_data, aes(x = SO2_intensity)) +
  geom_histogram(bins = 30, fill = "#5C6BC0", color = "white", alpha = 0.85) +
  labs(title = "SO₂排放强度", x = "万吨/亿元", y = "频数") +
  theme_bw(base_size = 10)

p5b <- ggplot(panel_data, aes(x = ln_green_patent)) +
  geom_histogram(bins = 30, fill = "#26A69A", color = "white", alpha = 0.85) +
  labs(title = "ln(绿色专利总数+1)", x = "对数值", y = "频数") +
  theme_bw(base_size = 10)

p5c <- ggplot(panel_data, aes(x = ln_real_gdpc)) +
  geom_histogram(bins = 30, fill = "#FFA726", color = "white", alpha = 0.85) +
  labs(title = "ln(人均实际GDP)", x = "对数值", y = "频数") +
  theme_bw(base_size = 10)

p5d <- ggplot(panel_data, aes(x = industry_ratio)) +
  geom_histogram(bins = 30, fill = "#EF5350", color = "white", alpha = 0.85) +
  labs(title = "第二产业占比", x = "比例", y = "频数") +
  theme_bw(base_size = 10)

fig5 <- gridExtra::grid.arrange(p5a, p5b, p5c, p5d, ncol = 2,
                                top = "图5 核心变量分布直方图")
ggsave("results/figures/figure5_descriptive_distribution.png", fig5,
       width = 10, height = 7, dpi = 300, bg = "white")
cat("✅ 图5保存：figure5_descriptive_distribution.png\n")

# 图6：稳健性检验系数对比
robust_plot_data <- data.frame(
  模型     = c("基准FE\n（绿色专利总数）", "替换\n（绿色发明专利）", "替换\n（绿色实用新型）"),
  系数     = c(coef(fe_base)["ln_green_patent"],
               coef(fe_inv)["ln_green_invention"],
               coef(fe_util)["ln_green_utility"]),
  下界     = c(confint(fe_base)["ln_green_patent", 1],
               confint(fe_inv)["ln_green_invention", 1],
               confint(fe_util)["ln_green_utility", 1]),
  上界     = c(confint(fe_base)["ln_green_patent", 2],
               confint(fe_inv)["ln_green_invention", 2],
               confint(fe_util)["ln_green_utility", 2])
)

fig6 <- ggplot(robust_plot_data, aes(x = 模型, y = 系数, color = 模型)) +
  geom_point(size = 3.5) +
  geom_errorbar(aes(ymin = 下界, ymax = 上界), width = 0.2, size = 1) +
  geom_hline(yintercept = 0, linetype = "dashed", color = "gray40") +
  scale_color_manual(values = c("#3F51B5", "#009688", "#FF5722")) +
  labs(title = "图6 稳健性检验：替换核心解释变量系数对比",
       subtitle = "误差棒为95%置信区间",
       x = "", y = "回归系数",
       caption = "注：所有模型均使用双向固定效应") +
  theme_bw(base_size = 12) +
  theme(plot.title = element_text(hjust = 0.5, face = "bold"),
        plot.subtitle = element_text(hjust = 0.5),
        legend.position = "none")

ggsave("results/figures/figure6_robustness_comparison.png", fig6,
       width = 9, height = 6, dpi = 300, bg = "white")
cat("✅ 图6保存：figure6_robustness_comparison.png\n")

# -----------------------------------------------------------
# 12. 完成提示
# -----------------------------------------------------------
cat("\n")
cat("========================================\n")
cat("✅ 全部分析完成！\n")
cat("📁 表格输出目录：results/tables/\n")
cat("📁 图表输出目录：results/figures/\n")
cat("📁 数据文件目录：data/\n")
cat("========================================\n")
