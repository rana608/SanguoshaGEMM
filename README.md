# 三国杀 GEMM · 矩阵演武

原生 Windows QSanguosha 客户端改造。输入小矩阵后，张飞出杀、华佗急救、曹丕放逐，结果直接读取结果武将的实际手牌数。支持 **C=AB，各维度 1–2、元素为 0–100 整数**；不是双精度 BLAS dGEMM。

固定上游：Mogara/QSanguosha-v2，提交 `e8768851bd8054db9fd1b63cd6f1feca813590d7`。武将技能与伤害/濒死规则沿用该版本，未修改原实现。

## 下载与源码

Windows 用户请从 [Releases](https://github.com/rana608/SanguoshaGEMM/releases) 下载 `SanguoshaGEMM-unified-windows.zip`，完整解压后启动最外层的 `SanguoshaGEMM-Launcher.exe`。同一下载区提供对应源码包、完整测试记录和 SHA256 校验文件。

```powershell
git clone https://github.com/rana608/SanguoshaGEMM.git
cd SanguoshaGEMM
```

仓库直接包含改造后的 `upstream/` 源码和资源，无需初始化子模块。工具链、编译目录、个人设置和大型交付 ZIP 不进入 Git；构建方式见 [Windows 构建说明](docs/BUILD.md)。根目录和 `upstream/` 均保留上游许可，第三方说明见 [THIRD_PARTY.md](docs/THIRD_PARTY.md)。

## 统一 GUI 入口

推荐下载并完整解压 `dist/SanguoshaGEMM-unified-windows.zip`，双击最外层 **SanguoshaGEMM-Launcher.exe**。页面只有两个启动按钮：**启动原始版**、**启动优化版**，直接进入对应客户端的矩阵输入页。

两个版本可以同时打开，各自配置和记录仍然独立；关闭启动页不会关闭游戏。工作区直接启动 `dist/SanguoshaGEMM-Launcher/SanguoshaGEMM-Launcher.exe`。详细用法和构建见 `docs/LAUNCHER.md`。两个客户端现已统一大牌堆；当前资源规则与验收见 `docs/UNIFORM_DECK.md`。

## 当前版本：统一大牌堆

两版的所有合法输入统一使用 800 张杀、800 张救援牌及 131,072 张可摸牌，包括零矩阵与 0–9 的小数值。不再根据输入数值切换牌堆，结果仍通过真实游戏结算产生。当前资源版本为 `uniform-large-v1`，验收记录在 `evidence/uniform-deck/`。全 100 的 2×2 结果为每个位置 20,000 张，共 80,000 张实际手牌。

大数值输入见 `examples/expanded/`，运行方式与资源说明见 `docs/SCALING.md`。上一轮按数值切换资源的历史扩容报告为 `evidence/expanded/suite-v1/report.html`，便携包内为 `expanded-report/report.html`。历史时间表与解读见 `docs/EXPANDED_RESULTS.md`。原始版与优化版的算法分别保持不变；大牌堆与日志查找均为共同基础设施，旧性能数据不应当作新版实测。

旧两个程序、源码和便携包保留在 `dist/legacy-small-v1/`；旧 96 例报告对应这些旧程序。3×3 / 4×4 方向已取消，本轮只做 2×2 数值与资源扩容。

## 两个独立版本

| 交付包 | 可执行文件 | 固定算法 |
| --- | --- | --- |
| `SanguoshaGEMM-Baseline-windows.zip` | `SanguoshaGEMM-Baseline.exe` | 原始无优化 `baseline-v1` |
| `SanguoshaGEMM-Optimized-windows.zip` | `SanguoshaGEMM-Optimized.exe` | 跳过零项 + 自动选择计算方向 `transpose-v1.2` |

分别完整解压，启动对应程序并点击 **矩阵演武**。无需安装 Qt。工作区对应目录为 `dist/SanguoshaGEMM-Baseline/` 和 `dist/SanguoshaGEMM-Optimized/`。

两版分别链接，算法在构建时固定，无法通过设置或 JSON 切换为另一版。可以同时运行：资源各自随包携带，配置固定存放于各自程序目录的 `config-baseline.ini` / `config-optimized.ini`，本地牌桌自动申请空闲端口。GUI 默认记录分别保存在各自 `records/baseline/` / `records/optimized/` 下，文件名带时间戳。

输入框每行填写一行数字，用空格分隔。支持普通演示、加速、极速；可以暂停、单步、停止、重新计算、保存和载入 JSON 记录。单步边界是一次完整的“杀—急救—放逐”。结果按钮可指向对应武将。

| 速度 | 行为 |
| --- | --- |
| 正常（0） | 保留主要牌桌动画，每次完整结算后等待约 900 ms |
| 加速（1） | 卡牌移动时长缩短，每次结算后等待约 90 ms |
| 极速（2） | 不主动等待，跳过装饰动画与卡牌移动过程，运行中减少牌桌重绘 |

极速仍执行完整规则，不会把外部计算的答案填入手牌。此处计算由 CPU 驱动；跳过动画减少显示开销，不代表使用 GPU 做矩阵乘法。

## 后台运行，无需操作桌面

以下命令在源码工作区执行，结果与错误均写入 JSON：

```powershell
python scripts/run_case.py examples/demo.json --edition baseline
python scripts/run_case.py examples/demo.json --edition optimized
```

默认输出到 `evidence/baseline/` / `evidence/optimized/`，文件名带时间戳。也可用 `--output` 显式指定不同结果文件。

便携包也可独立后台运行。例如在原始版解压目录打开 PowerShell（优化版替换对应文件名）：

```powershell
$inputFile = (Resolve-Path examples/demo.json).Path
$outputFile = Join-Path $PWD 'result-baseline.json'
$process = Start-Process -FilePath .\SanguoshaGEMM-Baseline.exe -ArgumentList @('--gemm-case', ('"' + $inputFile + '"'), ('"' + $outputFile + '"')) -WindowStyle Hidden -Wait -PassThru
Get-Content -LiteralPath $outputFile -Raw -Encoding UTF8
```

程序检测 `--gemm-case` 后自动使用 Qt offscreen，无牌桌窗口。直接调用支持相对路径，路径相对于启动目录。退出码：0 完成，1 计算途中停止，2 输入无效，3 输出无法写入，4 普通牌堆隔离检查失败。

输入示例：

```json
{"A":[[1,2],[3,0]],"B":[[2,1],[1,2]],"speed":2}
```

两版结果均为 `[[4,5],[6,3]]`。原始版执行 12 次出杀、12 次急救、12 次放逐，共摸 18 张牌。

记录包含版本标识 `edition`、输入、算法、初始武将与手牌、固定牌堆、每步消耗的牌、结果武将实际手牌数、错误、时间及资源统计。同版记录可直接作为输入重新结算；不会直接恢复文件里的结果值。跨版比较使用不含 `algorithm` 的同一输入，如附带 examples；显式要求另一版算法会报错，避免混淆实验数据。

## 冻结 baseline 与优化

| 版本 | 任务安排 |
| --- | --- |
| `baseline-v1` | 固定 i、j、k 顺序；B=0 仍完整出杀、救援、放逐 |
| `transpose-v1.2` | 跳过零项，并比较直接/转置方向任务数，选择较少者 |

两版保留相同播放选项。性能判断使用下述多测试集报告；原先的单位矩阵案例仅作为功能演示保留，不代表一般矩阵收益。

初期组合程序的中间优化 `sparse-v1.1` 数据保留于历史 `evidence/benchmark/`，本次只交付上述两个版本。万箭齐发批量方案未实现。

运行 `python scripts/benchmark.py` 测量完整的 96 组测试集，每组每版一次预热、十次实测，并保留全部结果。准备时间、无主动等待的引擎结算时间、包含播放节奏的运行时间分别统计。CPU 时间和内存峰值覆盖整个进程，包含启动；没有 GPU 利用率数据。后台运行不测量画面播放完成时间。

## 历史小数值测试集：96 组输入

测试集覆盖全部 8 种合法尺寸，其中 40 组为完整 2×2 乘法；包含稠密低值、均匀值和高值、左右数值不对称、含零、不同稀疏度、全零、全 9、整行/列零等。输入种子和测量顺序预先固定，结果逐例公开，不按加速效果筛选。

```powershell
python scripts/benchmark.py --runs 10
```

查看 `evidence/versions/suite-v1/report.html`，或便携包中的 `test-suite-report/report.html`。报告可筛选类别与快慢，列出实际矩阵、结果、两版耗时、出杀数和优化方向。完整数据可下载为 CSV / JSON。测试集说明与独立运行方法见 `docs/TEST_SUITE.md`。

已完成 2,112 次调用，96 组结果全部正确。按准备＋结算耗时、以 ±5% 为接近区间：48 组更快、46 组接近、2 组更慢。全 9 几乎无收益，一组稠密非方阵反而约慢 44%；完整分析见 `docs/TEST_SUITE_RESULTS.md`。独立测试包 `dist/SanguoshaGEMM-test-suite.zip` 包含全部输入、报告和原始记录。

## 同一矩阵的极速用时对比

在源码工作区运行：

```powershell
python scripts/compare.py examples/demo.json --runs 10
```

统一入口只提取输入中的 A、B，强制两版 `speed=2`。每版预热一次，然后交替先后顺序、串行实测，避免互相争抢 CPU。对比结束生成独立目录下的 `report.html` 和 `summary.json`，并打印路径。报告显示输入/结果矩阵、两版引擎用时、中位数/p95、加速比、出杀次数、准备加完整结算用时、含启动总用时及内存峰值。实际结果需两版一致并通过独立整数核验才展示成功。

便携包自带 `compare.py`（需 Python 3.11+）。将两个包解压到同一父目录后，在任意一版目录内运行 `python compare.py examples/demo.json --runs 10`，会自动找到并调用两版程序。也可用 `--baseline`、`--optimized` 指定两个 exe 的绝对路径，用 `--output-dir` 指定独立报告目录。

随包的 `comparison-example/report.html` 为旧单位矩阵演示快照。历史小数值比较入口是 `test-suite-report/report.html`，当前扩容入口是 `expanded-report/report.html`；单例对比仍可用于自选矩阵。

## 测试和构建

详见 `docs/VALIDATION.md`、`docs/BUILD.md`、`docs/THIRD_PARTY.md`。

```powershell
python scripts/test_engine.py --edition baseline
python scripts/test_records.py --edition baseline
python scripts/test_engine.py --edition optimized
python scripts/test_records.py --edition optimized
python scripts/test_isolation.py
python scripts/benchmark.py
```

最新数据位于 `evidence/versions/`。旧组合包及历史记录保留作参考，不作为当前交付入口。当前两个独立版本均为 Windows 32 位 Release 程序，在本机 64 位 Windows 后台运行。牌桌沿用原版资源及布局；最终界面改动尚未完整人工验收，已按用户要求停止桌面自动化。后台控制和记录验证与界面验收分别记录，不以后台测试代替视觉检查。

本改造用于非商业演示；保留上游署名、GPLv3、MCFR 以及 Qt 等第三方许可。分发时请同时保留许可证和对应源码。
