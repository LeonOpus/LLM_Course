"""
数据验证脚本 V2
================

验证生成的训练数据质量，输出统计信息。
"""

import os
import sys
import json
import re
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.schema_v2 import validate_trajectory, INDUSTRIES, QUESTION_TYPES
from transformers import AutoTokenizer


def load_data(file_path: str):
    """加载 JSONL 数据"""
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def validate_all(data: list):
    """验证所有数据"""
    results = {
        "total": len(data),
        "valid": 0,
        "invalid": 0,
        "errors": defaultdict(int)
    }

    for item in data:
        is_valid, errors = validate_trajectory(item)
        if is_valid:
            results["valid"] += 1
        else:
            results["invalid"] += 1
            for err in errors:
                results["errors"][err] += 1

    return results


def compute_statistics(data: list, tokenizer=None):
    """计算数据统计信息"""
    stats = {
        "total_samples": len(data),
        "industry_dist": defaultdict(int),
        "question_type_dist": defaultdict(int),
        "step_dist": defaultdict(int),
        "tools_dist": defaultdict(int),
        "has_citation": 0,
        "token_lengths": []
    }

    for item in data:
        meta = item.get("metadata", {})

        # 行业分布
        industry = meta.get("industry", "unknown")
        stats["industry_dist"][industry] += 1

        # 问题类型分布
        q_type = meta.get("question_type", "unknown")
        stats["question_type_dist"][q_type] += 1

        # 步数分布
        steps = meta.get("num_steps", 0)
        stats["step_dist"][steps] += 1

        # 工具使用分布
        for tool in meta.get("tools_used", []):
            stats["tools_dist"][tool] += 1

        # 引用情况
        if meta.get("has_citation"):
            stats["has_citation"] += 1

        # Token 长度
        if tokenizer:
            messages = item.get("messages", [])
            total_text = ""
            for msg in messages:
                total_text += msg.get("content", "")
            tokens = tokenizer.encode(total_text)
            stats["token_lengths"].append(len(tokens))
            meta["total_tokens"] = len(tokens)

    return stats


def print_report(validation_results: dict, statistics: dict):
    """打印报告"""
    print("=" * 60)
    print("数据质量验证报告")
    print("=" * 60)

    # 验证结果
    print(f"\n总样本数: {validation_results['total']}")
    print(f"验证通过: {validation_results['valid']} ({validation_results['valid']/validation_results['total']*100:.1f}%)")
    print(f"验证失败: {validation_results['invalid']} ({validation_results['invalid']/validation_results['total']*100:.1f}%)")

    if validation_results['errors']:
        print("\n错误分布:")
        for err, count in sorted(validation_results['errors'].items(), key=lambda x: -x[1]):
            print(f"  - {err}: {count}")

    # 统计信息
    print("\n" + "=" * 60)
    print("数据分布统计")
    print("=" * 60)

    print("\n行业分布:")
    for ind, count in sorted(statistics['industry_dist'].items()):
        ind_zh = INDUSTRIES.get(ind, ind)
        pct = count / statistics['total_samples'] * 100
        print(f"  {ind_zh} ({ind}): {count} ({pct:.1f}%)")

    print("\n问题类型分布:")
    for qt, count in sorted(statistics['question_type_dist'].items()):
        qt_zh = QUESTION_TYPES.get(qt, qt)
        pct = count / statistics['total_samples'] * 100
        print(f"  {qt_zh} ({qt}): {count} ({pct:.1f}%)")

    print("\n步数分布:")
    for steps, count in sorted(statistics['step_dist'].items()):
        pct = count / statistics['total_samples'] * 100
        print(f"  {steps} 步: {count} ({pct:.1f}%)")

    print("\n工具使用统计:")
    for tool, count in sorted(statistics['tools_dist'].items(), key=lambda x: -x[1]):
        print(f"  {tool}: {count}")

    print(f"\n有引用的样本: {statistics['has_citation']} ({statistics['has_citation']/statistics['total_samples']*100:.1f}%)")

    if statistics['token_lengths']:
        lengths = sorted(statistics['token_lengths'])
        print("\nToken 长度统计:")
        print(f"  最小: {min(lengths)}")
        print(f"  最大: {max(lengths)}")
        print(f"  平均: {sum(lengths)/len(lengths):.0f}")
        print(f"  P50: {lengths[len(lengths)//2]}")
        print(f"  P90: {lengths[int(len(lengths)*0.9)]}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="数据验证脚本")
    parser.add_argument("--input", type=str, default="data/train_v2.jsonl", help="输入文件")
    parser.add_argument("--tokenizer", type=str, default=None, help="Tokenizer 路径")
    args = parser.parse_args()

    # 加载数据
    print(f"加载数据: {args.input}")
    data = load_data(args.input)

    # 验证
    print("验证中...")
    validation_results = validate_all(data)

    # 统计
    tokenizer = None
    if args.tokenizer:
        print(f"加载 tokenizer: {args.tokenizer}")
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, trust_remote_code=True)

    statistics = compute_statistics(data, tokenizer)

    # 打印报告
    print_report(validation_results, statistics)

    # 保存更新后的数据（如果计算了 token 长度）
    if tokenizer:
        output_path = args.input.replace(".jsonl", "_with_tokens.jsonl")
        with open(output_path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"\n已保存带 token 长度的数据到: {output_path}")


if __name__ == "__main__":
    main()
