import os
import numpy as np
import matplotlib.pyplot as plt
import scipy.io
from scipy.optimize import least_squares
from numba import jit
import pandas as pd
import seaborn as sns
from math import pi

# ==========================================
# 1. 物理常数与全局配置
# ==========================================
CONST_Rg = 8.314        # 理想气体常数
CONST_Tref = 298.15     # 参考温度 (25°C)
CONST_GAMMA = 6.0       # 形状参数 gamma (用于(1-z)^6)
CONST_BETA = 35.0       # 形状参数 beta (用于exp(-35z))
CONST_Tamb = 297.15     # 环境温度 (~24°C)
CONST_MASS = 0.045      # 电池质量 (kg)
CONST_Cp_THERM = 1000.0 # 电池比热容 (J/kg*K)

# 输出结果保存目录
OUTPUT_DIR = 'NASA_LoadVoltage_Formula_Fit'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ==========================================
# 2. 固定参数配置 (手动/经验值)
# ==========================================
MANUAL_Ea = 15000.0  # [J/mol]

# 欧姆内阻 R1 基础参数
MANUAL_R1_Const = 0.045 
MANUAL_R1_Pow   = 0.012 
MANUAL_R1_Exp   = 0.010 

# 极化内阻 Rp 基础参数
MANUAL_Rp_Const = 0.035
MANUAL_Rp_Pow   = 0.015
MANUAL_Rp_Exp   = 0.060

# 打包固定参数
FIXED_RES_PARAMS = np.array([
    MANUAL_R1_Const, MANUAL_R1_Pow, MANUAL_R1_Exp,
    MANUAL_Rp_Const, MANUAL_Rp_Pow, MANUAL_Rp_Exp,
    MANUAL_Ea
])

# ==========================================
# 3. 核心数学模型 (Numba 加速)
# ==========================================

@jit(nopython=True)
def calc_ocv(z, k):
    """
    计算开路电压 OCV
    公式: OCV(z) = K0 + K1*z + K2/z + K3*ln(z) + K4*ln(1-z)
    """
    # 边界保护
    if z < 0.002: z = 0.002
    if z > 0.998: z = 0.998
    return k[0] + k[1]*z + k[2]/z + k[3]*np.log(z) + k[4]*np.log(1-z)

@jit(nopython=True)
def get_resistance_components(z, T, p_Res):
    """ 计算当前的 R1 (欧姆) 和 Rp (极化) """
    Ea = p_Res[6]
    FT = np.exp((Ea / CONST_Rg) * (1.0/T - 1.0/CONST_Tref))
    
    term_pow = (1.0 - z)**CONST_GAMMA 
    term_exp = np.exp(-CONST_BETA * z) 
    
    R1_base = p_Res[0] + p_Res[1]*term_pow + p_Res[2]*term_exp
    R1 = R1_base * FT
    
    Rp_base = p_Res[3] + p_Res[4]*term_pow + p_Res[5]*term_exp
    Rp = Rp_base * FT
    
    return R1, Rp

