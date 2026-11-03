# 统一大牌堆

当前版本 `uniform-large-v1` 对所有合法输入采用同一配置，原始版和优化版完全一致：

| 资源 | 固定容量 |
| --- | ---: |
| 普通杀 | 800 |
| 华佗红色救援牌 | 800 |
| 可摸牌堆 | 131,072 |
| 麒麟弓 | 1 |

零矩阵、0–9 的小数值、10–100 的大数值均使用大牌堆，不再按输入数值切换。大牌堆在进入计算模式时加载；仅打开启动页或矩阵输入框不提前建立牌桌。普通对局仍排除所有计算用扩展牌。

张飞实际获得的杀按任务数分配，华佗固定获得 800 张救援牌，所有结果武将从零手牌开始。这是共同资源容量，任务数仍由各自算法决定。原始版不跳过 B=0，优化版继续跳过零项并选择较少出杀的方向。没有按结果计算牌堆大小。

两版输入范围仍为行列 1–2、整数 0–100。小数值现在也承担同样的大牌堆初始化工作；此前小牌堆、按数值切换牌堆版本的计时只作历史记录，不能直接用于描述当前程序性能。新计时请使用 `scripts/compare.py` 或 `scripts/benchmark_suite.py`；它们会记录新程序哈希。

本次定向验收覆盖两版各 13 个真实引擎场景：零矩阵、1、9、10、小数值完整矩阵、全 100、非方阵、右零矩阵、暂停单步及三种资源/动作故障。检查实际手牌、每步摸牌与救援、两种算法任务数，并要求所有非故障输入的初始牌堆 ID 列表哈希完全一致。另运行两版各 21 个输入/精确重播检查，以及双版本配置、端口和输出隔离测试。故障注入刻意移除救援牌或清空牌堆，属于负向测试，不是用户可选择的资源档位。

两版合计 68 项定向场景及输入/重播检查已通过。完整性能套件仍会逐次启动程序，大牌堆统一后耗时高于历史小牌堆版本；单次体验可先使用 `scripts/run_case.py`。

证据：`evidence/uniform-deck/`；当前冻结清单：`evidence/frozen/current-manifest.json`。旧版本完整便携包与源码在 `dist/legacy-adaptive-v1/`，历史冻结和实测数据保持原样。

```powershell
python scripts/test_uniform_deck.py --edition baseline
python scripts/test_uniform_deck.py --edition optimized
python scripts/test_records.py --edition baseline --output-dir evidence/uniform-deck/baseline/records
python scripts/test_records.py --edition optimized --output-dir evidence/uniform-deck/optimized/records
python scripts/test_isolation.py --output-dir evidence/uniform-deck/isolation
python scripts/freeze_uniform.py
python scripts/test_launcher.py
```
