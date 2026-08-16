# -*- coding: utf-8 -*-
"""
type2_design.py — Type-II 补偿器设计工具
Gc(s) = G0·(1+s/ωz) / (s·(1+s/ωp))
3 个自由度：G0（增益）、fz（零点）、fp（高频极点）
对比 PI（2 自由度）：Type-II 多一个高频极点 → PM 可真正设计到 60°

用法：
    python type2_design.py                    # 默认 L=100uH, fc=f0/5
    python type2_design.py 100u 100u 10 500   # 指定 L C R fc
    python type2_design.py --pm60             # 迭代 fz 使 PM=60°
    python type2_design.py --fz 1592 --fp 5000  # 指定零点/极点
"""
import sys, math

def parse_eng(s):
    units = {'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3,
             'k': 1e3, 'K': 1e3, 'meg': 1e6, 'M': 1e6}
    s = s.strip().lower()
    for suf, mult in sorted(units.items(), key=lambda x: -len(x[0])):
        if s.endswith(suf):
            return float(s[:-len(suf)]) * mult
    return float(s)

# ---- 参数 ----
L, C, R = 100e-6, 100e-6, 10.0
fc = None
fz = None
fp = None
pm_target = None

args = sys.argv[1:]
vals = []
for a in args:
    if a == '--pm60':
        pm_target = 60.0
    elif a.startswith('--fz'):
        fz = parse_eng(a.split()[1]) if ' ' in a else parse_eng(args[args.index(a)+1])
    elif a.startswith('--fp'):
        fp = parse_eng(args[args.index(a)+1])
    elif not a.startswith('--'):
        vals.append(parse_eng(a))
if len(vals) >= 3:
    L, C, R = vals[0], vals[1], vals[2]
if len(vals) >= 4:
    fc = vals[3]

f0 = 1.0 / (2*math.pi*math.sqrt(L*C))
if fc is None:
    fc = f0 / 5.0

# ---- Gvd ----
def gvd_at(f):
    w = 2*math.pi*f
    s = 1j*w
    return 1.0 / (s**2*L*C + s*L/R + 1.0)

# ---- Type-II 设计 ----
def type2_calc(fc, fz, fp):
    wc = 2*math.pi*fc
    wz = 2*math.pi*fz
    wp = 2*math.pi*fp
    gvd = gvd_at(fc)
    mag_gvd = abs(gvd)
    ph_gvd = math.degrees(math.atan2(gvd.imag, gvd.real))
    # |Gc(fc)| = G0·|1+jwc/wz|/(wc·|1+jwc/wp|)
    num = math.sqrt(1 + (wc/wz)**2)
    den = wc * math.sqrt(1 + (wc/wp)**2)
    G0 = 1.0 / (mag_gvd * num / den)
    # ∠Gc(fc) = atan(wc/wz) - 90° - atan(wc/wp)
    ph_gc = math.degrees(math.atan(wc/wz)) - 90.0 - math.degrees(math.atan(wc/wp))
    pm = 180.0 + ph_gc + ph_gvd
    return G0, pm, ph_gc, ph_gvd, mag_gvd

# ---- 运放元件反推（Type-II 运放实现）----
# Gc(s) = (1+sR2C1) / (sR1(C1+C2)(1+sR2C1C2/(C1+C2)))
# 精确反推（给定 G0/fz/fp/Cf1）：
#   fz = 1/(2πR2·Cf1) → R2
#   fp = 1/(2πR2·Cf1Cf2/(Cf1+Cf2)) → Cf2 = 1/(2π·fp·R2 - 1/Cf1)
#   G0 = 1/(Rin·(Cf1+Cf2)) → Rin
def to_opamp(G0, fz, fp):
    Cf1 = 10e-9          # 选 Cf1 = 10nF
    R2 = 1.0/(2*math.pi*fz*Cf1)
    denom = 2*math.pi*fp*R2 - 1.0/Cf1
    Cf2 = 1.0/denom if denom > 0 else 1e-12
    Rin = 1.0/(G0*(Cf1+Cf2))
    return Rin, R2, Cf1, Cf2