@jit(nopython=True)
def discrete_simulation(t, I, T_init, C_nom, params):
    """
    核心仿真函数
    逻辑：
    1. 计算 SOC
    2. 计算 OCV
    3. 计算 R1, Up
    4. 应用公式: V_load = OCV - I*R1 - Up
    """
    n_steps = len(t)
    V_load_sim = np.zeros(n_steps) 
    T_sim = np.zeros(n_steps)      
    z_sim = np.zeros(n_steps)      
    
    # 解析参数
    p_OCV = params[0:5]
    p_Res = params[5:12]
    Cp_elec = params[12]
    hA = params[13]
    
    # 初始状态
    z = 1.0       # 假设满电开始
    Up = 0.0      # 初始极化电压
    T = T_init
    
    # 记录 Step 0
    T_sim[0] = T
    z_sim[0] = z
    
    R1, Rp = get_resistance_components(z, T, p_Res)
    OCV = calc_ocv(z, p_OCV)
    # --- 公式应用 ---
    V_load_sim[0] = OCV - I[0]*R1 - Up
    
    for k in range(n_steps - 1):
        dt = t[k+1] - t[k]
        I_k = I[k]
        
        # 1. SOC 更新
        z_new = z - (I_k * dt / C_nom)
        if z_new < 0.002: z_new = 0.002
        if z_new > 1.0: z_new = 1.0
        
        R1, Rp = get_resistance_components(z, T, p_Res)
        
        # 2. 极化电压 Up 更新 (一阶 RC)
        if Cp_elec > 1e-6:
            tau = Rp * Cp_elec
            if tau > 1e-8:
                exp_f = np.exp(-dt / tau)
                Up_new = Up * exp_f + Rp * (1.0 - exp_f) * I_k
            else:
                Up_new = I_k * Rp
        else:
            Up_new = I_k * Rp
        
        # 3. 热模型更新
        Qgen = (I_k**2) * R1 + (Up**2)/Rp if Rp > 1e-6 else (I_k**2) * R1
        Qdiss = hA * (T - CONST_Tamb) 
        T_new = T + (Qgen - Qdiss) / (CONST_MASS * CONST_Cp_THERM) * dt
        
        # 更新状态
        z = z_new; Up = Up_new; T = T_new
        z_sim[k+1] = z
        T_sim[k+1] = T
        
        # 4. 计算下一步的输出
        # 获取新状态下的参数
        R1_next, Rp_next = get_resistance_components(z, T, p_Res)
        OCV_next = calc_ocv(z, p_OCV)
        
        # --- 核心公式: V_load = OCV - I*R1 - Up ---
        # 这里的 V_load_sim 即为通过 OCV 修正后的最终拟合结果
        V_load_sim[k+1] = OCV_next - I[k+1]*R1_next - Up
        
    return V_load_sim, T_sim, z_sim

# ==========================================
# 4. 优化目标函数
# ==========================================

def cost_function(params_opt, fixed_res_params, t, V_target, I_meas, T_meas, Q_actual):
    # 组装参数
    full_params = np.concatenate((params_opt[0:5], fixed_res_params, params_opt[5:7]))
    
    # 运行仿真，得到 V_load_sim
    V_sim, T_sim, _ = discrete_simulation(t, I_meas, T_meas[0], Q_actual, full_params)
    
    # 计算残差 (V_calc - V_actual_load)
    res_V = V_sim - V_target
    res_T = T_sim - T_meas
    
    # 权重分配 (温度趋势对参数辨识很重要，给予较高权重)
    W_T = 2.0 
    W_V = 1.0
    
    combined = np.concatenate((res_V * W_V, res_T * W_T))
    
    if np.any(np.isnan(combined)):
        return np.ones_like(combined) * 1e5
        
    return combined

# ==========================================
# 5. 数据读取 (强制读取 Voltage_load)
# ==========================================

def load_nasa_data(filename):
    print(f"Loading data: {filename} ...")
    try:
        data = scipy.io.loadmat(filename)
        key = [k for k in data.keys() if not k.startswith('__')][0]
        cycles = data[key][0][0]['cycle'][0]
        
        target = next((c['data'] for c in cycles if c['type'][0] == 'discharge'), None)
        if target is None: raise ValueError("No discharge data found")
        
        # 读取基础数据
        I = target['Current_measured'][0][0].flatten()
        T = target['Temperature_measured'][0][0].flatten() + 273.15 
        t = target['Time'][0][0].flatten()
        
        # --- 关键修改：获取实际负载电压 (Voltage_load) ---
        # 1. 尝试直接读取 'Voltage_load'
        if 'Voltage_load' in target.dtype.names:
            V_actual = target['Voltage_load'][0][0].flatten()
            print("  -> Success: Found 'Voltage_load' in dataset.")
            
        # 2. NASA数据中有时 'Voltage_charge' 在放电周期中代表负载电压
        elif 'Voltage_charge' in target.dtype.names:
            V_actual = target['Voltage_charge'][0][0].flatten()
            print("  -> Note: Used 'Voltage_charge' field as Load Voltage (common NASA naming issue).")
            
        # 3. 实在没有，回退到端电压 (Voltage_measured) 并警告
        else:
            V_actual = target['Voltage_measured'][0][0].flatten()
            print("  -> Warning: 'Voltage_load' not found. Fallback to 'Voltage_measured'.")
            
        # 确保电流为正
        if np.mean(I) < 0: I = np.abs(I)
        
        # 去除前3个点 (预处理)
        if len(V_actual) > 3:
            V_actual = V_actual[3:]
            I = I[3:]
            T = T[3:]
            t = t[3:]
            
        Q_cycle = np.trapz(I, t) 
        return t, V_actual, I, T, Q_cycle, key
        
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return None

