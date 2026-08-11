# Buck 降压电路学习项目

基于 LTspice 网表（.cir）的 Buck 降压电路学习记录，涵盖电路搭建、仿真验证、输出电压偏差分析与自举驱动实现。

## 文件说明

| 文件 | 说明 |
|------|------|
| `buck.cir` | Buck 电路网表（自举驱动，DCM 模式，L=10µH） |
| `buck_ccm.cir` | 同 buck.cir，仅 L1=100µH（CCM 模式）+ Cgnd 收敛辅助 |
| `buck.asc` | LTspice 原理图 |
| `buck学习记录.md` | 完整学习笔记（含全部实验数据） |
| `diag*.cir` | 诊断实验网表（Vgs 不足、二极管压降、同步整流验证） |

## 电路拓扑

```
Vin(12V) ──┬── M1(NMOS) ── L1 ──┬── C1 ──┬── Vout
           │                    │        │
           └──── D1 ────────────┘        R1
                                        GND
```

- 输入：12V
- PWM：0/12V，5µs 高电平 / 10µs 周期（占空比 50%）
- 理论输出：`Vout = Vin × D = 6V`

## 运行仿真

需要安装 LTspice（本机路径 `D:\Program Files\ADI\LTspice\LTspice.exe`）：

```powershell
& "D:\Program Files\ADI\LTspice\LTspice.exe" -b -Run "buck.cir"
```

结果输出到 `buck.log`（测量值）和 `buck.raw`（波形）。

## 核心结论

1. **Vout = Vin×D 仅在 CCM + 理想器件下严格成立**
2. **DCM 模式输出偏高**（实测 7.83V vs 理论 6V），增大电感可进入 CCM（实测 5.72V）
3. **高边 NMOS 需要自举驱动**，否则 Vgs 不足（实测仅 2.58V）
4. **自举电路仿真收敛要点**：boot 节点加直流路径、驱动源加输出阻抗、大电感时加 Cgnd 打断代数环

详细分析见 [buck学习记录.md](buck学习记录.md)。

## 版本要求

- LTspice XVII / 24.x
- Windows
