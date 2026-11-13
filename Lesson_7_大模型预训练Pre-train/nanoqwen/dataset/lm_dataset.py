import json
import random
import re

import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
import torch
from sklearn.model_selection import train_test_split
import os
import ast

os.environ["TOKENIZERS_PARALLELISM"] = "false"


class PretrainDataset(Dataset):
    def __init__(self, data_path, tokenizer, max_length=512):
        super().__init__()
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.samples = self.load_data(data_path)

    def load_data(self, path):
        samples = []
        with open(path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                data = json.loads(line.strip())
                samples.append(data)
        return samples

#魔法方法
    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        sample = self.samples[index]

        # 构建输入文本
        encoding = self.tokenizer(
            str(sample['text']),
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        # encoding.input_ids 可能的形状：[1, seq_len] 或 [seq_len]
        # squeeze() 去掉大小为1的维度
        # 结果：[seq_len] - 一维的 token ID 列表

        # 例如：
        # 原始文本: "Hello world"
        # input_ids: [101, 7592, 2088, 102]  # 对应 [CLS, Hello, world, SEP]
        input_ids = encoding.input_ids.squeeze()
        # 假设 pad_token_id = 0
        # input_ids:  [101, 7592, 2088, 102, 0, 0, 0]  # 后面是padding
        # loss_mask:  [True, True, True, True, False, False, False]
        loss_mask = (input_ids != self.tokenizer.pad_token_id)
        # 原始数据
        # texts = ["Hello world", "Hi there my friend"]

        # # tokenize后（padding到相同长度）
        # input_ids = [
        #     [101, 7592, 2088, 102, 0, 0],     # "Hello world" + padding
        #     [101, 7592, 2045, 2026, 2767, 102] # "Hi there my friend"
        # ]

        # # loss_mask
        # loss_mask = [
        #     [True, True, True, True, False, False],  # 前4个是真实token
        #     [True, True, True, True, True, True]     # 全是真实token
        # ]

        X = torch.tensor(input_ids[:-1], dtype=torch.long)
        Y = torch.tensor(input_ids[1:], dtype=torch.long)

        # ## X 和 Y 的取法

        # ```python
        # X = torch.tensor(input_ids[:-1], dtype=torch.long)  # 前49个token
        # Y = torch.tensor(input_ids[1:], dtype=torch.long)   # 后49个token
        # ```

        # **具体示例：**
        # ```python
        # # 原始序列（长度50）
        # input_ids = [101, 7592, 2088, 102, 2023, ..., 999]  # 50个token

        # # X (输入) = 前49个
        # X = [101, 7592, 2088, 102, 2023, ..., 888]  # input_ids[:-1]

        # # Y (标签) = 后49个  
        # Y = [7592, 2088, 102, 2023, 999, ..., 999]  # input_ids[1:]
        # ```

        # ## 训练原理：下一个词预测

        # | 位置 | 输入 X | 目标 Y | 含义 |
        # |------|--------|--------|------|
        # | 0 | 101 | 7592 | 给定101，预测7592 |
        # | 1 | 7592 | 2088 | 给定7592，预测2088 |
        # | 2 | 2088 | 102 | 给定2088，预测102 |
        # | ... | ... | ... | ... |
        # | 48 | 888 | 999 | 给定888，预测999 |

        # ## 损失计算：一次计算49个位置

        # **不是计算50次loss，而是1次计算包含49个位置的loss！**

        # ```python
        # # 模型前向传播
        # logits = model(X)  # 形状: [49, vocab_size]

        # # 损失计算（一次性计算所有位置）
        # loss = CrossEntropyLoss(logits, Y)  # 自动处理所有49个位置
        # ```

        # ## 实际训练流程

        # ```python
        # # 1. 输入序列
        # input_ids = [101, 7592, 2088, 102, 2023]  # 长度5

        # # 2. 构造训练对
        # X = [101, 7592, 2088, 102]     # 前4个
        # Y = [7592, 2088, 102, 2023]    # 后4个

        # # 3. 模型预测
        # predictions = model(X)  # [4, vocab_size]

        # # 4. 计算损失（一次性计算4个位置）
        # loss = criterion(predictions, Y)  # 标量值
        # ```

        # ## 为什么这样设计？

        # 1. **并行计算** - GPU可以同时处理所有位置
        # 2. **效率高** - 一次前向传播预测多个token
        # 3. **Teacher Forcing** - 训练时用真实历史，而非模型预测

        # ## 推理时的区别

        # ```python
        # # 训练：并行预测所有位置
        # X = [101, 7592, 2088, 102]
        # Y_pred = model(X)  # 一次预测4个位置

        # # 推理：逐个生成
        # tokens = [101]
        # for i in range(max_len):
        #     next_token = model(tokens).argmax()
        #     tokens.append(next_token)
        # ```

        # **总结：** 长度50的数据会产生49个训练样本，但只计算1次loss（包含49个位置的损失），这样既高效又能充分利用序列信息。
        loss_mask = torch.tensor(loss_mask[1:], dtype=torch.long)
        return X, Y, loss_mask



if __name__ == "__main__":
    pass
