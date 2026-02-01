import os
import numpy as np
import matplotlib.pyplot as plt
import scipy.io
import pandas as pd
import seaborn as sns
import re
from numba import jit

# ==========================================
# 1. 全局配置
# ==========================================
CONST_Rg = 8.314
CONST_Tref = 298.15
CONST_GAMMA = 6.0
CONST_BETA = 35.0
CONST_Tamb = 297.15
CONST_MASS = 0.045
CONST_Cp_THERM = 1000.0

OUTPUT_DIR = 'Test_Result_B0005'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ==========================================
# 2. 参数读取器
# ==========================================
def parse_average_params(filepath):
    print(f"Reading Average Params from: {filepath}")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    params = np.zeros(14)
    def extract(key_pattern):
        # 匹配 Key ... : Value
        pattern = key_pattern + r'[^:]*:\s*([-+]?[\d\.]+(?:[eE][-+]?\d+)?)'
        m = re.search(pattern, content, re.IGNORECASE)
        return float(m.group(1)) if m else 0.0

    params[0] = extract('K0')
    params[1] = extract('K1')
    params[2] = extract('K2')
    params[3] = extract('K3')
    params[4] = extract('K4')

    params[5] = extract(r'R1.*Base')
    params[6] = extract(r'R1.*Pow')
    params[7] = extract(r'R1.*Exp')

    params[8] = extract(r'Rp.*Base')
    params[9] = extract(r'Rp.*Pow')
    params[10] = extract(r'Rp.*Exp')

    params[11] = extract('Ea')
    params[12] = extract('Cp')
    params[13] = extract('hA')
    
    return params

# ==========================================
# 3. 核心仿真
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
    V_sim = np.zeros(n_steps)
    T_sim = np.zeros(n_steps)
    z_sim = np.zeros(n_steps)
    
    p_OCV = params[0:5]
    p_Res = params[5:12]
    Cp_elec = params[12]
    hA = params[13]
    
    z = 1.0; Up = 0.0; T = T_init
    T_sim[0] = T; z_sim[0] = z
    
    # Initial
    R1, Rp = get_resistance_components(z, T, p_Res)
    V_sim[0] = calc_ocv(z, p_OCV) - I[0]*R1 - Up
    
    for k in range(n_steps - 1):
        dt = t[k+1] - t[k]
        if dt <= 0: dt = 0.1
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
        
        # V_load Calc
        R1_next, Rp_next = get_resistance_components(z, T, p_Res)
        V_sim[k+1] = calc_ocv(z, p_OCV) - I[k+1]*R1_next - Up
        
    return V_sim, T_sim, z_sim

# ==========================================
# 4. 数据加载 (Target: B0005 Voltage_load)
# ==========================================
def load_test_data(filename):
    print(f"Loading Test Data: {filename} ...")
    try:
        data = scipy.io.loadmat(filename)
        key = [k for k in data.keys() if not k.startswith('__')][0]
        cycles = data[key][0][0]['cycle'][0]
        target = next((c['data'] for c in cycles if c['type'][0] == 'discharge'), None)
        if target is None: raise ValueError("No discharge data")
        
        # 核心：Load Voltage
        if 'Voltage_load' in target.dtype.names:
            V = target['Voltage_load'][0][0].flatten()
            print("  -> Found 'Voltage_load'")
        elif 'Voltage_charge' in target.dtype.names:
            V = target['Voltage_charge'][0][0].flatten()
            print("  -> Found 'Voltage_charge' (Used as Load Voltage)")
        else:
            print("  -> Warning: Using 'Voltage_measured'")
            V = target['Voltage_measured'][0][0].flatten()
            
        I = target['Current_measured'][0][0].flatten()
        T = target['Temperature_measured'][0][0].flatten() + 273.15
        t = target['Time'][0][0].flatten()
        
        if np.mean(I) < 0: I = np.abs(I)
        if len(V) > 3:
            V = V[3:]; I = I[3:]; T = T[3:]; t = t[3:]
            
        Q_cycle = np.trapz(I, t)
        return t, V, I, T, Q_cycle, key
    except Exception as e:
        print(f"Error: {e}")
        return None

