from sklearn.datasets import load_diabetes
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import torch.optim as optim
import pandas as pd
import matplotlib.pyplot as plt
import copy
import os

# 加载糖尿病数据集
diabetes = load_diabetes()
X, y = diabetes.data, diabetes.target

# 划分数据集为训练集、验证集和测试集
X_temp, X_test, y_temp, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.2, random_state=42)

#转换为 PyTorch Tensor 并修改数据类型为 float32
X_train_t = torch.tensor(X_train, dtype=torch.float32)
y_train_t = torch.tensor(y_train, dtype=torch.float32).view(-1, 1) # 转换为列向量
X_val_t = torch.tensor(X_val, dtype=torch.float32)
y_val_t = torch.tensor(y_val, dtype=torch.float32).view(-1, 1)
X_test_t = torch.tensor(X_test, dtype=torch.float32)
y_test_t = torch.tensor(y_test, dtype=torch.float32).view(-1, 1)


#创建Dataset、DataLoader (batch大小设置为 16)
batch_size = 16
train_dataset = TensorDataset(X_train_t, y_train_t)
val_dataset = TensorDataset(X_val_t, y_val_t)
test_dataset = TensorDataset(X_test_t, y_test_t)

train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

print(f"训练集样本数: {len(X_train)}, 验证集样本数: {len(X_val)}, 测试集样本数: {len(X_test)}")

class FNN(nn.Module):
    def __init__(self, input_dim = 10, hidden_dims = [64, 32], output_dim = 1, activation = nn.ReLU()):
        super(FNN, self).__init__()
        layers = []
        prev_dim = input_dim
        
        # 动态构建隐藏层
        for h_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, h_dim))
            layers.append(activation)
            prev_dim = h_dim
            
        # 输出层
        layers.append(nn.Linear(prev_dim, output_dim))
        
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)
    
#训练模型
def train_model(model, train_loader, val_loader, lr=0.001, epochs=100):
    # 损失函数: 均方误差（MSE）
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    train_losses = []
    val_losses = []
    best_val_loss = float('inf')
    best_model_weights = None
    
    for epoch in range(epochs):
        #训练阶段
        model.train()
        epoch_train_loss = 0.0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            epoch_train_loss += loss.item() * batch_X.size(0)
            
        epoch_train_loss /= len(train_loader.dataset)
        train_losses.append(epoch_train_loss)
        
        #验证阶段
        model.eval()
        epoch_val_loss = 0.0
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                epoch_val_loss += loss.item() * batch_X.size(0)
                
        epoch_val_loss /= len(val_loader.dataset)
        val_losses.append(epoch_val_loss)
        
        # 记录并保存最佳模型参数
        if epoch_val_loss < best_val_loss:
            best_val_loss = epoch_val_loss
            best_model_weights = copy.deepcopy(model.state_dict())
            
        # 打印日志
        if (epoch + 1) % 20 == 0:
            print(f"Epoch [{epoch+1}/{epochs}], Train Loss: {epoch_train_loss:.4f}, Val Loss: {epoch_val_loss:.4f}")
            
    # 训练结束后，将最好的权重加载回模型
    if best_model_weights is not None:
        model.load_state_dict(best_model_weights)
        
    return model, train_losses, val_losses

#测试模型
def test_model(model, test_loader):
    # 损失函数: 均方误差（MSE）
    criterion = nn.MSELoss()
    model.eval()
    test_loss = 0.0
    
    with torch.no_grad():
        for batch_X, batch_y in test_loader:
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            test_loss += loss.item() * batch_X.size(0)
            
    test_loss /= len(test_loader.dataset)
    print(f"最终 Test Loss: {test_loss:.4f}")
    
    return test_loss

#损失曲线图
def plot_losses(experiment_name, results_dict, save_filename, output_dir):
    plt.figure(figsize=(10, 6))
    for label, losses in results_dict.items():
        plt.plot(losses['train'], label=f"{label} (Train)", linestyle='-')
        plt.plot(losses['val'], label=f"{label} (Val)", linestyle='--')
        
    plt.title(f"{experiment_name} Loss Curve")
    plt.xlabel("Epochs")
    plt.ylabel("MSE Loss")
    plt.legend()
    plt.grid(True)
    
    # 保存图片
    save_path = os.path.join(output_dir, f"{save_filename}.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"已保存曲线图至: {save_path}")


#对比柱状图
def plot_test_comparison(experiment_name, results_dict, save_filename, output_dir):
    labels = list(results_dict.keys())
    test_losses = [results_dict[label]['test'] for label in labels]
    
    plt.figure(figsize=(8, 5))
    colors = ['blue', 'orange', 'green', 'red', 'purple'][:len(labels)]
    bars = plt.bar(labels, test_losses, color=colors, width=0.5)
    
    plt.title(f"{experiment_name} - Test Loss Comparison")
    plt.ylabel("MSE Loss on Test Set")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.05, f'{yval:.2f}', ha='center', va='bottom', fontsize=10)
        
    plt.tight_layout()
    
    # 保存图片
    save_path = os.path.join(output_dir, f"{save_filename}.png")
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"已保存柱状图至: {save_path}")
