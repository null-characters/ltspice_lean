# buck_hysteresis.cir 网表解析

> 滞环占空比闭环控制 Buck 电路 —— 逐行/逐模块解析

---

## 1. 文件总览

```
文件名：buck_hysteresis.cir
电路：Buck 降压 + 自举驱动 + 滞环闭环控制（非 PI）
特性：50kHz 固定频率 PWM，Vref 可编程（10ms 处 6V→8V）
```

### 信号链

```
Vref(目标) ──┐
             ├→ Gint 滞环积分 → dctrl(占空比指令)
Vout(反馈) ──┘         │
                        ↓
锯齿波 tri ──→ Bpwm 比较 ──→ PWM ──→ B1 驱动 ──→ M1 开关
                                                      ↓
                                        L1/D1/C1 功率级 → Vout
```

---

## 2. 文件头（1-4 行）—— 注释

```spice
*Buck Converter - Hysteresis Duty-Cycle Control (Closed Loop)
*50kHz PWM (100kHz long sims >14ms hang in batch mode), duty adjusted by hysteresis:
*  Vout < Vref-0.1 -> duty up ; Vout > Vref+0.1 -> duty down ; else hold
*Output regulated to Vref +/- 0.1V. Vref steps 6V->8V at 10ms.
```

- `*` 开头 = 注释行，LTspice 忽略
- 记录：电路类型、**50kHz 选择原因**（100kHz 长仿真 >14ms 会卡死）、控制逻辑、Vref 突变设计

---

## 3. 输入电源（第 6 行）

```spice
Vin in 0 12
```

| 语法 | 含义 |
|------|------|
| `Vin` | 电源实例名 |
| `in` / `0` | 正端节点 / 负端节点（0 = 地）|
| `12` | 直流电压值 |

→ 12V 直流输入。

---

## 4. 滞环控制器（8-28 行）—— 核心模块

### 4.1 锯齿波载波（9-11 行）

```spice
Vtri tri 0 PULSE(0 12 0 19.6u 0.2u 0.2u 20u)
```

**PULSE 参数格式：**
```
PULSE(V1 V2 Tdelay Trise Tfall Ton Tperiod)
PULSE(0  12 0      19.6u 0.2u  0.2u 20u)
```

| 参数 | 值 | 含义 |
|------|-----|------|
| V1/V2 | 0/12V | 低电平/高电平 |
| Tdelay | 0 | 延迟 |
| Trise | 19.6µs | 0→12V 线性上升时间 |
| Tfall | 0.2µs | 12V→0 下降时间 |
| Ton | 0.2µs | 高电平保持 |
| Tperiod | 20µs | 周期 = 50kHz |

**注意**：Trise+Ton+Tfall = 19.6+0.2+0.2 = **20µs = 周期**，否则波形溢出异常。
→ 形成 0~12V 锯齿波，斜率 12V/19.6µs，作为 PWM 比较载波。

### 4.1.1 设计知识：为什么用"梯形"近似"锯齿"？

**波形本质**：98% 时间线性上升 + 1% 平顶 + 1% 快降。
- 从**控制功能**上 ≡ 理想锯齿波：比较器只看电压何时达到 V(dctrl)，上升斜坡线性即可保证 PWM 线性调制关系

**严格术语**：PULSE 源天生是**梯形波**——用"长上升沿 + 短下降沿"拼凑出锯齿效果（对称三角波是 50% 升 + 50% 降）

**仿真收敛优化（数值整形技巧）**：
- 理想锯齿波波峰处 12V→0V 瞬间跳变 = 不可导突变 → SPICE 反复迭代，易报 `Time Step Too Small`
- 加 0.2µs 平顶/快降 → 给出明确斜率（dv/dt = 60V/µs），连续可导 → 仿真顺畅
- **代价可忽略**：最大占空比理论极限 99%（非 100%），1% 牺牲换几百倍仿真加速

