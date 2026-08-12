# -*- coding: utf-8 -*-
"""
绘制 buck_hysteresis.cir 控制器的两个关键曲线：
1. sigmoid 函数 1/(1+exp(z))
2. 滞环积分器 Gint 的电流特性 I(Vout)（Vref=6V 和 8V）
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
# 中文字体（Windows）
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

# ============ 图1：sigmoid 函数 ============
z = np.linspace(-10, 10, 400)
s = 1 / (1 + np.exp(-z))   # 注意：sigmoid 标准形式是 1/(1+exp(-z))
# 脚本里 Gint 用的是 1/(1+exp(+z))（z 前的符号已并入参数），本质相同只是镜像

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(z, s, 'b-', lw=2, label=r'$1/(1+e^{-z})$')
ax.axhline(0.5, color='gray', ls='--', lw=0.8)
ax.axhline(1.0, color='gray', ls=':', lw=0.8)
ax.axhline(0.0, color='gray', ls=':', lw=0.8)
ax.annotate('z<0 → 1', xy=(-5, 0.99), fontsize=10, color='blue')
ax.annotate('z>0 → 0', xy=(5, 0.01), fontsize=10, color='blue')
ax.annotate('z=0 → 0.5', xy=(0.1, 0.52), fontsize=10, color='gray')
ax.set_xlabel('z')
ax.set_ylabel('sigmoid(z)')
ax.set_title('sigmoid 函数  1/(1+e^z)  (Gint 中用于平滑滞环)')
ax.grid(alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig('sigmoid.png', dpi=120)
plt.close(fig)

# ============ 图2：Gint 滞环电流特性 ============
def gint_current(vout, vref):
    """复现网表中的 Gint 表达式（去掉 0.2m 系数，显示归一化方向）"""
    return (1 / (1 + np.exp((vout - vref + 0.1) * 20))
            - 1 / (1 + np.exp((vref + 0.1 - vout) * 20)))

vout = np.linspace(4, 10, 600)
fig, ax = plt.subplots(figsize=(9, 5))
for vref, color in [(6.0, 'tab:blue'), (8.0, 'tab:red')]:
    I = 0.2e-3 * gint_current(vout, vref)          # 单位 A
    ax.plot(vout, I * 1e3, color=color, lw=2, label=f'Vref = {vref:.0f}V')
    # 标注窗口边界
    ax.axvspan(vref - 0.1, vref + 0.1, color=color, alpha=0.12)
    ax.axvline(vref - 0.1, color=color, ls='--', lw=0.8)
    ax.axvline(vref + 0.1, color=color, ls='--', lw=0.8)
    ax.text(vref, 0.16, f'{vref:.0f}V 窗口\n±0.1V', ha='center', fontsize=9, color=color)

ax.axhline(0, color='black', lw=1)
ax.annotate('Vout 过低 → +0.2mA\n(dctrl 充电, 占空比↑)', xy=(4.6, 0.13), fontsize=10)
ax.annotate('Vout 过高 → -0.2mA\n(dctrl 放电, 占空比↓)', xy=(9.6, -0.13), ha='right', fontsize=10)
ax.annotate('窗口内 → 0mA\n(保持, 电容记忆)', xy=(7.0, 0.02), ha='center', fontsize=10)
ax.set_xlabel('V(out) [V]')
ax.set_ylabel('Gint 电流 [mA]')
ax.set_title('滞环积分器 Gint 特性：I(Vout)，随 Vref 平移')
ax.set_xlim(4, 10)
ax.set_ylim(-0.25, 0.25)
ax.grid(alpha=0.3)
ax.legend(loc='upper left')
fig.tight_layout()
fig.savefig('hysteresis_Gint.png', dpi=120)
plt.close(fig)

print('已生成: sigmoid.png, hysteresis_Gint.png')
