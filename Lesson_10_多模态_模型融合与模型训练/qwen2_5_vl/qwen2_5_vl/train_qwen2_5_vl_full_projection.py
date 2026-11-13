# -*- coding: utf-8 -*-
"""
Qwen2.5-VL-3B-Instruct —— 仅训练投影层（visual.merger），冻结其他所有参数

  
# 主要区别
#冻结方式
#加载器
#TrainingArguments训练配置
#模型的加载和推理
"""

import os
import json
import torch
import torch.nn as nn
from datasets import Dataset
from modelscope import AutoTokenizer  # 你本地化了模型，直接从目录加载即可
from transformers import (
    TrainingArguments,
    Trainer,
    AutoProcessor,
    Qwen2_5_VLForConditionalGeneration,
)
from qwen_vl_utils import process_vision_info

# ========================== 配置 ==========================
MODEL_DIR = "./Qwen2.5-VL-3B-Instruct/"      # 本地模型目录
DATA_JSON = "data_vl.json"                   # 你的数据文件
OUTPUT_DIR = "./Qwen2.5-VL-3B_projector_only"
PROMPT_PREFIX = "COCO Yes:"                  # 你的提示前缀
USE_SWANLAB = True                           # 是否启用 SwanLab 回调

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========================== 预处理函数 ==========================
def process_func(example):
    """
    将一条样本转换为模型可用的张量：
    - input_ids / attention_mask / labels
    - pixel_values / image_grid_thw（视觉输入）
    """
    MAX_LENGTH = 8192
    conversation = example["conversations"]
    input_content = conversation[0]["value"]
    output_content = conversation[1]["value"]

    # 取图像路径
    file_path = input_content.split("<|vision_start|>")[1].split("<|vision_end|>")[0]
    # 修正为相对路径（避免 / 开头导致读取失败）
    if file_path.startswith('/'):
        file_path = '.' + file_path

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": f"{file_path}", "resized_height": 280, "resized_width": 280},
                {"type": "text", "text": PROMPT_PREFIX},
            ],
        }
    ]

    # 文本模板（不分词）
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    # 视觉预处理
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )

    # 用 tokenizer 编答案（只需 input_ids；attention_mask 用 1 填充）
    resp = tokenizer(f"{output_content}", add_special_tokens=False)
    resp_ids = resp["input_ids"]
    resp_attn = [1] * len(resp_ids)

    # 拼接监督信号（instruction + response + PAD）
    input_ids = inputs["input_ids"][0].tolist() + resp_ids + [tokenizer.pad_token_id]
    attention_mask = inputs["attention_mask"][0].tolist() + resp_attn + [1]
    labels = ([-100] * inputs["input_ids"].size(1)) + resp_ids + [tokenizer.pad_token_id]

    # 截断
    if len(input_ids) > MAX_LENGTH:
        input_ids = input_ids[:MAX_LENGTH]
        attention_mask = attention_mask[:MAX_LENGTH]
        labels = labels[:MAX_LENGTH]

    # 回到 tensor
    input_ids = torch.tensor(input_ids, dtype=torch.long)
    attention_mask = torch.tensor(attention_mask, dtype=torch.long)
    labels = torch.tensor(labels, dtype=torch.long)

    # 视觉张量
    pixel_values = inputs["pixel_values"]                 # [1, ...]
    image_grid_thw = inputs["image_grid_thw"].squeeze(0)  # (h, w)

    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "labels": labels,
        "pixel_values": pixel_values,
        "image_grid_thw": image_grid_thw,
    }


# ========================== 自定义 Collator ==========================
class QwenVlCollator:
    """
    稳健 Collator：将 list 强转为 tensor，pad 序列，stack 视觉张量
    """

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    @staticmethod
    def _to_tensor(x, dtype=None):
        if isinstance(x, torch.Tensor):
            return x
        return torch.tensor(x, dtype=dtype) if dtype is not None else torch.tensor(x)

    def __call__(self, features):
        # 文本三件套
        input_ids = [self._to_tensor(f["input_ids"], dtype=torch.long) for f in features]
        attention_mask = [self._to_tensor(f["attention_mask"], dtype=torch.long) for f in features]
        labels = [self._to_tensor(f["labels"], dtype=torch.long) for f in features]

        input_ids = nn.utils.rnn.pad_sequence(
            input_ids, batch_first=True, padding_value=self.tokenizer.pad_token_id
        )
        attention_mask = nn.utils.rnn.pad_sequence(
            attention_mask, batch_first=True, padding_value=0
        )
        labels = nn.utils.rnn.pad_sequence(
            labels, batch_first=True, padding_value=-100
        )

        # 视觉侧
        pixel_values = [self._to_tensor(f["pixel_values"]) for f in features]
        # 通常是 [1, C, T, H, W] 或 [1, N, C, H, W]，压掉最前面 1
        pixel_values = [pv.squeeze(0) if pv.dim() >= 5 and pv.size(0) == 1 else pv for pv in pixel_values]
        pixel_values = torch.stack(pixel_values, dim=0)  # [B, ...]

        image_grid_thw = [self._to_tensor(f["image_grid_thw"]) for f in features]
        image_grid_thw = torch.stack(image_grid_thw, dim=0)  # [B, h, w]

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
            "pixel_values": pixel_values,
            "image_grid_thw": image_grid_thw,
        }


# ========================== 推理函数 ==========================
@torch.no_grad()
def predict(messages, model, processor):
    model.eval()
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    device = next(model.parameters()).device
    inputs = inputs.to(device)

    generated_ids = model.generate(**inputs, max_new_tokens=128)
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    return output_text[0]


