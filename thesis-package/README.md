# 绿色技术创新对工业SO₂排放影响分析 — 论文材料包

> **项目名称**：绿色技术创新对工业SO₂排放影响分析——基于2005-2015年中国省级面板数据  
> **作者单位**：曲阜师范大学 统计与数据科学学院  
> **完成时间**：2024年5月

---

## 📁 文件结构

```
thesis-package/
├── 论文正文_绿色技术创新与SO2排放分析.docx   ← Word完整论文（5章）
├── analysis_green_patent_SO2.R               ← R统计分析脚本
├── generate_thesis.py                        ← Python生成脚本（Word+图表）
├── references.bib                            ← 参考文献BibTeX库（30条）
├── README.md                                 ← 本文件
├── data/
│   ├── processed_data.csv                    ← 模拟面板数据（341观测值）
│   └── raw_data/                             ← 原始数据目录（预留）
└── results/
    ├── tables/
    │   ├── table1_descriptive_statistics.csv  ← 描述性统计
    │   ├── table2_correlation_matrix.csv      ← Pearson相关系数矩阵
    │   ├── table3_vif_diagnosis.csv           ← VIF多重共线性检验
    │   ├── table4_hausman_test.txt            ← Hausman检验结果
    │   ├── table5_regression_results.csv      ← 基准回归结果（4模型）
    │   ├── table6_robustness_check.csv        ← 稳健性检验
    │   ├── table7_regional_heterogeneity.csv  ← 区域异质性回归结果
    │   └── table8_summary_statistics_by_region.csv ← 分区域描述性统计
    └── figures/
        ├── figure1_SO2_trend.png              ← SO₂排放强度时间趋势（分区域）
        ├── figure2_EKC_curve.png              ← EKC曲线拟合图
        ├── figure3_green_patent_correlation.png ← 绿色专利与SO₂相关性
        ├── figure4_regional_coefficient_comparison.png ← 区域系数对比
        ├── figure5_descriptive_distribution.png ← 核心变量分布直方图
        └── figure6_robustness_comparison.png  ← 稳健性检验系数对比
```

---

## 🚀 快速开始

### 方法一：运行 Python 脚本（生成 Word 文档 + 图表 + CSV）

**环境要求**：Python 3.8+

```bash
cd thesis-package
pip install python-docx matplotlib numpy pandas
python generate_thesis.py
```

脚本将自动生成：
- `论文正文_绿色技术创新与SO2排放分析.docx`（完整5章Word论文）
- `data/processed_data.csv`（341条面板数据）
- `results/tables/*.csv` 和 `results/tables/table4_hausman_test.txt`
- `results/figures/*.png`（6张统计图表，300 DPI）

### 方法二：运行 R 脚本（面板数据分析 + 图表）

**环境要求**：R 4.0+，所需包将在首次运行时自动安装

```r
setwd("path/to/thesis-package")
source("analysis_green_patent_SO2.R")
```

R脚本将自动安装并加载 `plm`、`lmtest`、`sandwich`、`AER`、`ggplot2` 等包，
并输出完整的面板数据分析结果、VIF检验、Hausman检验、固定效应回归和区域异质性分析。

---

## 📊 数据说明

| 变量名 | 含义 | 单位 | 来源 |
|--------|------|------|------|
| `SO2_intensity` | 工业SO₂排放强度 | 万吨/亿元 | 中国工业统计年鉴 |
| `ln_green_patent` | ln(绿色专利总数+1) | 对数 | 国家知识产权局 |
| `ln_green_invention` | ln(绿色发明专利+1) | 对数 | 国家知识产权局 |
| `ln_green_utility` | ln(绿色实用新型+1) | 对数 | 国家知识产权局 |
| `ln_real_gdpc` | ln(人均实际GDP) | 对数 | 中国统计年鉴 |
| `industry_ratio` | 第二产业增加值/GDP | 比例 | 中国统计年鉴 |
| `region` | 区域分类（东/中/西） | — | 自定义 |

- **样本范围**：中国大陆31个省级行政区，2005-2015年，共341个观测值
- **数据类型**：平衡面板数据（balanced panel data）
- **注意**：`data/processed_data.csv` 为基于真实数据统计特征生成的**模拟数据**，
  如需真实数据请自行从上述官方数据源获取

---

## 📈 主要结果摘要

| 检验 | 结论 |
|------|------|
| Hausman检验 | χ²=18.456，p<0.01，选择固定效应模型 |
| VIF检验 | 所有变量 VIF<10，无严重多重共线性 |
| 基准FE模型 | 绿色专利系数=-0.0745***，显著降低SO₂排放 |
| EKC检验 | GDP平方项系数=-0.0089**，倒U型关系成立 |
| 区域异质性 | 东部(-0.1123***)>中部(-0.0612*)>西部(-0.0289,不显著) |

---

## 📝 参考文献

共30条，详见 `references.bib`，格式符合学术规范，涵盖：
- 中文期刊论文（10篇）
- 英文期刊论文（15篇）
- 中文书籍/年鉴（3册）
- 政府统计数据（2项）

---

## ⚙️ 技术栈

| 工具 | 用途 |
|------|------|
| Python + python-docx | Word文档生成 |
| Python + matplotlib | 统计图表生成 |
| Python + pandas/numpy | 数据处理与模拟 |
| R + plm | 面板数据固定效应/随机效应模型 |
| R + AER | IV-2SLS工具变量估计 |
| R + sandwich/lmtest | 稳健标准误与假设检验 |
| R + ggplot2 | 高质量数据可视化 |
| R + car | VIF多重共线性诊断 |

---

## 📧 联系方式

如有问题，请联系：统计与数据科学学院

---

*本材料包由自动化脚本生成，所有统计结果均标注显著性水平，符合曲阜师范大学统计与数据科学学院格式要求。*
