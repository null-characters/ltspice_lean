/*
 * buck_hysteresis.c
 * 滞环控制 Buck —— 标准 C 语言实现（与 MATLAB 版相同的离散模型）
 *
 * 移植链：SPICE (buck_hysteresis.cir) -> MATLAB -> C
 * 与 MATLAB 脚本保持逐行对应：
 *   - 功率级：前向欧拉（iL, vout 状态）
 *   - 控制器：50kHz 周期采样 + 滞环积分（dctrl += 4mV）
 *   - PWM：理想锯齿波比较
 *
 * 编译：gcc -O2 -o buck_hysteresis.exe buck_hysteresis.c -lm
 * 运行：buck_hysteresis.exe
 */

#include <stdio.h>
#include <math.h>

/* ---------- 电路参数（与 SPICE/MATLAB 一致） ---------- */
#define VIN    12.0f
#define L      100e-6f
#define C      100e-6f
#define R      10.0f
#define VD     0.7f        /* 二极管压降 */
#define FSW    50e3f       /* 开关频率 */
#define TSW    (1.0f/FSW)  /* 20us */
#define KT     0.2e-3f     /* Gint 满幅电流 0.2mA */
#define CCAP   1e-6f       /* Cdctrl 积分电容 */
#define DSTEP  (KT*TSW/CCAP)  /* 每周期 dctrl 步进 4mV */

/* ---------- 仿真设置 ---------- */
#define DT     0.2e-6f     /* 功率级步长 */
#define TEND   25e-3f      /* 仿真时长 */
#define NSTEP  ((int)(TEND/DT))
#define NREC   10          /* 每 10 步记录一次（2us） */

static float clampf(float x, float lo, float hi)
{
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

int main(void)
{
    FILE *fp;
    float iL = 0.0f, vout = 0.0f, dctrl = 6.0f; /* 状态变量 */
    int k, n;

    /* 统计累积量 */
    long cnt = 0;
    double vout_sum = 0.0, dctrl_sum = 0.0;

    fp = fopen("c_result.csv", "w");
    if (!fp) { perror("fopen"); return 1; }
    fprintf(fp, "t,vout,dctrl\n");

    for (k = 1; k <= NSTEP; k++) {
        float t  = (k-1) * DT;
        float tri, vsw, diL, dvC, vref;

        /* 锯齿波载波（理想锯齿 0~12V） */
        tri = 12.0f * fmodf(t, TSW) / TSW;

        /* PWM 比较器 */
        int pwm_on = (tri < dctrl);

        /* 功率级（前向欧拉） */
        vsw = pwm_on ? VIN : -VD;
        diL = (vsw - vout) / L;
        iL  += DT * diL;
        if (iL < 0.0f) iL = 0.0f;          /* DCM 保护 */
        dvC = (iL - vout/R) / C;
        vout += DT * dvC;

        /* 控制器：每开关周期采样一次 */
        if (fmodf(t + DT, TSW) < DT || k == NSTEP) {
            /* Vref 斜坡：10ms 处 0.1ms 内 6V->8V */
            vref = 6.0f + 2.0f * clampf((t-10e-3f)/0.1e-3f, 0.0f, 1.0f);

            /* 滞环积分器：窗口 ±0.1V */
            if (vout < vref - 0.1f)
                dctrl += DSTEP;
            else if (vout > vref + 0.1f)
                dctrl -= DSTEP;

            /* 钳位 0~12V */
            dctrl = clampf(dctrl, 0.0f, 12.0f);
        }

        /* 记录 + 稳态统计（18~25ms） */
        if (k % NREC == 0) {
            fprintf(fp, "%.6f,%.6f,%.6f\n", t, vout, dctrl);
            if (t >= 18e-3f && t <= 25e-3f) {
                vout_sum  += vout;
                dctrl_sum += dctrl;
                cnt++;
            }
        }
    }
    fclose(fp);

    if (cnt > 0) {
        float vout_avg  = (float)(vout_sum/cnt);
        float dctrl_avg = (float)(dctrl_sum/cnt);
        printf("=== C 语言离散化仿真结果 ===\n");
        printf("Vout_avg (18-25ms) : %.4f V   (SPICE: 7.94V, MATLAB: 8.007V)\n", vout_avg);
        printf("Dctrl_avg (18-25ms): %.4f V   (SPICE: 8.23V,  MATLAB: 8.16V)\n", dctrl_avg);
        printf("Duty (%%):           %.2f %%   (SPICE: 68.6%%,  MATLAB: 67.98%%)\n", dctrl_avg/12.0f*100.0f);
        printf("IL_avg:             %.4f A   (SPICE: 0.798A, MATLAB: 0.801A)\n", vout_avg/R);
    }
    printf("数据已写入 c_result.csv\n");
    return 0;
}
