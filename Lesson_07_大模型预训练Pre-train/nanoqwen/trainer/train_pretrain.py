import os
import sys
__package__ = "trainer"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
import time
import math
import warnings
import torch
import torch.distributed as dist
from torch import optim, nn
from torch.nn.parallel import DistributedDataParallel
from torch.utils.data import DataLoader, DistributedSampler
from contextlib import nullcontext
from transformers import AutoTokenizer
from model.model_nanoqwen import NanoQwenConfig, NanoQwenForCausalLM
from dataset.lm_dataset import PretrainDataset

warnings.filterwarnings('ignore')


def Logger(content):
    """
    分布式训练友好的日志打印函数
    只有在非分布式训练或者是主进程(rank=0)时才打印日志
    """
    if not ddp or dist.get_rank() == 0:
        print(content)


def get_lr(current_step, total_steps, lr):
    """
    余弦退火学习率调度器
    Args:
        current_step: 当前训练步数
        total_steps: 总训练步数  
        lr: 基础学习率
    Returns:
        调整后的学习率
    """
    # 使用余弦退火公式：lr_min + 0.5 * (lr_max - lr_min) * (1 + cos(π * t / T))
    # 这里lr_min = lr/10, lr_max = lr
    return lr / 10 + 0.5 * lr * (1 + math.cos(math.pi * current_step / total_steps))


def train_epoch(epoch, wandb):
    """
    训练一个epoch的函数
    Args:
        epoch: 当前epoch编号
        wandb: wandb日志记录器（可能为None）
    """
    # 创建交叉熵损失函数，reduction='none'表示不自动求平均
    loss_fct = nn.CrossEntropyLoss(reduction='none')
    # 记录训练开始时间
    start_time = time.time()
    
    # 遍历训练数据加载器
    for step, (X, Y, loss_mask) in enumerate(train_loader):
        # 将输入数据移动到指定设备（GPU）
        X = X.to(args.device)
        Y = Y.to(args.device)
        loss_mask = loss_mask.to(args.device)

        # 根据当前步数计算学习率
        lr = get_lr(epoch * iter_per_epoch + step, args.epochs * iter_per_epoch, args.learning_rate)
        # 更新优化器中所有参数组的学习率
        for param_group in optimizer.param_groups:
            param_group['lr'] = lr

        # 在自动混合精度上下文中进行前向传播
        with ctx:
            # 模型前向传播，获取输出
            res = model(X)
            # 计算交叉熵损失
            # 将logits和目标标签展平为一维，然后计算损失，再恢复原始形状
            loss = loss_fct(
                res.logits.view(-1, res.logits.size(-1)),  # [batch*seq, vocab_size]
                Y.view(-1)  # [batch*seq]
            ).view(Y.size())  # 恢复为 [batch, seq]
            
            # 应用损失掩码，只计算非padding位置的损失
            loss = (loss * loss_mask).sum() / loss_mask.sum()
            # 如果模型有辅助损失（如MoE的负载均衡损失），加上辅助损失
            loss += res.aux_loss
            # 梯度累积：将损失除以累积步数
            loss = loss / args.accumulation_steps

# 混合精度训练中的问题
# FP16 的数值范围：6.1e-5 到 65504
# 但梯度往往很小，比如：1e-7, 1e-8