# ==========================================
# 5. 绘图函数
# ==========================================
def plot_results(t, V_meas, V_sim, T_meas, T_sim, z_sim, batt_id, rmse_v, rmse_t):
    # 1. 对比图
    plt.figure(figsize=(10, 5))
    plt.plot(t, V_meas, 'k-', lw=1.5, label='Actual V_load')
    plt.plot(t, V_sim, 'r--', lw=1.5, label=f'Predicted V_load (RMSE={rmse_v:.4f})')
    plt.title(f'B0005 Test Result (Using Avg Params of 6,7,18)')
    plt.ylabel('Load Voltage (V)'); plt.xlabel('Time (s)')
    plt.legend(); plt.grid(True, alpha=0.5)
    plt.savefig(os.path.join(OUTPUT_DIR, f"{batt_id}_Comparison.png"))
    plt.close()
    
    # 2. 残差图
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    res_V = V_sim - V_meas
    axes[0].plot(t, res_V, 'b')
    axes[0].set_ylabel('V Error (V)'); axes[0].grid(True)
    axes[0].set_title(f'Residuals: {batt_id}')
    
    res_T = T_sim - T_meas
    axes[1].plot(t, res_T, 'r')
    axes[1].set_ylabel('T Error (C)'); axes[1].grid(True)
    axes[1].set_xlabel('Time (s)')
    plt.savefig(os.path.join(OUTPUT_DIR, f"{batt_id}_Residuals.png"))
    plt.close()
    
    # 3. 热力图
    error = np.abs(res_V)
    bins = np.linspace(0, 1, 11)
    labels = [f"{int(x*100)}-{int(y*100)}%" for x, y in zip(bins[:-1], bins[1:])]
    soc_bins = pd.cut(z_sim, bins=bins, labels=labels, include_lowest=True)
    df = pd.DataFrame({'SOC': soc_bins, 'Err': error})
    agg = df.groupby('SOC', observed=False)['Err'].mean().reset_index()
    heatmap_data = agg.set_index('SOC').T
    
    plt.figure(figsize=(10, 3))
    sns.heatmap(heatmap_data, annot=True, fmt=".4f", cmap="Reds")
    plt.title(f'Error Heatmap vs SOC: {batt_id}')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"{batt_id}_Heatmap.png"))
    plt.close()

# ==========================================
# 6. 主程序
# ==========================================
def main():
    # 参数文件路径 (指向代码1生成的均值文件)
    AVG_PARAM_FILE = './Training_Results_Avg/Average_Model_Params.txt'
    TEST_FILE = 'B0005.mat'
    
    print(">>> Starting Test on B0005 using Average Parameters <<<")
    
    # 1. 读取均值参数
    try:
        params = parse_average_params(AVG_PARAM_FILE)
        print("Average Parameters Loaded.")
    except Exception as e:
        print(f"[Error] {e}")
        return
        
    # 2. 读取 B0005 数据
    if not os.path.exists(TEST_FILE):
        print(f"B0005.mat not found!")
        return
        
    data = load_test_data(TEST_FILE)
    if data is None: return
    t, V_meas, I, T, Q_actual, batt_id = data
    
    # 3. 预测
    print(f"Running simulation on {batt_id}...")
    V_sim, T_sim, z_sim = discrete_simulation(t, I, T[0], Q_actual, params)
    
    # 4. 评估
    rmse_v = np.sqrt(np.mean((V_sim - V_meas)**2))
    rmse_t = np.sqrt(np.mean((T_sim - T)**2))
    print(f"Test Result: RMSE_V={rmse_v:.5f} V, RMSE_T={rmse_t:.5f} C")
    
    # 5. 绘图
    plot_results(t, V_meas, V_sim, T, T_sim, z_sim, batt_id, rmse_v, rmse_t)
    print(f"Results saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()