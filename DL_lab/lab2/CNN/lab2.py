from lab2_base import *

if __name__ == '__main__':
    EPOCHS = 10
    
    # --- 实验 1 & 对比项 (4): CNN vs FNN (10% 数据量) ---
    print("\n>>> 开始运行基础 CNN 模型 (10% 数据) <<<")
    train_ld, val_ld, test_ld = prepare_dataloaders(ratio=0.1)

    cnn_model = BaseCNN()
    best_cnn, cnn_hist = train_model(cnn_model, train_ld, val_ld, epochs=EPOCHS, model_name="cnn_best.pth")
    plot_history(cnn_hist, "Base CNN (10% Data)", "cnn_history.png")
    cnn_test_acc, labels, preds = evaluate_model(best_cnn, test_ld)
    plot_confusion_matrix(labels, preds, "cnn_confusion_matrix.png")

    print("\n>>> 开始运行基础 FNN 模型 (对比实验4) <<<")
    fnn_model = FNN()
    best_fnn, fnn_hist = train_model(fnn_model, train_ld, val_ld, epochs=EPOCHS, model_name="fnn_best.pth")
    plot_history(fnn_hist, "FNN (10% Data)", "fnn_history.png")
    fnn_test_acc, _, _ = evaluate_model(best_fnn, test_ld)

    # --- 对比项 (3): Dropout 与 Normalization ---
    print("\n>>> 开始运行带 BN 与 Dropout 的 CNN (对比实验3) <<<")
    robust_cnn = BatchNormCNN()
    best_robust, robust_hist = train_model(robust_cnn, train_ld, val_ld, epochs=EPOCHS, model_name="robust_cnn.pth")
    plot_history(robust_hist, "CNN with BN & Dropout", "robust_cnn_history.png")
    robust_test_acc, _, _ = evaluate_model(best_robust, test_ld)

    # --- 对比项 (5): 数据规模影响 (增加到 50% 数据) ---
    print("\n>>> 开始运行基础 CNN 模型 (50% 数据 - 对比实验5) <<<")
    train_ld_50, val_ld_50, test_ld_50 = prepare_dataloaders(ratio=0.5)
    cnn_50_model = BaseCNN()
    best_cnn_50, cnn_50_hist = train_model(cnn_50_model, train_ld_50, val_ld_50, epochs=EPOCHS, model_name="cnn_50_best.pth")
    plot_history(cnn_50_hist, "Base CNN (50% Data)", "cnn_50_history.png")
    cnn_50_test_acc, _, _ = evaluate_model(best_cnn_50, test_ld_50)

    # 打印汇总
    print("\n" + "="*40)
    print("实验结果汇总 (Test Accuracy):")
    print(f"基础 CNN (10% 数据): {cnn_test_acc:.4f}")
    print(f"基础 FNN (10% 数据): {fnn_test_acc:.4f}")
    print(f"BN+Drop CNN (10% 数据): {robust_test_acc:.4f}")
    print(f"基础 CNN (50% 数据): {cnn_50_test_acc:.4f}")
    print("="*40)