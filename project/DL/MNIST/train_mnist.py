import os
# 明确指定 Keras 3 使用 TensorFlow 后端
os.environ["KERAS_BACKEND"] = "tensorflow"

import keras
from keras import layers
import numpy as np

print("开始加载 MNIST 数据集...")
# 1. 准备数据
(x_train, y_train), (x_test, y_test) = keras.datasets.mnist.load_data()

# 归一化像素值到 [0, 1] 范围，并增加一个通道维度 (因为是灰度图)
x_train = x_train.astype("float32") / 255.0
x_test = x_test.astype("float32") / 255.0
x_train = np.expand_dims(x_train, -1)
x_test = np.expand_dims(x_test, -1)

print(f"训练集形状: {x_train.shape}")
print(f"测试集形状: {x_test.shape}")

# 2. 构建卷积神经网络 (CNN) 模型
# 
model = keras.Sequential(
    [
        keras.Input(shape=(28, 28, 1)),
        layers.Conv2D(32, kernel_size=(3, 3), activation="relu"),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Conv2D(64, kernel_size=(3, 3), activation="relu"),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Flatten(),
        layers.Dropout(0.5),
        layers.Dense(10, activation="softmax"),
    ]
)

model.summary()

# 3. 编译模型
model.compile(
    loss="sparse_categorical_crossentropy", 
    optimizer="adam", 
    metrics=["accuracy"]
)

# 4. 训练模型！(这里就是 GPU 狂飙的时刻)
print("\n开始在 GPU 上训练模型...")
batch_size = 128
epochs = 5

history = model.fit(
    x_train, 
    y_train, 
    batch_size=batch_size, 
    epochs=epochs, 
    validation_split=0.1
)

# 5. 评估模型
print("\n开始在测试集上评估模型...")
score = model.evaluate(x_test, y_test, verbose=0)
print(f"测试集损失 (Loss): {score[0]:.4f}")
print(f"测试集准确率 (Accuracy): {score[1]:.4f}")