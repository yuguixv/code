import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, Subset, random_split
import numpy as np

# 设置随机种子
torch.manual_seed(42)
np.random.seed(42)

# 数据预处理
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,))
])

# 加载完整数据集
train_dataset = datasets.MNIST(
    root='./data', 
    train=True, 
    download=True, 
    transform=transform
)
test_dataset = datasets.MNIST(
    root='./data', 
    train=False, 
    transform=transform
)

# 随机抽取1%数据
def get_subset(dataset, ratio=0.1):
    indices = np.random.choice(
        len(dataset), 
        size=int(len(dataset)*ratio), 
        replace=False
    )
    return Subset(dataset, indices)

total_train_subset = get_subset(train_dataset)
test_subset = get_subset(test_dataset)

train_size = int(0.8 * len(total_train_subset))
val_size = len(total_train_subset) - train_size
train_subset, val_subset = random_split(total_train_subset, [train_size, val_size])

# 创建DataLoader
train_loader = DataLoader(train_subset, batch_size=16, shuffle=True)
test_loader = DataLoader(test_subset, batch_size=16)
val_loader = DataLoader(val_subset, batch_size=16)


print(f"训练样本数: {len(train_subset)}, 测试样本数: {len(test_subset)}")

class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3)
        self.pool = nn.MaxPool2d(2)
        self.dropout = nn.Dropout(0.5)
        self.fc1 = nn.Linear(64 * 5 * 5, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = self.pool(F.relu(self.conv2(x)))
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)