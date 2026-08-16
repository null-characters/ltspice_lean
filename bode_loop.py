# -*- coding: utf-8 -*-
"""
bode_loop.py (实验 1.2)
平均化 Buck 小信号模型 + PI 控制器，解析计算环路增益 T(s)
验证：10Hz 处 |Gvd|≈0dB（与 LTspice .ac 的 .meas 一致）

功率级（CCM 平均模型）：
  Gvd(s) = 1 / (s^2*L*C + s*L/R + 1)     （dctrl 电压直接映射开关平均电压）
控制器（PI）：
  Gc(s) = Kp + Ki/s
环路增益：T(s) = Gc(s) * Gvd(s)
"""
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

# ---- 参数 ----
L, C, R = 100e-6, 100e-6, 10.0
Kp, Ki = 5.0, 1000.0

f = np.logspace(1, 6, 500)          # 10Hz ~ 1MHz
s = 1j * 2*math.pi * f

Gvd = 1.0 / (s**2 * L * C + s * L/R + 1.0)
Gc  = Kp + Ki / s
T   = Gc * Gvd

mag = 20*np.log10(np.abs(T))
ph  = np.unwrap(np.angle(T)) * 180/math.pi

# ---- 穿越频率 + 相位裕度 ----
cross = np.where(np.diff(np.sign(mag)) != 0)[0]
fc, PM = None, None
for ci in cross:
    if mag[ci] > 0 and mag[ci+1] < 0:
        f1, m1, f2, m2 = f[ci], mag[ci], f[ci+1], mag[ci+1]
        fc = 10**((math.log10(f2/f1))*(0-m1)/(m2-m1) + math.log10(f1))
        p1, p2 = ph[ci], ph[ci+1]
        phc = p1 + (p2-p1)*(math.log10(fc)-math.log10(f1))/(math.log10(f2)-math.log10(f1))
        PM = phc + 180
        break

print(f'=== 环路增益 T(s) (Kp={Kp}, Ki={Ki}, L={L*1e6:.0f}uH, C={C*1e6:.0f}uF) ===')
if fc:
    print(f'增益穿越频率 fc = {fc:.0f} Hz')
    print(f'相位裕度 PM    = {PM:.1f} deg')
    print('判据 PM>45:', '稳定' if PM > 45 else '不稳定')
else:
    print('无增益穿越')

# ---- 波特图 ----
fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
ax[0].semilogx(f, mag, 'b-', lw=1.5)
ax[0].axhline(0, color='r', ls='--', lw=0.8)
if fc:
    ax[0].axvline(fc, color='r', ls=':', lw=0.8)
    ax[0].annotate(f'fc={fc:.0f}Hz', xy=(fc, 3), fontsize=10, color='r')
ax[0].set_ylabel('|T| (dB)')
ax[0].grid(alpha=0.3, which='both')
ax[0].set_title(f'环路增益 T(s) 波特图 (Kp={Kp}, Ki={Ki})')

ax[1].semilogx(f, ph, 'b-', lw=1.5)
ax[1].axhline(-180, color='r', ls='--', lw=0.8)
if fc:
    ax[1].axvline(fc, color='r', ls=':', lw=0.8)
    ax[1].annotate(f'PM={PM:.0f}°', xy=(fc, -150), fontsize=10, color='r')
ax[1].set_ylabel('相位 (°)')
ax[1].set_xlabel('频率 (Hz)')
ax[1].grid(alpha=0.3, which='both')
fig.tight_layout()
fig.savefig('bode_T.png', dpi=120)
print('图已保存: bode_T.png')