**一句话**：物理上是锯齿波，代码里是梯形波参数，目的是仿真不死机。

### 4.2 参考电压（12-13 行）

```spice
Bref ref 0 V=6+2*limit((time-10m)/0.1m,0,1)
```

- `Bref` = 行为电压源（输出由表达式计算）
- `time` = 当前仿真时间
- `(time-10m)/0.1m`：10ms 前为负，之后线性增大
- `limit(x,0,1)`：钳位到 0~1

| 时间段 | 表达式值 | Vref |
|--------|----------|------|
| 0~10ms | 0 | **6V** |
| 10~10.1ms | 0→1 | 6V→**8V** 斜坡 |
| >10.1ms | 1 | **8V** |

→ 用 `limit()` 生成平滑斜坡，避免瞬间跳变导致数值崩溃。

### 4.3 滞环积分器（14-22 行）—— 核心中的核心

```spice
Gint 0 dctrl VALUE={0.2m*(1/(1+exp((V(out)-V(ref)+0.1)*20)) - 1/(1+exp((V(ref)+0.1-V(out))*20)))}
Cdctrl dctrl 0 1u ic=6
Rdc dctrl 0 100meg
```

**`Gint`** = 行为电流源，电流由 sigmoid 表达式决定：
- `1/(1+exp(z))`：sigmoid 函数（z 很负→1，z 很正→0，平滑过渡）
- 第一项 `1/(1+exp((Vout-Vref+0.1)*20))`：
  - `Vout < Vref-0.1` → 接近 **+0.2mA**（充电）
- 第二项 `1/(1+exp((Vref+0.1-Vout)*20))`：
  - `Vout > Vref+0.1` → 接近 **-0.2mA**（放电）
- 窗口内（Vref±0.1）→ 两项抵消 ≈ **0**（保持）

| Vout 状态 | Gint 电流 | dctrl 方向 |
|-----------|-----------|------------|
| 低于下阈值 | +0.2mA | 充电，占空比↑ |
| 窗口内 | ≈0 | 保持（电容记忆）|
| 高于上阈值 | -0.2mA | 放电，占空比↓ |

**`Cdctrl`**：积分电容，`Gint` 电流充放电 → `dctrl` 电压 = 占空比指令。
- `ic=6` = 初始条件 6V = 50% 占空比
- **电容的记忆 = 滞环死区**

**`Rdc`**：100MΩ 泄漏电阻，给 dctrl 直流参考点（防 .op 悬空）。

### 4.4 dctrl 钳位（23-26 行）

```spice
Dclamp1 0 dctrl DCLAMP
Dclamp2 dctrl vcc DCLAMP
```

两个二极管把 dctrl 钳位在 **0~12V**：
- `Dclamp1`：dctrl<0 导通 → 拉回 0
- `Dclamp2`：dctrl>12V(vcc) 导通 → 拉回 12V
→ 防止积分漂移导致占空比饱和失控。

### 4.5 PWM 比较器（27-28 行）

```spice
Bpwm pwm 0 V=if(V(tri)<V(dctrl), 12, 0)
```

锯齿波 tri 低于占空比指令 dctrl → 输出 12V（导通），否则 0V（关断）。

| dctrl | 占空比 |
|-------|--------|
| 6V | 50% |
| 8V | ~67% |
| 12V | 100% |

---

## 5. 自举电路（30-37 行）

```spice
Vcc vcc 0 12        ; 12V 辅助电源
Db vcc boot D       ; 自举二极管：Vcc→boot
Cb boot sw 100n     ; 自举电容：boot↔sw（下端接 sw）
Rboot boot 0 1meg   ; 直流路径（防 .op 悬空）
```

**原理：**
1. M1 关断（D1 续流，sw≈-0.7V）→ Cb 通过 Db 充电至 ~11.3V
2. M1 导通（sw 上升）→ Cb 下端被抬高，`boot = sw + 11.3V`
3. 高边 NMOS 的 **Vgs 恒定 ~11.5V**，不随 sw 变化

