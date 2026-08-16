# -*- coding: utf-8 -*-
"""parse_ac.py v3: 解析 LTspice .raw（UTF-16 头部 + 二进制复数数据）"""
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

with open('buck_ac.raw', 'rb') as f:
    raw = f.read()

# ---- UTF-16 头部 ----
txt16 = raw[:6000].decode('utf-16-le', errors='ignore')
bin_pos = txt16.find('Binary:')
if bin_pos < 0:
    raise RuntimeError('Binary marker not found')
head_txt = txt16[:bin_pos]

nvars = int([l for l in head_txt.splitlines() if 'No. Variables' in l][0].split(':')[1])
npts  = int([l for l in head_txt.splitlines() if 'No. Points' in l][0].split(':')[1])
names = []
for l in head_txt.splitlines():
    if l.startswith('\t'):
        parts = l.split('\t')
        if len(parts) >= 3:
            names.append(parts[2])   # 格式: \t编号\t名字\t类型
print('变量数:', nvars, '点数:', npts)
print('变量:', names)

# ---- 数据区（Binary: 行后，float64，偏移 2）----
data = raw[bin_pos*2 + 14:]   # 跳过 "Binary:"
sz = 8
stride = sz * (1 + 2*nvars)   # freq + nvars 复数
n = (len(data) - 2) // stride
arr = np.frombuffer(data[2:2+n*stride], dtype='<f8').reshape(n, 1 + 2*nvars)
print('数据点数:', n, '首频:', arr[0,0], '尾频:', arr[-1,0])

freq = arr[:, 0]
idx = names.index('V(out)')
vout = arr[:, 1+2*idx] + 1j*arr[:, 2+2*idx]
gvd = vout

# ---- 环路增益 T(s) = (Kp + Ki/s)*Gvd ----
Kp, Ki = 5.0, 1000.0
s = 1j*2*math.pi*freq
T = (Kp + Ki/s) * gvd
mag = 20*np.log10(np.abs(T))
ph = np.unwrap(np.angle(T)) * 180/math.pi

cross = np.where(np.diff(np.sign(mag)) != 0)[0]
fc, PM = None, None
for ci in cross:
    if mag[ci] > 0 and mag[ci+1] < 0:
        f1, m1, f2, m2 = freq[ci], mag[ci], freq[ci+1], mag[ci+1]
        fc = 10**((math.log10(f2/f1))*(0-m1)/(m2-m1) + math.log10(f1))
        p1, p2 = ph[ci], ph[ci+1]
        phc = p1 + (p2-p1)*(math.log10(fc)-math.log10(f1))/(math.log10(f2)-math.log10(f1))
        PM = phc + 180
        break

print(f'\n=== 环路增益 T(s) (Kp={Kp}, Ki={Ki}) ===')
if fc:
    print(f'增益穿越频率 fc = {fc:.0f} Hz')
    print(f'相位裕度 PM    = {PM:.1f} deg')
    print('判据 PM>45°:', '稳定 ✓' if PM > 45 else '不稳定 ✗')
else:
    print('无增益穿越')

# ---- 波特图 ----
fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
ax[0].semilogx(freq, mag, 'b-', lw=1.5)
ax[0].axhline(0, color='r', ls='--', lw=0.8)
if fc:
    ax[0].axvline(fc, color='r', ls=':', lw=0.8)
    ax[0].annotate(f'fc={fc:.0f}Hz', xy=(fc, 3), fontsize=10, color='r')
ax[0].set_ylabel('|T| (dB)')
ax[0].grid(alpha=0.3, which='both')
ax[0].set_title(f'环路增益 T(s) 波特图 (Kp={Kp}, Ki={Ki})')

ax[1].semilogx(freq, ph, 'b-', lw=1.5)
ax[1].axhline(-180, color='r', ls='--', lw=0.8)
if fc:
    ax[1].axvline(fc, color='r', ls=':', lw=0.8)
    ax[1].annotate(f'PM={PM:.0f}°', xy=(fc, -150), fontsize=10, color='r')
ax[1].set_ylabel('相位 (°)')
ax[1].set_xlabel('频率 (Hz)')
ax[1].grid(alpha=0.3, which='both')
fig.tight_layout()
fig.savefig('bode_T.png', dpi=120)
print('\n图已保存: bode_T.png')
