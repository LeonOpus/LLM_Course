"""环境验证脚本"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 读取 .env（固定为项目根目录）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def check_python_version():
    """检查 Python 版本"""
    print("=" * 50)
    print("1. Python 版本检查")
    print("=" * 50)
    version = sys.version_info
    print(f"Python 版本: {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 10:
        print("✓ Python 版本满足要求 (>=3.10)")
        return True
    else:
        print("✗ 需要 Python 3.10 或更高版本")
        return False


def check_packages():
    """检查必要的包"""
    print("\n" + "=" * 50)
    print("2. 依赖包检查")
    print("=" * 50)

    required_packages = {
        "torch": "2.0.0",
        "transformers": "4.51.0",
        "peft": "0.13.0",
        "accelerate": "0.34.0",
        "datasets": "3.0.0",
        "openai": "1.0.0",
        "requests": "2.28.0",
    }

    all_ok = True
    for package, min_version in required_packages.items():
        try:
            module = __import__(package)
            version = getattr(module, "__version__", "unknown")
            print(f"✓ {package}: {version}")
        except ImportError:
            print(f"✗ {package}: 未安装")
            all_ok = False

    return all_ok


def check_device():
    """检查计算设备"""
    print("\n" + "=" * 50)
    print("3. 计算设备检查")
    print("=" * 50)

    import torch

    print(f"PyTorch 版本: {torch.__version__}")

    if torch.cuda.is_available():
        print(f"✓ CUDA 可用")
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        print(f"  显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        return "cuda"
    elif torch.backends.mps.is_available():
        print(f"✓ MPS (Apple Silicon) 可用")
        return "mps"
    else:
        print("⚠ 仅 CPU 可用，训练会很慢")
        return "cpu"


def check_model():
    """检查模型文件"""
    print("\n" + "=" * 50)
    print("4. 模型文件检查")
    print("=" * 50)

    model_path = "/root/autodl-tmp/qwen3_4b"

    if os.path.exists(model_path):
        print(f"✓ 模型路径存在: {model_path}")

        # 检查关键文件
        key_files = ["config.json", "tokenizer.json", "model.safetensors"]
        for f in key_files:
            fpath = os.path.join(model_path, f)
            if os.path.exists(fpath):
                size = os.path.getsize(fpath) / 1024 / 1024
                print(f"  ✓ {f}: {size:.1f} MB")
            else:
                # 检查分片文件
                if f == "model.safetensors":
                    shard_files = [x for x in os.listdir(model_path) if x.startswith("model") and x.endswith(".safetensors")]
                    if shard_files:
                        print(f"  ✓ 模型分片文件: {len(shard_files)} 个")
                    else:
                        print(f"  ⚠ {f}: 未找到")
                else:
                    print(f"  ⚠ {f}: 未找到")
        return True
    else:
        print(f"✗ 模型路径不存在: {model_path}")
        return False


def check_api_keys():
    """检查 API 密钥"""
    print("\n" + "=" * 50)
    print("5. API 密钥检查")
    print("=" * 50)

    # 博查搜索 API
    bocha_key = os.environ.get("BOCHA_API_KEY")
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY")

    if not bocha_key:
        print("✗ 缺少 BOCHA_API_KEY（请在 /root/autodl-tmp/train_project/.env 中配置）")
        return False
    if not dashscope_key:
        print("✗ 缺少 DASHSCOPE_API_KEY（请在 /root/autodl-tmp/train_project/.env 中配置）")
        return False

    print(f"✓ 博查搜索 API Key: {bocha_key[:10]}...")
    print(f"✓ DashScope API Key: {dashscope_key[:10]}...")

    # 测试博查搜索 API
    print("\n测试博查搜索 API...")
    try:
        import requests

        headers = {
            "Authorization": f"Bearer {bocha_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": "测试搜索",
            "summary": True,
            "count": 1
        }

        response = requests.post(
            "https://api.bocha.cn/v1/web-search",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                print("✓ 博查搜索 API 连接成功")
                return True
            else:
                print(f"✗ 博查搜索 API 返回错误: {data.get('msg')}")
                return False
        else:
            print(f"✗ 博查搜索 API HTTP 错误: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ 博查搜索 API 测试失败: {e}")
        return False


def check_tokenizer():
    """测试 tokenizer 加载"""
    print("\n" + "=" * 50)
    print("6. Tokenizer 加载测试")
    print("=" * 50)

    model_path = "/root/autodl-tmp/qwen3_4b"

    try:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        print(f"✓ Tokenizer 加载成功")
        print(f"  词表大小: {tokenizer.vocab_size}")
        print(f"  特殊 token: {tokenizer.special_tokens_map}")

        # 测试 apply_chat_template
        messages = [
            {"role": "system", "content": "你是助手"},
            {"role": "user", "content": "你好"}
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        print(f"✓ apply_chat_template 正常工作")
        print(f"  示例输出: {text[:100]}...")

        return True

    except Exception as e:
        print(f"✗ Tokenizer 加载失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("Deep Research Agent 环境验证")
    print("=" * 50)

    results = {
        "python": check_python_version(),
        "packages": check_packages(),
        "device": check_device(),
        "model": check_model(),
        "api": check_api_keys(),
        "tokenizer": check_tokenizer(),
    }

    print("\n" + "=" * 50)
    print("验证结果汇总")
    print("=" * 50)

    all_pass = True
    for name, result in results.items():
        status = "✓" if result else "✗"
        print(f"{status} {name}")
        if not result and name != "device":
            all_pass = False

    if all_pass:
        print("\n✓ 所有检查通过，可以开始训练！")
    else:
        print("\n✗ 部分检查未通过，请修复后再试")

    return all_pass


if __name__ == "__main__":
    main()