# ========================== 主流程 ==========================
def main():
    global tokenizer, processor  # 声明为全局变量
    # 1) 加载分词器
    tokenizer = AutoTokenizer.from_pretrained("./Qwen2.5-VL-3B-Instruct/", use_fast=False, trust_remote_code=True)
    
    # 2) 加载模型
    processor = AutoProcessor.from_pretrained("./Qwen2.5-VL-3B-Instruct/")

    model = Qwen2_5_VLForConditionalGeneration.from_pretrained("./Qwen2.5-VL-3B-Instruct/", device_map="auto", torch_dtype=torch.bfloat16, trust_remote_code=True,)
    model.enable_input_require_grads()  # 开启梯度检查点时，要执行该方法

    # 3) 只训练投影层：冻结其它所有参数【区别1】
    for p in model.parameters():
        p.requires_grad = False
    for p in model.model.visual.merger.parameters():
        p.requires_grad = True

    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[Info] projector-only: trainable={trainable/1e6:.3f}M / total={total/1e6:.1f}M")

    # 4) 数据集：读取、切分并映射
    with open(DATA_JSON, 'r', encoding="utf-8") as f:
        data = json.load(f)
    train_data, test_data = data[:-4], data[-4:]

    # with open("data_vl_train.json", "w", encoding="utf-8") as f:
    #     json.dump(train_data, f, ensure_ascii=False)
    # with open("data_vl_test.json", "w", encoding="utf-8") as f:
    #     json.dump(test_data, f, ensure_ascii=False)

    train_ds = Dataset.from_json("data_vl_train.json")
    # map 后移除原始列，避免重复缓存
    train_dataset = train_ds.map(process_func, remove_columns=train_ds.column_names)


    # train_dataset.set_format(
    #     type="torch",
    #     columns=["input_ids", "attention_mask", "labels", "pixel_values", "image_grid_thw"]
    # )

    # 5) 训练参数
    args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        num_train_epochs=2,
        learning_rate=2e-4,              # projector-only 可适当偏大
        logging_steps=10,
        logging_first_step=True,
        save_steps=200,
        save_total_limit=2,
        gradient_checkpointing=True,
        bf16=True,                       # 若上面用 float16，请改为 fp16=True
        report_to="none",
        save_on_each_node=True,
        tf32=True,
        dataloader_num_workers=2,
    )

    # 6) SwanLab 回调（可选）
    callbacks = []
    if USE_SWANLAB:
        try:
            from swanlab.integration.transformers import SwanLabCallback
            swanlab_callback = SwanLabCallback(
                project="Qwen2.5-VL-finetune",
                experiment_name="qwen2_5_vl_3b_projector_only",
                config={
                    "model": "Qwen2.5-VL-3B-Instruct",
                    "prompt": PROMPT_PREFIX,
                    "train_data_number": len(train_data),
                    "trainable": "model.model.visual.merger",
                    "lr": args.learning_rate,
                    "batch_size": args.per_device_train_batch_size,
                },
            )
            callbacks = [swanlab_callback]
        except Exception as e:
            print(f"[Warn] SwanLab not enabled: {e}")

    # 7) Trainer（使用自定义 Collator）
    collator = QwenVlCollator(tokenizer)
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        data_collator=collator,
        callbacks=callbacks,
    )

    # 8) 训练
    trainer.train()

    # 9) 选择最后一个 checkpoint 路径
    def get_last_checkpoint(dir_):
        ckpts = [d for d in os.listdir(dir_) if d.startswith("checkpoint-")]
        if not ckpts:
            return dir_
        ckpts = sorted(ckpts, key=lambda x: int(x.split("-")[-1]))
        return os.path.join(dir_, ckpts[-1])

    last_ckpt = get_last_checkpoint(OUTPUT_DIR)
    print(f"[Info] last checkpoint: {last_ckpt}")

    # 10) 重新加载 checkpoint 做推理
    val_model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        last_ckpt,
        device_map="auto",
        torch_dtype=torch.bfloat16,   # 与训练一致
        trust_remote_code=True,
    )

    with open("data_vl_test.json", "r", encoding="utf-8") as f:
        test_dataset = json.load(f)

    preds = []
    for item in test_dataset:
        input_image_prompt = item["conversations"][0]["value"]
        origin_image_path = input_image_prompt.split("<|vision_start|>")[1].split("<|vision_end|>")[0]
        if origin_image_path.startswith('/'):
            origin_image_path = '.' + origin_image_path

        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": origin_image_path},
                {"type": "text", "text": PROMPT_PREFIX},
            ],
        }]

        out = predict(messages, val_model, processor)
        preds.append((origin_image_path, out))
        print({"image": origin_image_path, "prediction": out})



if __name__ == "__main__":
    # 全局 tokenizer / processor 需要在 process_func 里使用，放在 main 外创建不方便；
    # 因此这里在第一时间调用 main，使其在内部创建，并复用其闭包中的 tokenizer/processor。
    # 为了让 process_func 拿到 tokenizer/processor，将它们声明为全局变量。
    global tokenizer, processor
    # 先进行一次最小初始化（main 内会覆盖）
    tokenizer = None
    processor = None
    # 实际运行
    # 在 main() 内部会重新对 tokenizer/processor 赋值，并供 process_func 使用
    # 这是为了让 map(process_func) 能访问到这两个对象
    main()

