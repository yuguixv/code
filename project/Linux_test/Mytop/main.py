# --- 导入工具 ---
import time
import psutil
# 从 rich 库里导入我们需要的小组件：动态刷新、面板、表格、控制台
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from datetime import datetime

# --- 核心逻辑区：获取数据 ---
def get_system_info():
    """
    这个函数负责当'搬运工'，从系统底层抓取数据，
    然后打包成一个字典返回。
    """
    
    # 1. 获取 CPU 使用率
    # interval=None 表示非阻塞模式，它会立刻返回上一次调用以来的平均值。
    # 如果填 1，程序会卡在这里等 1 秒来计算，会导致界面卡顿。
    cpu_usage = psutil.cpu_percent(interval=None)
    
    # 2. 获取内存信息
    memory = psutil.virtual_memory()
    # memory.total 单位是字节(Byte)，除以 1024^3 换算成 GB
    mem_total = memory.total / (1024 ** 3) 
    mem_used = memory.used / (1024 ** 3)
    
    # 3. 获取开机时间
    # psutil.boot_time() 返回的是时间戳（一串数字），
    # datetime...strftime 把它变成人类能看懂的 "年-月-日 时:分:秒"
    boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")

    # 把所有洗好的菜（数据）装盘（字典）返回
    return {
        "cpu": cpu_usage,
        "mem_total": f"{mem_total:.2f} GB", # .2f 表示保留两位小数
        "mem_used": f"{mem_used:.2f} GB",
        "mem_percent": memory.percent,
        "boot_time": boot_time
    }

# --- 视觉呈现区：画表格 ---
def generate_dashboard():
    """
    这个函数负责当'画家'，拿到数据，画出漂亮的表格。
    """
    data = get_system_info() # 先调用上面的函数拿到最新数据

    # 创建一个空表格，设定标题和颜色
    table = Table(title="MyTop System Monitor", style="cyan", header_style="bold magenta")
    
    # 定义三列：指标名、具体数值、视觉状态条
    table.add_column("指标", justify="right")
    table.add_column("数值", justify="left")
    table.add_column("状态", justify="center")

    # --- 填充第一行：CPU ---
    # 逻辑：如果 CPU 占用小于 50% 是绿色，否则是红色（警报）
    cpu_color = "[green]" if data['cpu'] < 50 else "[red]"
    # 技巧：'█' * n 利用了字符串乘法，模拟进度条效果
    table.add_row(
        "CPU Usage", 
        f"{data['cpu']}%", 
        f"{cpu_color}{'█' * int(data['cpu'] // 5)}" 
    )

    # --- 填充第二行：内存 ---
    mem_color = "[green]" if data['mem_percent'] < 80 else "[red]"
    table.add_row(
        "Memory", 
        f"{data['mem_used']} / {data['mem_total']}", 
        f"{mem_color}{'█' * int(data['mem_percent'] // 5)}"
    )

    # --- 填充第三行：开机时间 ---
    table.add_row("Boot Time", data['boot_time'], "✅")

    # 最后用 Panel (面板) 把表格包起来，加个蓝边框，显得专业
    return Panel(table, title="[bold yellow]Linux Dashboard", border_style="blue")

# --- 程序入口 ---
if __name__ == "__main__":
    console = Console()
    console.print("[bold green]正在启动监控...[/bold green]")
    time.sleep(1) # 假装在加载，增加仪式感

    try:
        # Live 是核心魔法：它会在屏幕同一位置不断重绘，而不是一直打印新行。
        # refresh_per_second=1：每秒刷新一次
        with Live(generate_dashboard(), refresh_per_second=1) as live:
            while True:
                # 死循环：只要不按 Ctrl+C，就一直跑
                # 每次循环都重新调用 generate_dashboard 获取新数据并重绘
                live.update(generate_dashboard())
                time.sleep(1) # 休息1秒，防止脚本自己把 CPU 跑满
    except KeyboardInterrupt:
        # 捕捉用户按下的 Ctrl+C 中断信号，优雅退出，不报错
        console.print("\n[bold red]监控已停止！[/bold red]")