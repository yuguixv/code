import torch
import torch.nn as nn
import torch.optim as optim

X_svm = torch.randn(100, 2)
y_svm = (X_svm[:,0] + X_svm[:,1] > 0).float() * 2 - 1
y_svm = y_svm.view(-1, 1)

class LinearSVM(nn.Module):
    def __init__(self, input_dim):
        super(LinearSVM, self).__init__()
        self.linear = nn.Linear(input_dim, 1)

    def forward(self, x):
        return self.linear(x)
    
model_svm = LinearSVM(input_dim = 2)
optimizer_svm = optim.SGD(model_svm.parameters(), lr=0.05, weight_decay=0.01)

print("开始训练 SVM 模型...")
for epoch in range(100):
    optimizer_svm.zero_grad()
    outputs = model_svm(X_svm)
    hinge_loss = torch.mean(torch.clamp(1 - outputs * y_svm, min = 0))

    hinge_loss.backward()
    optimizer_svm.step()

    if (epoch + 1) % 20 == 0:
        print(f"Epoch [{epoch + 1}/100], Hinge Loss: {hinge_loss.item():.4f}")