# Agent+SFT 训练说明

本项目用于微调 Qwen3 旅行助手模型。推荐先跑 LoRA 训练，成本最低，也最容易验证流程。

## 1. 安装依赖

```bash
cd Agent+SFT
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果加载 Qwen3 模型时报 tokenizer 或模型结构错误，升级一次核心依赖：

```bash
pip install -U transformers accelerate peft
```

## 2. 下载模型

默认使用 Qwen3-0.6B，并下载到项目根目录下的 `qwen3-0_6b`。

```bash
huggingface-cli download Qwen/Qwen3-0.6B \
  --local-dir ./qwen3-0_6b \
  --local-dir-use-symlinks False
```

下载完成后，目录大概是这样：

```text
qwen3-0_6b/
  config.json
  tokenizer.json
  model.safetensors
  ...
```

## 3. 运行 LoRA 训练

这是最推荐的训练方式。

```bash
python3 train_qwen_last_assistant_lora.py \
  --train_file ./merged_train_final_multiturn_v2.json \
  --model_name_or_path ./qwen3-0_6b \
  --output_dir ./qwen3-0_6b_lora_last_assistant \
  --max_seq_length 20000 \
  --per_device_train_batch_size 1 \
  --gradient_accumulation_steps 8 \
  --learning_rate 2e-5 \
  --num_train_epochs 1 \
  --warmup_ratio 0.03 \
  --logging_steps 10 \
  --save_steps 1000 \
  --save_total_limit 3 \
  --lr_scheduler_type cosine \
  --bf16 \
  --gradient_checkpointing \
  --local_files_only
```

训练完成后，LoRA adapter 会保存在：

```text
./qwen3-0_6b_lora_last_assistant
```

## 4. 可选：合并 LoRA 到基础模型

如果需要得到一个可直接加载的完整模型，可以执行：

```bash
python3 merge_lora_into_base.py \
  --base_model ./qwen3-0_6b \
  --adapter_path ./qwen3-0_6b_lora_last_assistant \
  --output_dir ./qwen3-0_6b_lora_merged \
  --bf16 \
  --local_files_only
```

合并后的模型保存在：

```text
./qwen3-0_6b_lora_merged
```

## 5. 可选：全参训练

全参训练显存占用更高，不建议作为第一步验证。

```bash
python3 train_qwen_full_finetune_last_assistant.py \
  --train_file ./merged_train_final_multiturn_v2.json \
  --model_name_or_path ./qwen3-0_6b \
  --output_dir ./qwen3-0_6b_fullft_last_assistant \
  --max_seq_length 14096 \
  --per_device_train_batch_size 1 \
  --gradient_accumulation_steps 16 \
  --learning_rate 2e-5 \
  --num_train_epochs 1 \
  --warmup_ratio 0.03 \
  --logging_steps 10 \
  --save_steps 300 \
  --save_total_limit 3 \
  --lr_scheduler_type cosine \
  --bf16 \
  --gradient_checkpointing \
  --local_files_only
```

## 常用文件

```text
merged_train_final_multiturn_v2.json      训练数据
train_qwen_last_assistant_lora.py         LoRA 训练脚本
train_qwen_full_finetune_last_assistant.py 全参训练脚本
merge_lora_into_base.py                   LoRA 合并脚本
qwen3-0_6b/                               本地基础模型目录
```
