# 最新状态：统一大牌堆

用户要求两个版本所有输入统一使用大牌堆。当前代码 uniform-large-v1 已移除按数值切换及小牌堆注册，合法输入无论大小/全零都是800杀、800救援、131072可摸牌。算法不变；普通牌堆仍隔离。当前验收 scripts/test_uniform_deck.py + test_records.py + test_isolation.py，数据 evidence/uniform-deck/；冻结 scripts/freeze_uniform.py，生成 current-manifest.json 供启动器打包校验。旧按阈值切换版本包在 dist/legacy-adaptive-v1，旧耗时不得冒充新版本。统一启动页仍保留，禁止 Computer Use。以下为历史接续记录。

# 三国杀 GEMM 接续

用户已批准原生 Windows QSanguosha 客户端方案。固定上游 e8768851bd8054db9fd1b63cd6f1feca813590d7。

当前交付为两个独立版本：Baseline（固定 baseline-v1）与 Optimized（固定 transpose-v1.2）。每版通过 127 个引擎用例和 21 个记录用例，另通过同时运行、配置/端口/输出隔离和拒绝跨版算法检查。历史组合版的 190 项结果保留，不混入新版本数据。

硬约束：技能代码保持原样；结果来自游戏手牌；最多 2×2，整数 0–100；保留 baseline-v1；正常/加速/无动画极速三档。禁止拿外部矩阵乘法结果填游戏状态。

验收：100 个标量组合、矩阵样例/边界/随机、故障停机、真实 Windows 牌桌。未获得证据的阶段不得宣称通过。

程序：dist/SanguoshaGEMM-Baseline/SanguoshaGEMM-Baseline.exe 与 dist/SanguoshaGEMM-Optimized/SanguoshaGEMM-Optimized.exe。用法见 README.md；验证边界见 docs/VALIDATION.md；数据见 evidence/。工具链仅放任务专用目录，不改变系统 PATH。

最新用户偏好：禁止继续 Computer Use；验证在后台进行，输出 JSON/日志。此前看过原生牌桌示例，但最终工具条布局、GUI 重播与大手牌视觉计数未人工复验，不得宣称这些项目已通过。V2 批量实验尚未实现。

同矩阵极速对比：scripts/compare.py，强制 speed=2，1 次预热＋默认 10 次实测，交替顺序串行运行。输出 HTML/JSON；固定样例报告 evidence/versions/benchmark/report.html。

性能评估扩展为预先固定的 96 组唯一输入（40 组 2×2，覆盖全部 8 种尺寸），每例每版 1 次预热＋10 次实测；输入 examples/suites/sgemm-v1，报告 evidence/versions/suite-v1/report.html。当前以该完整套件为主，旧单位矩阵演示不能代表整体性能。

完整套件已通过：2,112 次真实程序调用全部正确；准备＋结算以 ±5% 分档，48 快 / 46 接近 / 2 慢。case-035 转置使出杀 33→30、人数 6→8，耗时 205.97→297.09 ms，约慢 44%；不得隐去该退化，也不得在本次测量后悄悄替换优化算法。未来成本模型改进另立版本并全套比较。另一慢例 case-092 为零出牌，准备差约 0.17 ms，不作强因果推断。详情 docs/TEST_SUITE_RESULTS.md。

当前工作改为扩容：两版均已支持 0–100，元素超过 9 时懒加载固定 800 杀 / 800 救援 / 131072 可摸牌。算法不变，共同将日志的旧手牌查找改为 QSet；原始旧包在 dist/legacy-small-v1，旧 96 例耗时不能当新版数据。12 例扩容测试 evidence/expanded/suite-v1，1 次预热＋3 次实测，两版共 96 次调用。当前用户已取消 3×3/4×4，不要继续推进该方向。只完成更大数值 2×2 的实测、回归和交付。

扩容性能已完成：12/12，96 次调用全部正确，逐牌审计通过。全 100 的 C 四项均 20000、实际摸牌80000；原始/优化纯引擎 12.939/13.051 秒，准备＋结算15.345/15.499秒，含启动21.879/22.059秒，峰值约169MiB。扩容后原有296项回归与版本隔离检查通过，额外边界结果看 evidence/expanded/edges/summary.json。完整结果 docs/EXPANDED_RESULTS.md，当前冻结入口 scripts/freeze_expanded.py。

新增统一 GUI 启动页：launcher/ 独立 Qt Widgets 工程，两个按钮通过 --gemm 启动现有 Baseline/Optimized，游戏二进制未改动。启动器 dist/SanguoshaGEMM-Launcher/SanguoshaGEMM-Launcher.exe；统一包 dist/SanguoshaGEMM-unified-windows.zip（launcher在根，两个版本子目录）。构建 scripts/build_launcher.ps1；部署/统一打包 scripts/package_launcher.py --archive；后台真实按钮、进程、路径、缺失文件及渲染测试 scripts/test_launcher.py，证据 evidence/launcher。保持禁止 Computer Use。
