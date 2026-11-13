#!/bin/bash

# 如果脚本中的任何命令执行失败，则立即退出
set -e

# 这里是你原本要运行的 Accelerate 启动命令
# 使用反斜杠 `\` 将长命令分成多行，更易读
accelerate launch \
    --config_file accelerate_config.yaml \
    train_on_multi_gpu.py \
    --model_id_or_path "Qwen2.5-7B-Instruct" \
    --dataset_path "distil_gpt4_1_dataset/gpt_4_1_processed_results.json" \
    --output_dir "sft_lora_model_int8_ds_output_2gpu" \
    --per_device_train_batch_size 1 \
    --gradient_accumulation_steps 8 \
    --optimizer "adamw_torch" \
    --save_steps 500 \
    --logging_steps 2 \
    --learning_rate 1e-4 \
    --num_train_epochs 1 \
    --max_grad_norm 0.3 \
    --lr_scheduler_type "cosine" \
    --weight_decay 0.01 \
    --warmup_ratio 0.03 \
    --no_bf16  \
    --no_gradient_checkpointing \
    --max_seq_length 2048 \
    --no_packing \
    --lora_alpha 16 \
    --lora_dropout 0.0 \
    --lora_target_modules "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj" \
    --load_in_8bit \
    --report_to "wandb" \
    --wandb_project "finetune_dsr1-ds-2gpu-distil"

echo "训练脚本成功完成。" # 脚本成功结束时打印一条消息

# chmod +x run_distill_train.sh
# nohup ./run_distill_train.sh > train.log 2>&1 &