# ---- 时域预估（闭环极点分析）----
def time_response(L, C, R, G0, fz, fp):
    """
    闭环特征多项式：1 + Gc·Gvd = 0
    Gc = G0(1+s/wz)/(s(1+s/wp)) = Gp·(s+wz)/(s(s+wp)), Gp = G0·wp/wz
    Gvd = 1/(LC·s² + L/R·s + 1)
    → s(s+wp)(LC·s²+L/R·s+1) + Gp(s+wz) = 0
    返回主导极点、阻尼比、超调、调节时间
    """
    import numpy as np
    wz = 2*math.pi*fz
    wp = 2*math.pi*fp
    Gp = G0*wp/wz          # 传函 (s+wz)/(s(s+wp)) 的正确增益
    # 展开系数（4 阶）
    c4 = L*C
    c3 = L/R + wp*L*C
    c2 = 1.0 + wp*L/R
    c1 = wp + Gp
    c0 = Gp*wz
    # companion matrix 特征值（数值稳定）
    A = np.array([[-c3/c4, -c2/c4, -c1/c4, -c0/c4],
                  [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]], dtype=float)
    roots = np.linalg.eigvals(A)
    # 主导极点：实部绝对值最小（最慢）的极点
    real = roots.real
    idx = np.argmin(np.abs(real))
    dom = roots[idx]
    if np.max(real) > 0:
        return 'unstable', None, None, None, None, dom
    if abs(dom.imag) > 1e-6:
        # 共轭复主导极点 → 欠阻尼
        zeta = -dom.real / abs(dom)
        wn = abs(dom)
        overshoot = 100*math.exp(-math.pi*zeta/math.sqrt(1-zeta**2))
        ts = 4.0/(zeta*wn)
        return 'underdamped', zeta, wn, overshoot, ts, dom
    else:
        # 实主导极点 → 过阻尼
        tau = 1.0/np.min(np.abs(real))
        return 'overdamped', None, None, 0.0, 4*tau, dom

# ---- 主流程 ----
print('='*62)
print(f'Type-II 补偿器设计 (L={L*1e6:.0f}uH, C={C*1e6:.0f}uF, R={R:.0f}ohm)')
print(f'f0 = {f0:.0f} Hz, fc = {fc:.0f} Hz = f0/{f0/fc:.1f}')
print('='*62)

if fz is None:
    fz = f0               # 默认零点在 LC 谐振（补偿双极点相位）
if fp is None:
    fp = max(10*fc, 2*fz) # 默认高频极点：≥10×fc 且 >2×fz（保证 fp>fz）

G0, pm, ph_gc, ph_gvd, mag_gvd = type2_calc(fc, fz, fp)
print(f'\n--- 初始设计 (fz={fz:.0f}Hz=f0, fp={fp:.0f}Hz=10fc) ---')
print(f'|Gvd(fc)| = {mag_gvd:.3f}, ∠Gvd = {ph_gvd:.1f}°')
print(f'∠Gc(fc)   = {ph_gc:.1f}°  (零点半程提升)')
print(f'G0        = {G0:.6f}')
print(f'PM        = {pm:.1f}°')

# ---- 第二穿越诊断（f0 谐振处 |T| 检查）----
# |Gvd(f0)| = Q = R·√(C/L)，谐振峰高时 f0 处 |T| 可能 >1 → 高频不稳定
w0 = 2*math.pi*f0
wz = 2*math.pi*fz
wp = 2*math.pi*fp
Q = R*math.sqrt(C/L)
Gc_f0 = G0*math.sqrt(1+(w0/wz)**2)/(w0*math.sqrt(1+(w0/wp)**2))
T_f0 = Gc_f0*Q
G0_max = w0*math.sqrt(1+(w0/wp)**2)/(math.sqrt(1+(w0/wz)**2)*Q)
print(f'\n--- 第二穿越诊断（关键）---')
print(f'Q = {Q:.1f}（谐振峰 |Gvd(f0)| = Q）')
print(f'|T(f0)| = {T_f0:.2f}  ({"<1 无第二穿越 OK" if T_f0 < 1 else ">1 有第二穿越，高频可能不稳定!"})')
print(f'G0 上限（防第二穿越）= {G0_max:.0f}  (当前 G0={G0:.0f})')
if T_f0 >= 1:
    print(f'[警告] 设计需调整：降低 G0 到 {G0_max:.0f} 以下，或降低 fc / 调整 fz')
    print(f'   提示：fc 降低 → G0 随 wc 减小 → 更容易满足；当前 fc={fc:.0f} 偏激进')

