# -*- coding: utf-8 -*-
"""
buck_pi_design.py — Buck PI 控制器设计工具（环路法）
基于实验 1.2 的手推流程：由目标穿越频率 fc 反推 Kp/Ki，并验证相位裕度。

用法：
    python buck_pi_design.py                 # 默认参数（L=100uH, fc=f0/5）
    python buck_pi_design.py 10u 100u 10 300 # L=10uH C=100uF R=10 fc=300Hz
    python buck_pi_design.py --iter           # 自动迭代找 PM=60° 的最大 fc

输出：
    Kp, Ki, fc, PM（可在 LTspice 中验证）
"""
import sys
import math

# ============ 参数 ============
def parse_eng(s):
    """解析工程记法: 100u -> 1e-4, 10 -> 10, 1meg -> 1e6"""
    units = {'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3,
             'k': 1e3, 'K': 1e3, 'meg': 1e6, 'M': 1e6}
    s = s.strip().lower()
    for suf, mult in sorted(units.items(), key=lambda x: -len(x[0])):
        if s.endswith(suf):
            return float(s[:-len(suf)]) * mult
    return float(s)

# 默认值
L, C, R = 100e-6, 100e-6, 10.0
fc_target = None      # None -> 自动取 f0/5
pm_target = 60.0      # 迭代目标相位裕度

# 命令行解析
args = sys.argv[1:]
if args:
    try:
        vals = [parse_eng(a) for a in args if not a.startswith('--')]
        if len(vals) >= 3:
            L, C, R = vals[0], vals[1], vals[2]
        if len(vals) >= 4:
            fc_target = vals[3]
    except ValueError:
        pass

do_iter = '--iter' in args

# ============ 核心计算 ============
def gvd_at(L, C, R, f):
    """Gvd(s) = 1/(s^2*LC + s*L/R + 1) 在频率 f 处的复数"""
    w = 2 * math.pi * f
    s = 1j * w
    return 1.0 / (s**2 * L * C + s * L / R + 1.0)

def design(L, C, R, fc):
    """给定 fc，设计 PI 参数（零点 = fc/10）"""
    wc = 2 * math.pi * fc
    gvd = gvd_at(L, C, R, fc)
    mag_gvd = abs(gvd)
    ph_gvd = math.degrees(math.atan2(gvd.imag, gvd.real))

    # 步骤2: PI 零点 = fc/10
    wz = wc / 10.0

    # 步骤3: |T(fc)|=1 -> Kp
    kp = 1.0 / (mag_gvd * math.sqrt(1 + (wz/wc)**2))

    # 步骤4: Ki = wz*Kp
    ki = wz * kp

    # 步骤5: 验证 PM
    ph_gc = -math.degrees(math.atan((ki/wc) / kp))
    pm = 180.0 + ph_gc + ph_gvd
    return kp, ki, pm, mag_gvd, ph_gvd

def f0_of(L, C):
    return 1.0 / (2 * math.pi * math.sqrt(L * C))

# ============ 主流程 ============
f0 = f0_of(L, C)
print('=' * 60)
print(f'Buck PI 设计  (L={L*1e6:.0f}uH, C={C*1e6:.0f}uF, R={R:.0f}ohm)')
print(f'LC 谐振 f0 = {f0:.0f} Hz')
print('=' * 60)

if do_iter:
    # 迭代找 PM=pm_target 的最大 fc
    # 注意：零点=fc/10 规则下 ∠Gc=-5.7° 恒定，PM 下限 = 180-5.7-90 = 84°
    # 所以 pm_target 若 <84° 不可达（需改零点规则），脚本报告边界
    print(f'\n迭代找 PM ≈ {pm_target:.0f}° 的最大 fc ...')
    fc_lo, fc_hi = f0/50, f0*0.95
    best = None
    for _ in range(50):
        fc_mid = (fc_lo + fc_hi) / 2
        _, _, pm, _, _ = design(L, C, R, fc_mid)
        best = (fc_mid, pm)
        if pm > pm_target:
            fc_lo = fc_mid
        else:
            fc_hi = fc_mid
    fc, pm_actual = best
    kp, ki, pm, mag_gvd, ph_gvd = design(L, C, R, fc)
    if pm_actual > pm_target + 0.5:
        print(f'注意: 零点=fc/10 规则下 PM 下限≈84°，目标 {pm_target:.0f}° 不可达')
        print(f'最大 fc 受限于 f0（进入谐振区后 |Gvd| 剧变，需精确设计）')
    print(f'迭代结果: fc = {fc:.0f} Hz = f0/{f0/fc:.1f}, PM = {pm_actual:.1f}°')
else:
    if fc_target is None:
        fc = f0 / 5.0
        print(f'未指定 fc，使用默认 f0/5 = {fc:.0f} Hz')
    else:
        fc = fc_target
    kp, ki, pm, mag_gvd, ph_gvd = design(L, C, R, fc)
    print(f'目标 fc = {fc:.0f} Hz = f0/{f0/fc:.1f}')

print(f'\n--- 设计结果 ---')
print(f'|Gvd(fc)| = {mag_gvd:.3f}  ({20*math.log10(mag_gvd):.1f} dB)')
print(f'∠Gvd(fc) = {ph_gvd:.1f} deg')
print(f'Kp = {kp:.3f}')
print(f'Ki = {ki:.1f}')
print(f'PI 零点 fz = {ki/kp/2/math.pi:.0f} Hz = fc/10')
print(f'相位裕度 PM = {pm:.1f} deg  ({"稳定" if pm>45 else "危险" if pm>0 else "不稳定"})')
print(f'\n--- LTspice 网表片段 ---')
print(f'.param Kp={kp:.3f}')
print(f'.param Ki={ki:.1f}')
print(f'Gi 0 int VALUE={{Ki*1u*tanh(V(err)/1)}}')
print(f'Bp dctrl int V=Kp*tanh(V(err)/1)')
