"""Generate the expanded-run result note from measured values only."""
import json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
s=json.loads((ROOT/'evidence/expanded/suite-v1/summary.json').read_text(encoding='utf-8'))
assert s['status']=='complete' and s['passed']==12 and not s['failed']
lines=['# 大数值 2×2 实测结果','',
       '2026-11-03，两版真实 QSanguosha Windows Release 程序，后台极速（speed=2），无桌面自动化。', '',
       '**12 组唯一的 2×2 输入，每例每版 1 次预热＋3 次实测，共 96 次调用，全部结果正确。** 输入在计时前固定，包含全 10/25/50/100、两组随机稠密、左右数值不对称、稀疏和左右零矩阵。每轮交替版本先后顺序，进程串行运行。', '',
       '两个版本均支持 0–100，并使用相同的大牌堆：800 杀、800 救援牌、131,072 张可摸牌。扩容不预先计算答案。全 100 实际执行 800 次出杀与救援，每个结果武将 20,000 张手牌，全场 80,000 张。', '',
       '## 全部测量','',
       '时间单位为秒，数值均为实测中位数。纯引擎和准备＋结算不含程序启动；总时间包含启动、资源加载和记录写出。', '',
       '| 输入 | 出杀 原始→优化 | 实际摸牌 | 引擎 原始 / 优化 | 准备＋结算 原始 / 优化 | 含启动总时间 原始 / 优化 |',
       '| --- | ---: | ---: | ---: | ---: | ---: |']
for c in sorted(s['cases'],key=lambda x:x['id']):
    b,o=c['baseline'],c['optimized']
    times=['%.3f / %.3f'%(b[k]/1000,o[k]/1000) for k in ['medianMs','medianComputeMs','medianProcessWallMs']]
    lines.append('| %s | %s→%s | %s | %s |'%(c['id'],b['activeCardUses'],o['activeCardUses'],b['drawnCards'],' | '.join(times)))
c=next(c for c in s['cases'] if c['id']=='all-100');b,o=c['baseline'],c['optimized']
lines+=['','## 结果如何理解','',
        '全 100 的任务数相同，两版引擎分别为 %.3f / %.3f 秒，准备＋结算 %.3f / %.3f 秒，含启动 %.3f / %.3f 秒；实测工作集峰值分别 %.2f / %.2f MiB。该输入没有跳零或转置收益，不能把扩容本身当作算法加速。'%(b['medianMs']/1000,o['medianMs']/1000,b['medianComputeMs']/1000,o['medianComputeMs']/1000,b['medianProcessWallMs']/1000,o['medianProcessWallMs']/1000,b['peakWorkingSetMiB'],o['peakWorkingSetMiB']), '',
        '按准备＋结算中位数比、以 ±5%% 为展示区间：%d 组更快、%d 组接近、%d 组更慢。只有 3 个实测样本，快慢分档不表示统计显著性；尤其是任务相同的用例，不应把小幅差异归因于算法。'%(s['faster'],s['similar'],s['slower']), '',
        '大牌堆的卡牌对象和房间状态需要加载，即使优化版零出牌，完整程序调用仍有明显成本。报告保留三种时间，避免只展示纯结算倍数。旧 96 例是旧二进制的历史测量；本轮共同更新了资源和日志查找，不混用新旧耗时。', '',
        '## 验证与范围','',
        '原始记录及可筛选报告：`evidence/expanded/suite-v1/`。`verify_expanded.py` 检查全部 96 份记录的实际结果手牌、唯一牌 ID、固定牌堆、救援后 1 血、每步摸牌与累加连续性，以及两种任务安排。独立整数乘法只用于核验。普通牌堆不包含扩展计算牌，故障必须停止而不是返回成功。', '',
        '这是数值范围扩大后的 2×2 游戏计算，不是大维度 BLAS。当前仍限制维度 1–2、整数 0–100；没有 GPU 性能数据，未进行大手牌 GUI 的最终人工验收。用户已取消 3×3/4×4 方向。']
(ROOT/'docs/EXPANDED_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Wrote docs/EXPANDED_RESULTS.md from complete measurements')
