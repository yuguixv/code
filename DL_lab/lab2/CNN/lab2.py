from lab2_base import *

if __name__ == '__main__':
    EPOCHS = 10

    print("\n开始运行基础 CNN 模型(10%数据):")
    train, val, test = prepare_dataloaders(ratio=0.1)

    cnn_model = BaseCNN()
    best_cnn, cnn_hist = train_model(cnn_model, train, val, epochs=EPOCHS, model_name="cnn_best.pth")
    plot_history(cnn_hist, "Base CNN (10% Data)", "cnn_history.png")
    cnn_test_acc, labels, preds = evaluate_model(best_cnn, test)

    #对比项 (4): CNN vs FNN
    print("\n开始运行基础 FNN 模型:")
    fnn_model = FNN()
    best_fnn, fnn_hist = train_model(fnn_model, train, val, epochs=EPOCHS, model_name="fnn_best.pth")
    plot_history(fnn_hist, "FNN(10% Data)", "fnn_history.png")
    fnn_test_acc, _, _ = evaluate_model(best_fnn, test)

    #对比项 (3): Dropout 与 Normalization
    print("\n开始运行带 BatchNorm 与 Dropout 的 CNN:")
    bn_cnn = BatchNormCNN()
    best_bn, bn_hist = train_model(bn_cnn, train, val, epochs=EPOCHS, model_name="bn_cnn.pth")
    plot_history(bn_hist, "CNN with BN & Dropout", "bn_cnn_history.png")
    bn_test_acc, _, _ = evaluate_model(best_bn, test)

    #对比项 (5): 数据规模影响 (增加到 50% 数据)
    print("\n开始运行基础 CNN 模型(50% 数据):")
    train_50, val_50, test_50 = prepare_dataloaders(ratio=0.5)
    cnn_50_model = BaseCNN()
    best_cnn_50, cnn_50_hist = train_model(cnn_50_model, train_50, val_50, epochs=EPOCHS, model_name="cnn_50_best.pth")
    plot_history(cnn_50_hist, "Base CNN (50% Data)", "cnn_50_history.png")
    cnn_50_test_acc, _, _ = evaluate_model(best_cnn_50, test_50)

    # 打印汇总
    print("\n")
    print("实验结果汇总 (Test Accuracy):")
    print(f"基础 CNN (10% 数据): {cnn_test_acc:.4f}")
    print(f"基础 FNN (10% 数据): {fnn_test_acc:.4f}")
    print(f"BN+Drop CNN (10% 数据): {bn_test_acc:.4f}")
    print(f"基础 CNN (50% 数据): {cnn_50_test_acc:.4f}")