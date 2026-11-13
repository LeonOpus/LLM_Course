"""训练脚本"""

import os
import sys
import argparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, get_peft_model, TaskType

from src.train.data_loader_v2 import DeepResearchDatasetV2, create_data_collator


def get_device() -> str:
    """获取可用设备"""
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"


def resolve_dtype(device: str, dtype_arg: str) -> torch.dtype:
    """根据设备与参数选择 dtype"""
    if dtype_arg == "fp32":
        return torch.float32
    if dtype_arg == "fp16":
        return torch.float16
    if dtype_arg == "bf16":
        return torch.bfloat16
    if device == "cuda":
        return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    return torch.float32


def main():
    parser = argparse.ArgumentParser(description="训练 Deep Research Agent")
    parser.add_argument("--train-data", type=str, required=True,
                        help="训练数据路径")
    parser.add_argument("--model-path", type=str,
                        default="/root/autodl-tmp/qwen3_0.6b",
                        help="基础模型路径")
    parser.add_argument("--output-dir", type=str, default="../outputs",
                        help="输出目录")
    parser.add_argument("--max-length", type=int, default=8192,
                        help="最大序列长度")
    parser.add_argument("--batch-size", type=int, default=1,
                        help="批次大小")
    parser.add_argument("--gradient-accumulation", type=int, default=8,
                        help="梯度累积步数")
    parser.add_argument("--epochs", type=int, default=3,
                        help="训练轮数")
    parser.add_argument("--learning-rate", type=float, default=2e-5,
                        help="学习率")
    parser.add_argument("--lora-r", type=int, default=16,
                        help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=32,
                        help="LoRA alpha")
    parser.add_argument("--dtype", type=str, default="auto",
                        choices=["auto", "fp16", "bf16", "fp32"],
                        help="训练精度")
    parser.add_argument("--gradient-checkpointing", action="store_true",
                        help="开启梯度检查点以节省显存")
    parser.add_argument("--save-steps", type=int, default=0,
                        help="每 N 步保存一次 checkpoint（0 表示不按步保存）")

    args = parser.parse_args()

    device = get_device()
    print("=" * 50)
    print("Deep Research Agent 训练")
    print("=" * 50)
    print(f"设备: {device}")
    print(f"模型: {args.model_path}")
    print(f"训练数据: {args.train_data}")
    print(f"最大长度: {args.max_length}")
    print(f"批次大小: {args.batch_size}")
    print(f"梯度累积: {args.gradient_accumulation}")
    print(f"有效批次: {args.batch_size * args.gradient_accumulation}")
    print(f"训练轮数: {args.epochs}")
    print(f"学习率: {args.learning_rate}")
    print(f"LoRA: r={args.lora_r}, alpha={args.lora_alpha}")
    print(f"训练精度: {args.dtype}")
    print("=" * 50)

    # 加载 tokenizer
    print("\n加载 tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_path,
        trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # 加载数据集
    print("\n加载数据集...")
    train_dataset = DeepResearchDatasetV2(
        data_path=args.train_data,
        tokenizer=tokenizer,
        max_length=args.max_length
    )
    print(f"训练样本数: {len(train_dataset)}")

    # 加载模型（不使用 device_map="auto"，手动管理设备）
    print("\n加载模型...")
    dtype = resolve_dtype(device, args.dtype)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        torch_dtype=dtype,  # 按设备与参数选择 dtype
        trust_remote_code=True
    )

    # 配置 LoRA
    print("\n配置 LoRA...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none"
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 设置输出目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(args.output_dir, f"run_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    # 训练参数
    save_strategy = "steps" if args.save_steps and args.save_steps > 0 else "epoch"
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation,
        learning_rate=args.learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_steps=10,
        save_strategy=save_strategy,
        save_steps=args.save_steps if save_strategy == "steps" else None,
        save_total_limit=3,
        fp16=(device == "cuda" and dtype == torch.float16),
        bf16=(device == "cuda" and dtype == torch.bfloat16),
        dataloader_num_workers=0,  # MPS 兼容
        remove_unused_columns=False,
        report_to="none",
        gradient_checkpointing=args.gradient_checkpointing,
    )

    # 数据整理器
    data_collator = create_data_collator(tokenizer)

    # 创建 Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=data_collator,
    )

    # 开始训练
    print("\n开始训练...")
    trainer.train()

    # 保存模型
    print("\n保存模型...")
    final_path = os.path.join(output_dir, "final")
    trainer.save_model(final_path)
    tokenizer.save_pretrained(final_path)

    print(f"\n训练完成！模型保存到: {final_path}")


if __name__ == "__main__":
    main()
