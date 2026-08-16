# -*- coding: utf-8 -*-
"""
bode_sweep.py (实验 1.2 验证标准)
扫描 Kp 和 L，观察增益穿越频率 fc 与相位裕度 PM 的变化
验证：Kp↑ → PM↓；L↑ → fc↓
"""
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

L0, C, R = 100e-6, 100e-6, 10.0
Ki = 1000.0
f = np.logspace(1, 6, 600)
s = 1j * 2*math.pi * f

def loop_metrics(L, Kp):
    Gvd = 1.0 / (s**2 * L * C + s * L/R + 1.0)
    Gc = Kp + Ki / s
    T = Gc * Gvd
    mag = 20*np.log10(np.abs(T))
    ph = np.unwrap(np.angle(T)) * 180/math.pi
    cross = np.where(np.diff(np.sign(mag)) != 0)[0]
    for ci in cross:
        if mag[ci] > 0 and mag[ci+1] < 0:
            f1, m1, f2, m2 = f[ci], mag[ci], f[ci+1], mag[ci+1]
            fcx = 10**((math.log10(f2/f1))*(0-m1)/(m2-m1) + math.log10(f1))
            p1, p2 = ph[ci], ph[ci+1]
            phc = p1 + (p2-p1)*(math.log10(fcx)-math.log10(f1))/(math.log10(f2)-math.log10(f1))
            return fcx, phc + 180
    return None, None

# ---- 扫描 Kp（固定 L=100uH）----
print('=== 扫描 Kp (L=100uH, Ki=1000) ===')
print('Kp\tfc(Hz)\tPM(deg)\t判据')
rows_kp = []
for Kp in [0.5, 1, 2, 5, 10, 20]:
    fcx, pm = loop_metrics(L0, Kp)
    if fcx:
        rows_kp.append((Kp, fcx, pm))
        print(f'{Kp:4.1f}\t{fcx:6.0f}\t{pm:6.1f}\t{"稳定" if pm > 45 else "临界" if pm > 0 else "不稳"}')

# ---- 扫描 L（固定 Kp=5）----
print('\n=== 扫描 L (Kp=5, Ki=1000) ===')
print('L(uH)\tfc(Hz)\tPM(deg)')
rows_L = []
for Lu in [50, 100, 150, 200, 400]:
    fcx, pm = loop_metrics(Lu*1e-6, 5.0)
    if fcx:
        rows_L.append((Lu, fcx, pm))
        print(f'{Lu:5.0f}\t{fcx:6.0f}\t{pm:6.1f}')

# ---- 绘图：Kp 扫描 ----
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
if rows_kp:
    kp_a = np.array([r[0] for r in rows_kp])
    fc_a = np.array([r[1] for r in rows_kp])
    pm_a = np.array([r[2] for r in rows_kp])
    ax[0].semilogx(kp_a, fc_a, 'b-o')
    ax[0].set_xlabel('Kp'); ax[0].set_ylabel('fc (Hz)')
    ax[0].grid(alpha=0.3); ax[0].set_title('Kp↑ → fc↑')
    ax[1].semilogx(kp_a, pm_a, 'r-o')
    ax[1].axhline(45, color='g', ls='--', lw=0.8)
    ax[1].set_xlabel('Kp'); ax[1].set_ylabel('PM (deg)')
    ax[1].grid(alpha=0.3); ax[1].set_title('Kp↑ → PM↓')
fig.tight_layout()
fig.savefig('bode_sweep_kp.png', dpi=120)
print('\n图已保存: bode_sweep_kp.png')
