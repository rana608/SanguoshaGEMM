# 三国杀 GEMM · 统一启动页

完整解压 `SanguoshaGEMM-unified-windows.zip`，双击最外层的 **SanguoshaGEMM-Launcher.exe**。

页面有两个启动按钮：

- **启动原始版**：进入原始无优化版的“矩阵演武”输入页。
- **启动优化版**：进入跳过零项、自动选择计算方向版本的输入页。

启动后填写矩阵，选择正常、加速或极速，然后点击“进入牌桌”。支持行列 1–2、元素为 0–100 的非负整数。看动画请选择正常演示；大数值测试建议极速。

两个客户端可以同时运行，继续保持各自独立的配置、端口和记录目录。启动页不会关闭已经运行的客户端；关闭客户端后，对应按钮恢复可用。启动页只为本次启动的客户端防止重复点击。

统一包已经包含两个版本，不需要安装 Python 或 Qt。请保留两个 `SanguoshaGEMM-Baseline` / `SanguoshaGEMM-Optimized` 文件夹及启动器旁的 DLL、plugins、assets，不要单独移动 EXE。找不到某版本时，其按钮会禁用并提示完整解压。

在源码工作区中，启动器位于 `dist/SanguoshaGEMM-Launcher/`，自动使用相邻的两个版本目录。两个客户端现均采用统一大牌堆；资源与验收见 `UNIFORM_DECK.md`。旧性能记录仅对应其记录的程序哈希。

## 构建启动器

使用现有 Qt 5.5.1 / MinGW 4.9.2 工具链，无需重新构建两个游戏客户端：

```powershell
./scripts/build_launcher.ps1
python scripts/package_launcher.py
python scripts/test_launcher.py
python scripts/package_launcher.py --archive
```

`launcher/` 为启动页完整源码；启动器通过独立进程调用各版的 `--gemm` 入口，并使用对应程序的目录作为工作目录。测试在 Qt offscreen 后台运行，覆盖真实按钮启动、不同目标、两个进程存活、退出后按钮恢复及缺失版本，不读取或操作桌面。原版美术资源与许可证一并保留；完整对应源码随源码包提供。
