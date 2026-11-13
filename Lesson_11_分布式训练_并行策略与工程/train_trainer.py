import torch
import torch.nn as nn
from torch.utils.data import Dataset

from dataclasses import dataclass, field
from typing import Optional
from transformers import (
    Trainer,
    TrainingArguments,
    HfArgumentParser,
)

# ============ 1) 定义一个自定义模型，forward 返回 loss + logits ============

class SimpleNet(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class SimpleNetForTrainer(nn.Module):
    """
    将 SimpleNet 包装一下，以符合 Hugging Face Trainer 的 forward 签名：
      - 必须要支持 `labels=...` 作为可选参数
      - 返回值 dict 中包含 "loss" (用于反向传播) 和 "logits" (用于评估/推理)
    """
    def __init__(self, input_dim, hidden_dim, output_dim):
        super().__init__()
        self.model = SimpleNet(input_dim, hidden_dim, output_dim)
        self.loss_fn = nn.MSELoss()

    def forward(self, input_ids=None, labels=None):
        # input_ids 就是我们前向传播的输入
        logits = self.model(input_ids)
        
        # 如果提供了 labels，就计算 loss
        loss = None
        if labels is not None:
            loss = self.loss_fn(logits, labels)

        return {"loss": loss, "logits": logits}


# ============ 2) 定义一个自定义数据集，返回 dict ============

class RandomDataset(Dataset):
    """
    随机生成数据: X ~ Normal(0,1),  Y ~ Normal(0,1)
    """
    def __init__(self, size=10000, input_dim=10, output_dim=2):
        super().__init__()
        self.X = torch.randn(size, input_dim)
        self.Y = torch.randn(size, output_dim)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return {
            "input_ids": self.X[idx],
            "labels": self.Y[idx],
        }


# ============ 3) 我们用 HfArgumentParser 来解析命令行参数 ============

@dataclass
class CustomArguments:
    input_dim: int = field(default=10, metadata={"help": "输入维度"})
    hidden_dim: int = field(default=20, metadata={"help": "隐藏层大小"})
    output_dim: int = field(default=2,  metadata={"help": "输出维度"})
    data_size: int = field(default=10000, metadata={"help": "训练集大小"})


def main():
    # 使用 HF 提供的 ArgumentParser，一次性解析多个 dataclass
    parser = HfArgumentParser((CustomArguments, TrainingArguments))
    custom_args, training_args = parser.parse_args_into_dataclasses()

    # ============ 4) 初始化模型、数据集、Trainer ============

    # (a) 模型
    model = SimpleNetForTrainer(
        custom_args.input_dim,
        custom_args.hidden_dim,
        custom_args.output_dim
    )

    # (b) 数据集
    train_dataset = RandomDataset(
        size=custom_args.data_size,
        input_dim=custom_args.input_dim,
        output_dim=custom_args.output_dim
    )
    # 这里只示范一个 train_dataset，也可以加 val_dataset

    # (c) 实例化 Trainer
    trainer = Trainer(
        model=model,
        args=training_args,           # 训练配置: lr, epochs, logging, output_dir等
        train_dataset=train_dataset,
        # 我们直接返回 {"input_ids": x, "labels": y}，不需要额外 collate_fn
        # 如果你想要自定义 collate，可以在这里添加 data_collator=...
    )

    # ============ 5) 开始训练 ============

    trainer.train()
    trainer.save_model(training_args.output_dir)  # 存储最终模型

    print("Finished training & saved model to:", training_args.output_dir)


if __name__ == "__main__":
    main()
