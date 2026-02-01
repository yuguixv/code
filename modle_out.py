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
CONST_Rg = 8.314        
CONST_Tref = 298.15     
CONST_GAMMA = 6.0       
CONST_BETA = 35.0       
CONST_Tamb = 297.15     
CONST_MASS = 0.045      
CONST_Cp_THERM = 1000.0 

OUTPUT_DIR = 'Training_Results_Avg'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ==========================================
# 2. 固定参数 (R_base 由拟合决定，这里只放 Ea)
# ==========================================
MANUAL_Ea = 15000.0  

# 基础电阻参数结构初始值 (仅用于占位，实际会优化)
FIXED_RES_PARAMS = np.array([
    0.045, 0.012, 0.010,  # R1 Base, Pow, Exp
    0.035, 0.015, 0.060,  # Rp Base, Pow, Exp
    MANUAL_Ea
])

# ==========================================
# 3. 核心数学模型 (Numba)
# ==========================================
@jit(nopython=True)
def calc_ocv(z, k):
    if z < 0.002: z = 0.002
    if z > 0.998: z = 0.998
    return k[0] + k[1]*z + k[2]/z + k[3]*np.log(z) + k[4]*np.log(1-z)

@jit(nopython=True)
def get_resistance_components(z, T, p_Res):
    Ea = p_Res[6]
    FT = np.exp((Ea / CONST_Rg) * (1.0/T - 1.0/CONST_Tref))
    
    term_pow = (1.0 - z)**CONST_GAMMA 
    term_exp = np.exp(-CONST_BETA * z) 
    
    R1 = (p_Res[0] + p_Res[1]*term_pow + p_Res[2]*term_exp) * FT
    Rp = (p_Res[3] + p_Res[4]*term_pow + p_Res[5]*term_exp) * FT
    return R1, Rp

@jit(nopython=True)
def discrete_simulation(t, I, T_init, C_nom, params):
    n_steps = len(t)
    V_load_sim = np.zeros(n_steps)
    T_sim = np.zeros(n_steps)
    z_sim = np.zeros(n_steps)
    
    p_OCV = params[0:5]
    p_Res = params[5:12]
    Cp_elec = params[12]
    hA = params[13]
    
    z = 1.0; Up = 0.0; T = T_init
    T_sim[0] = T; z_sim[0] = z
    
    R1, Rp = get_resistance_components(z, T, p_Res)
    V_load_sim[0] = calc_ocv(z, p_OCV) - I[0]*R1 - Up
    
    for k in range(n_steps - 1):
        dt = t[k+1] - t[k]
        I_k = I[k]
        
        # SOC
        z_new = z - (I_k * dt / C_nom)
        if z_new < 0.002: z_new = 0.002
        if z_new > 1.0: z_new = 1.0
        
        R1, Rp = get_resistance_components(z, T, p_Res)
        
        # Up (RC)
        if Cp_elec > 1e-6:
            tau = Rp * Cp_elec
            if tau > 1e-8:
                exp_f = np.exp(-dt / tau)
                Up_new = Up * exp_f + Rp * (1.0 - exp_f) * I_k
            else:
                Up_new = I_k * Rp
        else:
            Up_new = I_k * Rp
        
        # Thermal
        Qgen = (I_k**2) * R1 + (Up**2)/Rp if Rp > 1e-6 else (I_k**2) * R1
        Qdiss = hA * (T - CONST_Tamb) 
        T_new = T + (Qgen - Qdiss) / (CONST_MASS * CONST_Cp_THERM) * dt
        
        # Update
        z = z_new; Up = Up_new; T = T_new
        z_sim[k+1] = z; T_sim[k+1] = T
        
        # Voltage Calculation (V_load)
        R1_next, Rp_next = get_resistance_components(z, T, p_Res)
        V_load_sim[k+1] = calc_ocv(z, p_OCV) - I[k+1]*R1_next - Up
        
    return V_load_sim, T_sim, z_sim

# ==========================================
# 4. 优化目标函数
# ==========================================
def cost_function(params_opt, fixed_res_params, t, V_target, I_meas, T_meas, Q_actual):
    # params_opt: [K0..K4, Cp, hA]
    # 注意：这里我们简化优化，假设电阻参数使用固定基准+微调，或者为了简单起见，
    # 我们只优化 K0-K4, Cp, hA, 而电阻参数固定（或者您可以将电阻参数也放入优化列表）。
    # 为了保持代码与之前一致且稳定，这里我们依然把 FIXED_RES_PARAMS 传进去，
    # 但如果想求均值，最好是电阻参数也一样。
    # 这里我们只优化 OCV 和 动态参数。
    
    full_params = np.concatenate((params_opt[0:5], fixed_res_params, params_opt[5:7]))
    V_sim, T_sim, _ = discrete_simulation(t, I_meas, T_meas[0], Q_actual, full_params)
    
    res_V = V_sim - V_target
    res_T = T_sim - T_meas
    
    combined = np.concatenate((res_V * 1.0, res_T * 2.0))
    if np.any(np.isnan(combined)): return np.ones_like(combined) * 1e5
    return combined

