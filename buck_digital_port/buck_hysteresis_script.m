%% buck_hysteresis_script.m
% 将 SPICE 版滞环控制器（buck_hysteresis.cir）离散化为 MATLAB 脚本仿真
% 功率级：前向欧拉离散；控制器：50kHz 周期采样 + 滞环积分
% 对应关系：
%   Gint 连续电流 ±0.2mA  -> 每周期 duty_cmd += 4mV（0.2m*Tsw/C）
%   Cdctrl 1uF 积分电容    -> duty_cmd 状态变量（离散积分）
%   Bpwm 比较器           -> pwm = (tri < duty_cmd)
%   Bref 斜坡             -> vref = 6+2*clamp((t-10m)/0.1m,0,1)

clear; clc; close all;

%% 电路参数（与 buck_hysteresis.cir 一致）
Vin  = 12;          % 输入电压
L    = 100e-6;      % 电感
C    = 100e-6;      % 输出电容
R    = 10;          % 负载
Vd   = 0.7;         % 二极管正向压降（D 模型近似）
fsw  = 50e3;        % 开关频率
Tsw  = 1/fsw;       % 开关周期 20us
kT   = 0.2e-3;      % Gint 满幅电流（0.2mA）
Ccap = 1e-6;        % Cdctrl 积分电容
dstep = kT*Tsw/Ccap; % 每周期 dctrl 步进 = 0.2m*20u/1u = 4mV

%% 仿真设置
dt     = 0.2e-6;    % 功率级步长（PWM 周期内 100 步）
Tend   = 25e-3;     % 仿真时长
nstep  = round(Tend/dt);
nrec   = 10;        % 每 nrec 步记录一次（每 2us）

%% 状态初始化
iL    = 0;          % 电感电流
vout  = 0;          % 输出电压
dctrl = 6;          % 占空比指令初值 ic=6（50%）

%% 数据记录
t_rec  = zeros(0,1); vout_rec = zeros(0,1); dctrl_rec = zeros(0,1);

%% 主循环
for k = 1:nstep
    t = (k-1)*dt;

    % --- 锯齿波载波（理想锯齿 0~12V，周期 Tsw）---
    tri = 12 * mod(t, Tsw) / Tsw;

    % --- PWM 比较器（Bpwm）---
    pwm_on = tri < dctrl;

    % --- 功率级（前向欧拉）---
    vsw = pwm_on * Vin + (~pwm_on)*(-Vd);     % 开关节点电压（续流钳位 -Vd）
    diL = (vsw - vout) / L;
    iL  = iL + dt * diL;
    if iL < 0, iL = 0; end                    % DCM 保护（电感电流不反向）
    dvC = (iL - vout/R) / C;
    vout = vout + dt * dvC;

    % --- 控制器：每开关周期采样一次（50kHz）---
    if mod(t + dt, Tsw) < dt || k == nstep
        % Vref 斜坡（Bref）：10ms 处 0.1ms 内 6V->8V
        vref = 6 + 2 * min(max((t-10e-3)/0.1e-3, 0), 1);
        % 滞环积分器（Gint）：窗口 ±0.1V
        if vout < vref - 0.1
            dctrl = dctrl + dstep;            % 充电：占空比增
        elseif vout > vref + 0.1
            dctrl = dctrl - dstep;            % 放电：占空比减
        end
        % 钳位 0~12V（Dclamp）
        dctrl = min(max(dctrl, 0), 12);
    end

    % --- 记录 ---
    if mod(k, nrec) == 0
        t_rec(end+1,1)     = t;
        vout_rec(end+1,1)  = vout;
        dctrl_rec(end+1,1) = dctrl;
    end
end

%% 结果统计（稳态 18~25ms，对比 SPICE）
idx = t_rec >= 18e-3 & t_rec <= 25e-3;
vout_avg  = mean(vout_rec(idx));
dctrl_avg = mean(dctrl_rec(idx));
duty_avg  = dctrl_avg / 12 * 100;
il_avg    = vout_avg / R;

fprintf('=== MATLAB 离散化仿真结果 ===\n');
fprintf('Vout_avg (18-25ms) : %.4f V   (SPICE: 7.94V)\n', vout_avg);
fprintf('Dctrl_avg (18-25ms): %.4f V   (SPICE: 8.23V)\n', dctrl_avg);
fprintf('Duty (%%):           %.2f %%   (SPICE: 68.6%%)\n', duty_avg);
fprintf('IL_avg:             %.4f A   (SPICE: 0.798A)\n', il_avg);

%% 画图
fig = figure('Position',[100 100 1000 700]);
subplot(2,1,1);
plot(t_rec*1e3, vout_rec, 'b-', 'LineWidth', 0.8); hold on;
vref_rec = 6 + 2*min(max((t_rec-10e-3)/0.1e-3,0),1);
plot(t_rec*1e3, vref_rec, 'r--', 'LineWidth', 1.2);
xlabel('t (ms)'); ylabel('Vout (V)'); grid on;
legend('Vout','Vref','Location','southeast');
title('Buck 滞环闭环（MATLAB 离散化）：Vout');
ylim([0 10]);

subplot(2,1,2);
plot(t_rec*1e3, dctrl_rec/12*100, 'g-', 'LineWidth', 0.8);
xlabel('t (ms)'); ylabel('Duty (%)'); grid on;
title('占空比指令（dctrl/12*100）');
ylim([40 80]);
saveas(fig, 'matlab_result.png');
fprintf('\n图已保存: matlab_result.png\n');
