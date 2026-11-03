# 扩大数值范围与矩阵维度

## 已实现：更大数值的 2×2

两个版本均支持各维度 1–2、元素为 0–100 的非负整数。当前 `uniform-large-v1` 对所有输入统一使用 800 张普通杀、800 张红色救援牌、131,072 张可摸牌及一张麒麟弓；零矩阵与小数值也使用完全相同的牌堆。详见 [统一大牌堆](UNIFORM_DECK.md)。

资源是固定储备，不预先计算 AB 后配牌。杀的初始手牌按实际任务数发放，华佗获得整个救援储备；所有结果仍来自原版放逐技能产生的实际摸牌。原始版保持 i、j、k 串行、不跳过 B=0 的任务；优化版仍跳过零项并按较少出杀次数选择直接或转置方向。

扩容使全 100 的 2×2 运算需要 800 次出杀、800 次救援、800 次放逐，合计摸 80,000 张牌，每个结果位 20,000 张。没有实现无限牌堆；当前的输入上限使资源有可验证的充足余量，也避免整数溢出及无界内存分配。

为避免大手牌下日志审计反复线性搜索旧手牌，两个版本共同将“原手牌 ID 是否存在”的查找改为集合。此改动仅服务记录生成，不改变任务、游戏规则、实际抽牌或最终结果。因此新旧程序的时间不能混作同一版本；上一轮两个程序、源码包及哈希保存在 `dist/legacy-small-v1/`，旧 96 例报告仍对应旧二进制。

输入示例位于 `examples/expanded/`；预先固定的 12 组测试位于 `examples/suites/expanded-v1/`，包括数值阶梯、随机稠密、左右不对称、稀疏、左零与右零。历史 `expanded-v1` 的 12 组两版各 1 次预热＋3 次实测、共 96 次调用全部正确；完整分析见 [实测结果](EXPANDED_RESULTS.md)。结果报告在 `evidence/expanded/suite-v1/report.html`，便携包内为 `expanded-report/report.html`。

```powershell
python scripts/run_case.py examples/expanded/all-100.json --edition baseline
python scripts/run_case.py examples/expanded/all-100.json --edition optimized
python scripts/benchmark_suite.py --catalog examples/suites/expanded-v1/catalog.json --runs 3
python scripts/verify_expanded.py
```

GUI 中直接填写 0–100 的矩阵即可自动选择资源配置；大数值的正常动画可能持续十几分钟。选择极速可跳过演示等待。后台测试不替代大手牌界面的人工验收，最终 GUI 布局和动画仍未复验。

## 本轮范围

用户已取消 3×3 / 4×4 方向，本轮只完善大数值的 2×2 运算。维度超过 2 仍会明确拒绝；不会为追求维度而改造原版座位布局。后续关注现有 2×2 中的真实出牌成本、牌堆加载成本、手牌规模和两版性能差异。
