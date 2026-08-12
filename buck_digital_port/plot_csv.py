# -*- coding: utf-8 -*-
"""
plot_csv.py
读取 C 语言仿真的 c_result.csv（t, vout, dctrl）并绘图
与 MATLAB 的 matlab_result.png 对应，便于三方波形对比
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

# 读取 CSV
data = np.loadtxt('c_result.csv', delimiter=',', skiprows=1)
t     = data[:, 0] * 1e3        # s -> ms
vout  = data[:, 1]
dctrl = data[:, 2]

# Vref 斜坡（与控制器一致）
vref = 6 + 2 * np.clip((t*1e-3 - 10e-3) / 0.1e-3, 0, 1)

# 稳态统计
idx = (t >= 18) & (t <= 25)
print(f'=== c_result.csv 统计 (18-25ms) ===')
print(f'Vout_avg : {vout[idx].mean():.4f} V')
print(f'Dctrl_avg: {dctrl[idx].mean():.4f} V')
print(f'Duty     : {dctrl[idx].mean()/12*100:.2f} %')

# 绘图
fig, ax = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

ax[0].plot(t, vout, 'b-', lw=0.8, label='Vout (C)')
ax[0].plot(t, vref, 'r--', lw=1.2, label='Vref')
ax[0].set_ylabel('Vout (V)')
ax[0].set_ylim(0, 10)
ax[0].grid(alpha=0.3)
ax[0].legend(loc='lower right')
ax[0].set_title('Buck 滞环闭环（C 语言离散化）：Vout 与 Vref')

ax[1].plot(t, dctrl/12*100, 'g-', lw=0.8, label='Duty (C)')
ax[1].set_ylabel('Duty (%)')
ax[1].set_xlabel('t (ms)')
ax[1].set_ylim(40, 80)
ax[1].grid(alpha=0.3)
ax[1].legend(loc='lower right')
ax[1].set_title('占空比指令（dctrl/12×100%）')

fig.tight_layout()
fig.savefig('c_result.png', dpi=120)
print('图已保存: c_result.png')