# 可选：迭代 fp 使 PM 到目标（fz 固定 = f0，补偿 LC）
# ∠Gc = atan(wc/wz) - 90 - atan(wc/wp)
# fp 移近 fc → atan(wc/wp) 增大 → ∠Gc 更负 → PM 下降
if pm_target is not None:
    print(f'\n--- 迭代 fp 使 PM = {pm_target:.0f}° (fz 固定=f0) ---')
    fp_lo, fp_hi = fc, fc*100
    for _ in range(60):
        fp_mid = (fp_lo+fp_hi)/2
        _, pm_t, _, _, _ = type2_calc(fc, fz, fp_mid)
        if pm_t > pm_target:
            fp_hi = fp_mid      # PM 太高 → fp 移近 fc（PM 降）
        else:
            fp_lo = fp_mid      # PM 太低 → fp 移远（PM 升）
    fp = (fp_lo+fp_hi)/2
    G0, pm, ph_gc, ph_gvd, mag_gvd = type2_calc(fc, fz, fp)
    print(f'fp = {fp:.0f} Hz = {fp/fc:.1f}×fc, G0 = {G0:.6f}, PM = {pm:.1f}°')

# 运放元件（精确反推）
Rin, R2, Cf1, Cf2 = to_opamp(G0, fz, fp)
print(f'\n--- 运放实现元件（Type-II，精确反推）---')
print(f'Rin = {Rin/1e3:.2f} kΩ  (输入电阻)')
print(f'R2  = {R2/1e3:.2f} kΩ  (反馈电阻)')
print(f'Cf1 = {Cf1*1e9:.2f} nF  (零点 fz=1/(2πR2·Cf1))')
print(f'Cf2 = {Cf2*1e12:.2f} pF  (极点 fp=1/(2πR2·Cf1Cf2/(Cf1+Cf2)))')

# ---- 时域预估 ----
print(f'\n--- 时域预估（闭环极点分析）---')
mode, zeta, wn, ov, ts, dom = time_response(L, C, R, G0, fz, fp)
if mode == 'underdamped':
    print(f'主导极点: {dom.real:.1f} ± j{dom.imag:.1f} (欠阻尼)')
    print(f'阻尼比 ζ   = {zeta:.3f}')
    print(f'自然频率 ωn = {wn/6.2832:.0f} Hz')
    print(f'预估超调   = {ov:.1f}%  (二阶近似)')
    print(f'预估调节时间 ts(2%) = {ts*1e3:.1f} ms')
elif mode == 'overdamped':
    print(f'主导极点: {dom.real:.1f} (过阻尼，无超调)')
    print(f'预估调节时间 ts(2%) = {ts*1e3:.1f} ms')
else:
    print(f'⚠️ 闭环不稳定（主导极点实部 {dom.real:.1f}）——时域必然振荡/发散')

print(f'\n--- 软启动 / 输出钳位提示 ---')
print(f'1. 启动时 Vout=0 → 误差大 → 补偿器输出饱和（占空比 100%）→ 过冲')
print(f'   → 建议：Vref 用斜坡软启动（buck_type2.cir 已有 0.1ms 斜坡）')
print(f'   → 或限制补偿器输出（运放限幅 0~12V，防积分饱和）')
print(f'2. 预估超调 > 20% 时：降 G0（增大 Rin）或调软启动，再 .tran 验证')

print(f'\n--- LTspice 网表片段（Type-II 运放实现）---')
print(f'Berr err 0 V=V(out)-V(ref)')
print(f'Rin err vn {Rin/1e3:.2f}k')
print(f'R2 vop vm {R2/1e3:.2f}k')
print(f'Cf1 vm vn {Cf1*1e9:.2f}n')
print(f'Cf2 vop vn {Cf2*1e12:.2f}p')
print(f'Eop vop 0 VALUE={{limit(-1e6*V(vn), -15, 15)}}')
