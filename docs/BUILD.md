# Windows 构建与打包

已使用官方 Qt 5.5.1 / MinGW 4.9.2 32 位工具链构建成功。旧工具链无法可靠处理中文目录，构建脚本使用 `%USERPROFILE%/sgemm-work` 目录联接指向工作区；若该路径已指向别处会停止，不覆盖其他项目。

## 依赖

- Windows、Python 3.11+、7-Zip（`7z` 在 PATH 中）。从仓库取源码时另需 Git。
- 对应上游源码及完整资源放在 `upstream/`。源码交付包已经包含，无需再次克隆。
- GitHub 仓库同样直接包含 `upstream/` 的修改后快照，无需子模块。该目录的原始 Git 历史不随仓库分发；`freeze*.py` 用于维护者保留的固定上游检出，不是用户构建的必需步骤。已发布版本的冻结记录保留在 `evidence/frozen/`。
- `upstream/` 保留原有 Git 文本行尾规则，Git 检出时可能转换行尾。需要核对冻结清单中的原始文件字节哈希时，使用对应 Release 的 `SanguoshaGEMM-source.zip`；仓库 README 等发布说明也可能晚于该冻结记录。
- 执行 `scripts/bootstrap.ps1`，在 `.tools/` 中下载并验证 Qt 安装包及 SWIG 3.0.12。Qt 下载约 1 GB，解压与构建需数 GB 空间。

bootstrap 从安装包提取工具，不运行安装程序，不修改系统 PATH。下载地址与 SHA256 固定在 `scripts/download_tools.py`。现有环境已验证下载哈希及提取后的工具链；组合 bootstrap 脚本尚未在另一台干净机器上端到端验证。

## 命令

在源码工作区依次运行：

```powershell
./scripts/bootstrap.ps1
./scripts/build.ps1
./scripts/package.ps1
python scripts/test_engine.py --edition baseline
python scripts/test_records.py --edition baseline
python scripts/test_engine.py --edition optimized
python scripts/test_records.py --edition optimized
python scripts/test_isolation.py
python scripts/benchmark.py
```

`build.ps1` 设置当前进程 PATH，生成本地 qt.conf，选择官方开源版本配置，执行 qmake、SWIG、翻译生成和 Release 编译。默认按顺序生成 `build/SanguoshaGEMM-Baseline.exe` 和 `build/SanguoshaGEMM-Optimized.exe`。可以用 `-Edition baseline` 或 `-Edition optimized` 单独构建。两版共享编译缓存，每版独立链接；不要同时启动两个构建脚本。每轮强制重新链接，避免缓存导致版本混淆。

qmake 的 `GEMM_EDITION=baseline` / `optimized` 分别选择 `gemm-edition-baseline.cpp` / `gemm-edition-optimized.cpp`。版本、默认算法、配置文件名与记录标识固定在相应程序内。

`package.ps1` 复制资源和许可，生成 `dist/SanguoshaGEMM-Baseline/` 和 `dist/SanguoshaGEMM-Optimized/`，也支持 `-Edition` 单独打包。Qt 官方包中的 windeployqt 含安装器前缀，采用 `deploy_qt.py` 扫描 PE 导入并复制实际依赖。QtQuick 1.0 由 Qt5Declarative 提供，无需部署无关 QtWebKit 和调试版模块。程序动态链接 Qt DLL，保留替换动态库的能力。

维护者可在原始 Git 工作区运行 `python scripts/freeze.py`，记录上游提交、核心规则未修改的证据、改造源码和程序哈希、测量环境与固定样例。导出的源码包不含 Git 历史，直接保留随包提供的冻结证据，不需重新执行 freeze。`python scripts/archive.py` 创建两个独立便携包及包含两个构建目标的源码包，不包含本机工具链、构建缓存、Git 历史或运行偏好文件。

普通游戏的规则源文件保持原样，GEMM AI、牌堆与节奏分支仅作用于计算模式。没有把 GEMM 模式加入通用开服选择列表，避免未经矩阵初始化启动。音频使用上游可选构建开关，本交付未启用 FMOD 音频支持。

## 扩容版本验收

当前代码支持 0–100，构建和打包仍使用上面的两个独立目标。旧冻结脚本 `freeze.py` 面向原 96 例小数值版本；当前扩容交付使用 `freeze_expanded.py`，避免把旧测量绑定到新程序。

```powershell
python scripts/build_expanded_suite.py
python scripts/benchmark_suite.py --catalog examples/suites/expanded-v1/catalog.json --output-dir evidence/expanded/suite-v1 --runs 3
python scripts/verify_expanded.py
python scripts/test_engine.py --edition baseline --output-dir evidence/expanded/regression/baseline/engine
python scripts/test_records.py --edition baseline --output-dir evidence/expanded/regression/baseline/records
python scripts/test_engine.py --edition optimized --output-dir evidence/expanded/regression/optimized/engine
python scripts/test_records.py --edition optimized --output-dir evidence/expanded/regression/optimized/records
python scripts/test_isolation.py --output-dir evidence/expanded/regression/isolation
python scripts/test_expanded_edges.py
python scripts/write_expanded_results.py
./scripts/package.ps1
python scripts/freeze_expanded.py
python scripts/archive.py
```

计时应在独占本任务测试进程时串行完成，不要同时构建或做回归。已有报告目录不会被基准测试静默覆盖；复测请换输出目录，只有相同输入、程序和测量脚本允许 `--resume`。默认验收路径用于本次冻结，复测其他路径时需相应调整验收脚本。

## 统一启动页

`launcher/launcher.pro` 是独立的 Qt Widgets 程序，不改动两个引擎目标。使用 `scripts/build_launcher.ps1` 编译，然后运行 `python scripts/package_launcher.py`、`python scripts/test_launcher.py` 和 `python scripts/package_launcher.py --archive`。统一包根目录为启动器，两个客户端保留独立文件夹；完整源码包包含 launcher/。用法见 [启动页说明](LAUNCHER.md)。

## 当前统一大牌堆版本

资源策略已统一，当前定向测试、冻结顺序见 [UNIFORM_DECK.md](UNIFORM_DECK.md)。使用 `freeze_uniform.py` 生成当前清单，然后运行 `package_launcher.py --archive` 和 `archive.py`。上面的 `freeze_expanded.py` 是历史版本入口，不应用于绑定本次二进制到旧计时。