# ==========================================
# 6. 绘图与报告生成
# ==========================================

def save_txt_report(batt_id, p, rmse_v, rmse_t):
    """ 生成参数 TXT 报告 """
    content = f"""
================================================================
BATTERY FITTING REPORT: {batt_id}
Fitting Logic: 
1. Identify OCV and Dynamic Params.
2. Calculate V_load = OCV - I*R1 - Up.
3. Compare with Actual Voltage_load.
================================================================

1. ERROR METRICS
----------------
   RMSE Load Voltage      : {rmse_v:.6f} V
   RMSE Temperature       : {rmse_t:.6f} C

2. FITTED PARAMETERS (Identified from Data)
-------------------------------------------
   [OCV Model (K0-K4)]
   K0 (Base)              : {p[0]:.6f}
   K1 (Linear SOC)        : {p[1]:.6f}
   K2 (1/SOC)             : {p[2]:.6f}
   K3 (ln(SOC))           : {p[3]:.6f}
   K4 (ln(1-SOC))         : {p[4]:.6f}

   [Internal Resistance] (Fixed Base + Temp Correction)
   R1 (Ohmic) Base        : {p[5]:.4f} Ohms (at Ref Temp/SOC=1)
   Rp (Polar) Base        : {p[8]:.4f} Ohms
   Ea (Activation Energy) : {p[11]:.1f} J/mol

   [Dynamic & Thermal]
   Cp (Polarization Cap)  : {p[12]:.4f} F
   hA (Heat Transfer)     : {p[13]:.4f} W/K
================================================================
"""
    file_path = os.path.join(OUTPUT_DIR, f"{batt_id}_FitReport.txt")
    with open(file_path, "w") as f:
        f.write(content)
    print(f"Report saved: {file_path}")

def plot_fit_comparison(t, V_meas, V_sim, batt_id, rmse_v):
    """ 
    对比图：
    - 实线：数据文件中的 Voltage_load
    - 虚线：公式 V_load = OCV - IR - Up 计算出的结果
    """
    plt.figure(figsize=(10, 5))
    plt.plot(t, V_meas, 'k-', linewidth=1.5, label='Actual Voltage_load (Data)', alpha=0.7)
    plt.plot(t, V_sim, 'r--', linewidth=1.5, label=f'Calculated V_load (Model) RMSE={rmse_v:.4f}')
    
    plt.xlabel('Time (s)')
    plt.ylabel('Load Voltage (V)')
    plt.title(f'Load Voltage Comparison: {batt_id}\nFormula: $V_{{load}} = OCV(z) - I \cdot R_1 - U_p$')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"{batt_id}_LoadVoltage_Compare.png"))
    plt.close()

def plot_residuals(t, V_meas, V_sim, T_meas, T_sim, batt_id):
    """ 残差图 """
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    # 电压误差
    res_V = V_sim - V_meas
    axes[0].plot(t, res_V, color='tab:blue')
    axes[0].set_ylabel('V_load Error (V)')
    axes[0].set_title(f'Residuals (Calculated vs Actual): {batt_id}')
    axes[0].grid(True)
    axes[0].axhline(0, color='black', lw=1)

    # 温度误差
    res_T = T_sim - T_meas
    axes[1].plot(t, res_T, color='tab:red')
    axes[1].set_ylabel('Temp Error (C)')
    axes[1].set_xlabel('Time (s)')
    axes[1].grid(True)
    axes[1].axhline(0, color='black', lw=1)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"{batt_id}_Residuals.png"))
    plt.close()

def plot_heatmap_error(z_sim, V_meas, V_sim, batt_id):
    """ 热力图 """
    error = np.abs(V_sim - V_meas)
    bins = np.linspace(0, 1, 11)
    labels = [f"{int(x*100)}-{int(y*100)}%" for x, y in zip(bins[:-1], bins[1:])]
    
    soc_bins = pd.cut(z_sim, bins=bins, labels=labels, include_lowest=True)
    df = pd.DataFrame({'SOC_Range': soc_bins, 'Abs_Error': error})
    agg_df = df.groupby('SOC_Range', observed=False)['Abs_Error'].mean().reset_index()
    heatmap_data = agg_df.set_index('SOC_Range').T
    
    plt.figure(figsize=(10, 3))
    sns.heatmap(heatmap_data, annot=True, fmt=".4f", cmap="Reds", cbar_kws={'label': 'Mean Abs Error (V)'})
    plt.title(f'V_load Error Heatmap vs SOC: {batt_id}')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"{batt_id}_Heatmap.png"))
    plt.close()

