import argparse
import random
import warnings
import numpy as np
import torch
from transformers import AutoTokenizer, TextStreamer
from model.model_nanoqwen import NanoQwenConfig, NanoQwenForCausalLM

warnings.filterwarnings('ignore')


def init_model(args):
    tokenizer = AutoTokenizer.from_pretrained('./model/')
    moe_path = '_moe' if args.use_moe else ''
    ckp = f'./{args.out_dir}/pretrain_{args.hidden_size}{moe_path}_1.pth'

    model = NanoQwenForCausalLM(NanoQwenConfig(
        hidden_size=args.hidden_size,
        num_hidden_layers=args.num_hidden_layers,
        use_moe=args.use_moe
    ))

    model.load_state_dict(torch.load(ckp, map_location=args.device), strict=True)
    print(f'NanoQwen预训练模型参数量: {sum(p.numel() for p in model.parameters() if p.requires_grad) / 1e6:.2f}M(illion)')
    return model.eval().to(args.device), tokenizer


def get_prompt_datas():
    # 预训练模型的文本接龙测试（无法对话）
    prompt_datas = [
        '今天天气很好，',
        '人工智能技术正在',
        '中国的传统文化包括',
        '科学研究表明，',
        '在计算机科学中，',
        '地球是太阳系中',
        '人类的神经系统由',
        '数学是一门研究',
        '环境保护对于人类',
        '经济发展需要',
        '教育的重要性在于',
        '健康的生活方式包括',
        '互联网改变了',
        '文学作品能够',
        '音乐艺术可以',
        '体育运动有助于',
        '科技创新推动',
        '社会进步需要',
        '文化传承是',
        '自然界的规律'
    ]
    return prompt_datas


# 设置可复现的随机种子
def setup_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def main():
    parser = argparse.ArgumentParser(description="Test NanoQwen Pretrained Model")
    parser.add_argument('--out_dir', default='out', type=str)
    parser.add_argument('--temperature', default=0.85, type=float)
    parser.add_argument('--top_p', default=0.85, type=float)
    parser.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu', type=str)
    # 模型配置参数
    # NanoQwen2-moe (145M)：(hidden_size=640, num_hidden_layers=8, use_moe=True)
    # NanoQwen2-Small (26M)：(hidden_size=512, num_hidden_layers=8)
    # NanoQwen2 (104M)：(hidden_size=768, num_hidden_layers=16)
    parser.add_argument('--hidden_size', default=512, type=int)
    parser.add_argument('--num_hidden_layers', default=8, type=int)
    parser.add_argument('--max_seq_len', default=512, type=int)
    parser.add_argument('--use_moe', default=False, type=bool)
    args = parser.parse_args()

    model, tokenizer = init_model(args)

    prompts = get_prompt_datas()
    test_mode = int(input('[0] 自动测试\n[1] 手动输入\n'))
    streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    for idx, prompt in enumerate(prompts if test_mode == 0 else iter(lambda: input('👶: '), '')):
        setup_seed(random.randint(0, 2048))
        # setup_seed(2025)  # 如需固定每次输出则换成【固定】的随机种子
        if test_mode == 0: 
            print(f'👶: {prompt}')

        # 预训练模型使用简单的文本接龙格式
        new_prompt = tokenizer.bos_token + prompt

        inputs = tokenizer(
            new_prompt,
            return_tensors="pt",
            truncation=True
        ).to(args.device)

        print('🤖️: ', end='')
        generated_ids = model.generate(
            inputs["input_ids"],
            max_new_tokens=args.max_seq_len,
            num_return_sequences=1,
            do_sample=True,
            attention_mask=inputs["attention_mask"],
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            streamer=streamer,
            top_p=args.top_p,
            temperature=args.temperature
        )

        response = tokenizer.decode(generated_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        print('\n\n')


if __name__ == "__main__":
    main()
