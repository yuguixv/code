from lab1_base import *
import matplotlib.pyplot as plt
import os

#保存图片
output_dir = "experiment_results"
os.makedirs(output_dir, exist_ok=True)

epochs = 1000

#1.网络深度的影响
print("1.网络深度的影响")

#lr=0.001，ReLU
depth_configs = {
    "Shallow (1 layer)": [64],
    "Medium (2 layers)": [64, 32],
    "Deep (3 layers)": [64, 32, 16]
}
depth_results = {}

for name, dims in depth_configs.items():
    print(f"\n当前网络结构: {name}")

    model = FNN(hidden_dims=dims, activation=nn.ReLU())
    best_model, t_loss, v_loss = train_model(model, train_loader, val_loader, lr=0.001, epochs=epochs)
    test_l = test_model(best_model, test_loader)
    depth_results[name] = {'train': t_loss, 'val': v_loss, 'test': test_l}

# 绘图
plot_losses("Experiment 1: Network Depth", depth_results, save_filename="exp1_depth_curve", output_dir=output_dir)
plot_test_comparison("Experiment 1: Network Depth", depth_results, save_filename="exp1_depth_bar", output_dir=output_dir)



#2.学习率的影响
print("\n")
print("2.学习率的影响")

#两层隐藏层，ReLU
lrs = [0.1, 0.01, 0.001, 0.0001]
lr_results = {}

for lr in lrs:
    print(f"\n当前学习率: LR = {lr}")

    model = FNN(hidden_dims=[64, 32], activation=nn.ReLU())
    best_model, t_loss, v_loss = train_model(model, train_loader, val_loader, lr=lr, epochs=epochs)
    test_l = test_model(best_model, test_loader)
    lr_results[f"LR={lr}"] = {'train': t_loss, 'val': v_loss, 'test': test_l}

# 绘图
plot_losses("Experiment 2: Learning Rate", lr_results, save_filename="exp2_lr_curve", output_dir=output_dir)
plot_test_comparison("Experiment 2: Learning Rate", lr_results, save_filename="exp2_lr_bar", output_dir=output_dir)



#3.激活函数的影响
print("\n")
print("3.激活函数的影响")

#2层隐藏层，lr=0.001
activations = {
    "Sigmoid": nn.Sigmoid(),
    "Tanh": nn.Tanh(),
    "ReLU": nn.ReLU(),
    "LeakyReLU": nn.LeakyReLU(),
    "Swish": nn.SiLU() 
}
act_results = {}

for name, act in activations.items():
    print(f"\n当前激活函数: {name}")

    model = FNN(hidden_dims=[64, 32], activation=act)
    best_model, t_loss, v_loss = train_model(model, train_loader, val_loader, lr=0.001, epochs=epochs)
    test_l = test_model(best_model, test_loader)
    act_results[name] = {'train': t_loss, 'val': v_loss, 'test': test_l}

# 绘图
plot_losses("Experiment 3: Activation Function", act_results, save_filename="exp3_act_curve", output_dir=output_dir)
plot_test_comparison("Experiment 3: Activation Function", act_results, save_filename="exp3_act_bar", output_dir=output_dir)