def plot_radar_chart(results_dict):
    """ 雷达图 """
    if not results_dict: return
    categories = ['K0 (OCV)', 'Cp (Cap)', 'hA (Therm)', 'RMSE (V)', 'RMSE (T)']
    N = len(categories)
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    # 归一化
    raw_data = {cat: [] for cat in categories}
    ids = []
    for bid, res in results_dict.items():
        ids.append(bid)
        p = res['params']
        raw_data['K0 (OCV)'].append(p[0])
        raw_data['Cp (Cap)'].append(p[12])
        raw_data['hA (Therm)'].append(p[13])
        raw_data['RMSE (V)'].append(res['rmse_v'])
        raw_data['RMSE (T)'].append(res['rmse_t'])
        
    norm_data = {}
    for cat in categories:
        vals = np.array(raw_data[cat])
        rang = np.max(vals) - np.min(vals)
        if rang == 0: norm_data[cat] = np.ones_like(vals)
        else: norm_data[cat] = (vals - np.min(vals)) / rang

    colors = ['r', 'g', 'b', 'm']
    for i, bid in enumerate(ids):
        values = [norm_data[cat][i] for cat in categories]
        values += values[:1]
        ax.plot(angles, values, linewidth=2, linestyle='solid', label=bid, color=colors[i % len(colors)])
        ax.fill(angles, values, color=colors[i % len(colors)], alpha=0.1)
        
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    plt.title("Parameter & Performance Radar (Normalized)", y=1.08)
    plt.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
    plt.savefig(os.path.join(OUTPUT_DIR, "Radar_Chart.png"))
    plt.close()

# ==========================================
# 7. 主程序
# ==========================================

def main():
    files = ['B0005.mat', 'B0006.mat', 'B0007.mat', 'B0018.mat']
    all_results = {}
    
    print(">>> Starting Formula-Based Fitting (V_load = OCV - IR - Up) <<<")
    
    for f in files:
        if not os.path.exists(f): continue
        
        # 1. 加载数据 (寻找 Voltage_load)
        data_pack = load_nasa_data(f)
        if data_pack is None: continue
        t, V_actual_load, I, T, Q_actual, batt_id = data_pack
        
        # 2. 优化初始化
        # 优化目标: 找到一组参数，使得 calculated V_load 最接近 actual Voltage_load
        x0 = [3.5, 0.5, -0.001, 0.05, -0.01, 50.0, 0.2] 
        lb = [2.0, -2.0, -1.0, -1.0, -1.0,  10.0, 0.01]
        ub = [4.5,  2.0,  1.0,  1.0,  0.5, 100.0, 10.0]
        
        print(f"[{batt_id}] Identifying OCV and Dynamics...")
        res = least_squares(
            cost_function, x0, bounds=(lb, ub), 
            args=(FIXED_RES_PARAMS, t, V_actual_load, I, T, Q_actual),
            loss='soft_l1', f_scale=0.1
        )
        
        final_params = np.concatenate((res.x[0:5], FIXED_RES_PARAMS, res.x[5:]))
        
        # 3. 最终计算: 使用公式得到 V_load_sim
        V_load_sim, T_sim, z_sim = discrete_simulation(t, I, T[0], Q_actual, final_params)
        
        # 4. 计算指标
        rmse_v = np.sqrt(np.mean((V_load_sim - V_actual_load)**2))
        rmse_t = np.sqrt(np.mean((T_sim - T)**2))
        
        all_results[batt_id] = {'params': final_params, 'rmse_v': rmse_v, 'rmse_t': rmse_t}
        print(f"    Result: RMSE_V_load={rmse_v:.5f} V, RMSE_T={rmse_t:.5f} C")
        
        # 5. 输出所有结果
        save_txt_report(batt_id, final_params, rmse_v, rmse_t)
        plot_fit_comparison(t, V_actual_load, V_load_sim, batt_id, rmse_v)
        plot_residuals(t, V_actual_load, V_load_sim, T, T_sim, batt_id)
        plot_heatmap_error(z_sim, V_actual_load, V_load_sim, batt_id)

    if all_results:
        plot_radar_chart(all_results)
        print(f"\nCompleted. All results saved in '{OUTPUT_DIR}'.")

if __name__ == "__main__":
    main()