# ==========================================
# 5. 数据读取 (强制 Voltage_load)
# ==========================================
def load_nasa_data(filename):
    print(f"Loading training data: {filename} ...")
    try:
        data = scipy.io.loadmat(filename)
        key = [k for k in data.keys() if not k.startswith('__')][0]
        cycles = data[key][0][0]['cycle'][0]
        target = next((c['data'] for c in cycles if c['type'][0] == 'discharge'), None)
        if target is None: raise ValueError("No discharge data found")
        
        I = target['Current_measured'][0][0].flatten()
        T = target['Temperature_measured'][0][0].flatten() + 273.15 
        t = target['Time'][0][0].flatten()
        
        # 优先读取 Load Voltage
        if 'Voltage_load' in target.dtype.names:
            V_load = target['Voltage_load'][0][0].flatten()
        elif 'Voltage_charge' in target.dtype.names:
            V_load = target['Voltage_charge'][0][0].flatten()
        else:
            V_load = target['Voltage_measured'][0][0].flatten()
            
        if np.mean(I) < 0: I = np.abs(I)
        
        if len(V_load) > 3:
            V_load = V_load[3:]; I = I[3:]; T = T[3:]; t = t[3:]
            
        Q_cycle = np.trapz(I, t) 
        return t, V_load, I, T, Q_cycle, key
    except Exception as e:
        print(f"Err {filename}: {e}")
        return None

# ==========================================
# 6. 保存均值参数
# ==========================================
def save_average_report(params_mean, count):
    p = params_mean
    content = f"""
================================================================
AVERAGE PARAMETER REPORT
Generated from {count} Datasets (B0006, B0007, B0018)
Target: Load Voltage
================================================================

[OCV Parameters]
K0 (Base)              : {p[0]:.6f}
K1 (Linear)            : {p[1]:.6f}
K2 (1/z)               : {p[2]:.6f}
K3 (ln(z))             : {p[3]:.6f}
K4 (ln(1-z))           : {p[4]:.6f}

[Internal Resistance]
R1 (Ohmic) Base        : {p[5]:.6f}
R1 Pow                 : {p[6]:.6f}
R1 Exp                 : {p[7]:.6f}

Rp (Polar) Base        : {p[8]:.6f}
Rp Pow                 : {p[9]:.6f}
Rp Exp                 : {p[10]:.6f}

Ea (Activation)        : {p[11]:.1f}

[Dynamic & Thermal]
Cp (Polarization Cap)  : {p[12]:.4f}
hA (Heat Transfer)     : {p[13]:.4f}
================================================================
"""
    file_path = os.path.join(OUTPUT_DIR, "Average_Model_Params.txt")
    with open(file_path, "w") as f:
        f.write(content)
    print(f"Average parameters saved to: {file_path}")

# ==========================================
# 7. 主程序
# ==========================================
def main():
    # 训练集文件 (B0018, B0006, B0007)
    TRAIN_FILES = ['B0018.mat', 'B0006.mat', 'B0007.mat']
    all_params_list = []
    
    print(">>> Starting Training on [B0018, B0006, B0007] <<<")
    
    for f in TRAIN_FILES:
        if not os.path.exists(f): continue
        
        data_pack = load_nasa_data(f)
        if data_pack is None: continue
        t, V_load, I, T, Q_actual, batt_id = data_pack
        
        # 优化 K0-K4, Cp, hA (保持电阻参数为经验值，或您可以选择开启全部优化)
        # 这里为了演示，我们只优化 7 个参数，电阻参数使用固定值
        # 这样均值更有意义
        x0 = [3.5, 0.5, -0.001, 0.05, -0.01, 50.0, 0.2] 
        lb = [2.0, -2.0, -1.0, -1.0, -1.0,  10.0, 0.01]
        ub = [4.5,  2.0,  1.0,  1.0,  0.5, 100.0, 10.0]
        
        print(f"[{batt_id}] Fitting...")
        res = least_squares(
            cost_function, x0, bounds=(lb, ub), 
            args=(FIXED_RES_PARAMS, t, V_load, I, T, Q_actual),
            loss='soft_l1', f_scale=0.1
        )
        
        # 组装完整参数 (14个)
        full_p = np.concatenate((res.x[0:5], FIXED_RES_PARAMS, res.x[5:]))
        all_params_list.append(full_p)
        
        # 简单的验证输出
        V_sim, _, _ = discrete_simulation(t, I, T[0], Q_actual, full_p)
        rmse = np.sqrt(np.mean((V_sim - V_load)**2))
        print(f"    -> RMSE: {rmse:.4f} V")

    # 计算均值并保存
    if all_params_list:
        avg_params = np.mean(np.array(all_params_list), axis=0)
        save_average_report(avg_params, len(all_params_list))
        print("Training Complete.")
    else:
        print("No data processed.")

if __name__ == "__main__":
    main()