`Rboot`：电容在 .op 时开路会导致 boot 悬空 → 加 100MΩ 直流路径。

---

## 6. 栅极驱动器（39-48 行）

```spice
B1 drv 0 V=V(sw)+if(V(pwm)>6, 11.5, 0)
Rg drv gate 10       ; 驱动输出阻抗
Cg gate sw 1n        ; 栅极电容
Cgnd gate 0 1n       ; 收敛辅助
```

| 元件 | 作用 |
|------|------|
| `B1` | 模拟驱动芯片：PWM 高 → drv=sw+11.5V（Vgs=11.5V）；低 → drv=sw（Vgs=0）|
| `Rg` | 真实芯片输出阻抗（10Ω）|
| `Cg` | MOS 栅极电容（1nF）|
| `Cgnd` | gate 对地电容，**打断 sw→gate→sw 代数环**（L=100µH 时必需，否则 Singular matrix）|

---

## 7. 功率级（50-62 行）—— 标准 Buck

```spice
M1 in gate sw 0 NMOS   ; 高边 NMOS：D=in, G=gate, S=sw
D1 0 sw D              ; 续流二极管：阳极=0, 阴极=sw
Rsw sw 0 10meg         ; sw 直流路径（防悬空）
L1 sw out 100u         ; 电感 100µH
C1 out 0 100u          ; 输出电容 100µF
R1 out 0 10            ; 负载 10Ω
```

- M1：高边开关（漏极接 Vin，源极接开关节点 sw）
- D1：续流（阳极接地，阴极接 sw，导通时 sw 被钳到 -0.7V）
- L1/C1：LC 滤波；R1：负载

---

## 8. 器件模型（64-67 行）

```spice
.MODEL NMOS NMOS(VTO=2 KP=10)    ; NMOS：阈值 2V，跨导 10
.MODEL D D(IS=1e-12)             ; 普通二极管（饱和电流 1e-12）
.MODEL DCLAMP D(IS=1e-14)        ; 钳位二极管（更理想，漏电更小）
```

---

## 9. 仿真指令（69-70 行）

```spice
.tran 25ms uic
```

- 瞬态分析 **25ms**
- `uic`（Use Initial Conditions）：跳过 .op 直接瞬态，从零状态开始
  - 原因：Gint 的 0.2mA × Rdc 100MΩ = 20000V 荒谬 .op 工作点
  - 配合 `Cdctrl ic=6` 指定 dctrl 初始值

---

## 10. 测量语句（72-99 行）

```spice
.meas Vout_before AVG V(out) TRIG time=2ms TARG time=9.9ms
```

| 语法 | 含义 |
|------|------|
| `AVG V(out)` | 求 V(out) 平均值 |
| `MIN/MAX V(x)` | 求最小值/最大值 |
| `TRIG/TARG` | 只统计该时间区间 |

- `Duty_xxx AVG V(dctrl)*100/12` → **占空比百分比**（dctrl 电压 / 12V × 100）
- `Dctrl_t1~t5` → 10ms 突变后每 2ms 采样，展示**占空比爬升轨迹**
- `IL_min_after MIN I(L1)` → 判断工作模式：**>0 = CCM，≈0 = DCM**

---

## 11. 结束（101 行）

```spice
.end
```

SPICE 网表必须以 `.end` 结尾。

---

## 12. 仿真结果速查（参考）

```
duty_before: 52.7%      ← Vref=6V 稳态
duty_t1:     55.5%      ← 10ms 突变后爬升
duty_t2:     58.9%
duty_t3:     62.2%
duty_t4:     65.5%
duty_t5:     68.3%
duty_after:  68.6%      ← Vref=8V 稳态
il_min_after: 0.496A    ← >0 确认 CCM
```

---

*解析日期：2026-08-11*