# gradient = 1e-7  # 这个梯度在 FP16 中会变成 0！
# fp16_gradient = torch.tensor(gradient, dtype=torch.float16)
# print(fp16_gradient)  # tensor(0., dtype=torch.float16)
# 后果
# 梯度消失 - 小梯度被截断为0
# 训练停滞 - 模型参数无法更新
# 数值不稳定 - 训练过程不收敛

        # 使用梯度缩放器进行反向传播（用于混合精度训练）
        scaler.scale(loss).backward()

        # 梯度累积：每accumulation_steps步执行一次参数更新
        if (step + 1) % args.accumulation_steps == 0:
            # 取消梯度缩放，恢复真实梯度值
            scaler.unscale_(optimizer)
            # 梯度裁剪，防止梯度爆炸
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)

            # 执行优化器步骤，更新模型参数
            scaler.step(optimizer)
            # 更新梯度缩放器的缩放因子
            scaler.update()

            # 清零梯度，set_to_none=True可以节省内存
            optimizer.zero_grad(set_to_none=True)

        # 每log_interval步打印一次训练日志
        if step % args.log_interval == 0:
            # 计算已用时间
            spend_time = time.time() - start_time
            # 打印训练进度信息
            Logger(
                'Epoch:[{}/{}]({}/{}) loss:{:.3f} lr:{:.12f} epoch_Time:{}min:'.format(
                    epoch + 1,  # 当前epoch（从1开始）
                    args.epochs,  # 总epoch数
                    step,  # 当前步数
                    iter_per_epoch,  # 每个epoch的总步数
                    loss.item() * args.accumulation_steps,  # 真实损失值
                    optimizer.param_groups[-1]['lr'],  # 当前学习率
                    spend_time / (step + 1) * iter_per_epoch // 60 - spend_time // 60))  # 预计剩余时间

            # 如果启用了wandb且是主进程，记录训练指标
            if (wandb is not None) and (not ddp or dist.get_rank() == 0):
                wandb.log({"loss": loss.item() * args.accumulation_steps,
                           "lr": optimizer.param_groups[-1]['lr'],
                           "epoch_Time": spend_time / (step + 1) * iter_per_epoch // 60 - spend_time // 60})

        # 每save_interval步保存一次模型检查点
        if (step + 1) % args.save_interval == 0 and (not ddp or dist.get_rank() == 0):
            # 切换到评估模式
            model.eval()
            # 根据是否使用MoE构造保存路径
            moe_path = '_moe' if lm_config.use_moe else ''
            ckp = f'{args.save_dir}/pretrain_{lm_config.hidden_size}{moe_path}.pth'

            # 获取模型状态字典（处理分布式训练的情况）
            if isinstance(model, torch.nn.parallel.DistributedDataParallel):
                state_dict = model.module.state_dict()
            else:
                state_dict = model.state_dict()

            # 将权重转换为半精度以节省存储空间
            state_dict = {k: v.half() for k, v in state_dict.items()}
            # 保存模型检查点
            torch.save(state_dict, ckp)
            # 切换回训练模式
            model.train()


def init_model(lm_config):
    """
    初始化模型和分词器
    Args:
        lm_config: 语言模型配置
    Returns:
        model: 初始化的模型
        tokenizer: 分词器
    """
    # 从本地路径加载分词器
    tokenizer = AutoTokenizer.from_pretrained('../model/')
    # 创建NanoQwen模型并移动到指定设备
    model = NanoQwenForCausalLM(lm_config).to(args.device)
    # 打印模型可训练参数数量
    Logger(f'LLM可训练总参数量：{sum(p.numel() for p in model.parameters() if p.requires_grad) / 1e6:.3f} 百万')
    return model, tokenizer


def init_distributed_mode():
    """
    初始化分布式训练环境
    设置进程组、本地rank、设备等
    """
    if not ddp: return  # 如果不是分布式训练，直接返回
    global ddp_local_rank, DEVICE

    # 初始化NCCL后端的进程组
    dist.init_process_group(backend="nccl")
    # 获取分布式训练的各种rank信息
    ddp_rank = int(os.environ["RANK"])  # 全局rank
    ddp_local_rank = int(os.environ["LOCAL_RANK"])  # 本地rank
    ddp_world_size = int(os.environ["WORLD_SIZE"])  # 总进程数
    # 设置当前进程使用的GPU设备
    DEVICE = f"cuda:{ddp_local_rank}"
    torch.cuda.set_device(DEVICE)


# 分布式训练启动命令示例：torchrun --nproc_per_node 2 train_pretrain.py
if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="NanoQwen Pretraining")
    # 输出目录
    parser.add_argument("--out_dir", type=str, default="../out")
    # 训练轮数（epochs设置为1可快速验证，实际训练建议2-6轮）
    parser.add_argument("--epochs", type=int, default=1)
    # 批次大小
    parser.add_argument("--batch_size", type=int, default=32)
    # 学习率
    parser.add_argument("--learning_rate", type=float, default=5e-4)
    # 训练设备
    parser.add_argument("--device", type=str, default="cuda:0" if torch.cuda.is_available() else "cpu")
    # 数据类型（支持混合精度训练）
    parser.add_argument("--dtype", type=str, default="bfloat16")
    # 是否使用wandb记录训练过程
    parser.add_argument("--use_wandb", action="store_true")
    # wandb项目名称
    parser.add_argument("--wandb_project", type=str, default="NanoQwen-Pretrain")
    # 数据加载器工作进程数
    parser.add_argument("--num_workers", type=int, default=1)
    # 是否启用分布式数据并行训练
    parser.add_argument("--ddp", action="store_true")
    # 梯度累积步数
    parser.add_argument("--accumulation_steps", type=int, default=8)
    # 梯度裁剪阈值
    parser.add_argument("--grad_clip", type=float, default=1.0)
    # 预热迭代次数
    parser.add_argument("--warmup_iters", type=int, default=0)
    # 日志打印间隔
    parser.add_argument("--log_interval", type=int, default=100)
    # 模型保存间隔
    parser.add_argument("--save_interval", type=int, default=100)
    # 本地rank（分布式训练用）
    parser.add_argument('--local_rank', type=int, default=-1)
    # 模型隐藏层维度
    parser.add_argument('--hidden_size', default=512, type=int)
    # 模型层数
    parser.add_argument('--num_hidden_layers', default=8, type=int)
    # 最大序列长度
    parser.add_argument('--max_seq_len', default=512, type=int)
    # 是否使用MoE（专家混合）
    parser.add_argument('--use_moe', default=False, type=bool)
    # 训练数据路径
    parser.add_argument("--data_path", type=str, default="../dataset/pretrain_hq.jsonl")
    # 解析命令行参数
    args = parser.parse_args()

    # 创建语言模型配置
    lm_config = NanoQwenConfig(hidden_size=args.hidden_size, num_hidden_layers=args.num_hidden_layers, use_moe=args.use_moe)
    # 设置保存目录
    args.save_dir = os.path.join(args.out_dir)
    # 创建必要的目录
    os.makedirs(args.save_dir, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)
    # 计算每次迭代处理的token数量
    tokens_per_iter = args.batch_size * args.max_seq_len
    # 确定设备类型
    device_type = "cuda" if "cuda" in args.device else "cpu"

    # 构造wandb运行名称
    args.wandb_run_name = f"NanoQwen-Pretrain-Epoch-{args.epochs}-BatchSize-{args.batch_size}-LearningRate-{args.learning_rate}"

    # 根据设备类型设置自动混合精度上下文
    ctx = nullcontext() if device_type == "cpu" else torch.cuda.amp.autocast()

    # 检查是否为分布式训练（通过环境变量RANK判断）
    ddp = int(os.environ.get("RANK", -1)) != -1
    # 初始化分布式训练相关变量
    ddp_local_rank, DEVICE = 0, "cuda:0"

    # 设置随机种子以确保结果可复现
    base_seed = 1337
    torch.manual_seed(base_seed)
    torch.cuda.manual_seed(base_seed)

    # 如果是分布式训练，进行相应初始化
    if ddp:
        init_distributed_mode()
        args.device = torch.device(DEVICE)
        rank = dist.get_rank()
        # 为不同进程设置不同的随机种子
        torch.manual_seed(base_seed + rank)
        torch.cuda.manual_seed(base_seed + rank)

    # 初始化wandb（仅在主进程）
    if args.use_wandb and (not ddp or ddp_local_rank == 0):
        import wandb
        wandb.init(project=args.wandb_project, name=args.wandb_run_name)
    else:
        wandb = None

    # 初始化模型和分词器
    model, tokenizer = init_model(lm_config)
    # 创建训练数据集
    train_ds = PretrainDataset(args.data_path, tokenizer, max_length=args.max_seq_len)
    # 创建分布式采样器（如果是分布式训练）
    train_sampler = DistributedSampler(train_ds) if ddp else None
    # 创建数据加载器
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        pin_memory=True,  # 将数据固定在内存中，加速GPU传输
        drop_last=False,  # 不丢弃最后一个不完整的batch
        shuffle=False,  # 分布式训练时由sampler控制shuffle
        num_workers=args.num_workers,
        sampler=train_sampler
    )

    # 创建梯度缩放器（用于混合精度训练）
    scaler = torch.cuda.amp.GradScaler(enabled=(args.dtype in ['float16', 'bfloat16']))
    # 创建AdamW优化器
    optimizer = optim.AdamW(model.parameters(), lr=args.learning_rate)

    # 如果是分布式训练，包装模型为DistributedDataParallel
    if ddp:
        # 指定不需要同步梯度的参数（位置编码通常不需要）
        model._ddp_params_and_buffers_to_ignore = {"pos_cis"}
        model = DistributedDataParallel(model, device_ids=[ddp_local_rank])

    # 计算每个epoch的迭代次数
    iter_per_epoch = len(train_loader)
    # 开始训练循环
    for epoch in range(args.epochs):
        train_epoch(epoch, wandb)
