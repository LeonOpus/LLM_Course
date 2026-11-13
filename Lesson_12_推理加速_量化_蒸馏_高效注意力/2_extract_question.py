import json
import os
from pprint import pprint
from llm import gpt_a,extract_llm_interview_questions
from tqdm import tqdm
from tqdm import tqdm
import concurrent.futures
from typing import List, Optional, Dict, Any # 引入更多类型提示

OUTPUT_FILENAME = 'extracted_llm_questions.json' # 输出的 JSON 文件名
NUM_THREADS = 16  # 设置要使用的线程数
filename = 'search_contents_2025-04-16_1.json'                # 替换为你的 JSON 文件名

# 读取 JSON 文件
with open(filename, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 输出读取的数据
# pprint(data[20])

merge_text=[]
for text in tqdm(data):
    qas=text["content_text"]
    merge_text.append(qas)
    
print(len(merge_text))
    
    
# --- 多线程处理 ---
final_results: List[str] = [] # 用于收集所有提取到的问题

# 使用 ThreadPoolExecutor 来管理线程
print(f"开始使用 {NUM_THREADS} 个线程并行处理文本...")
with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
    # executor.map 会将 merge_text 中的每个元素传递给 extract_llm_interview_questions 函数
    # 它会自动将任务分配给线程池中的线程，并按输入顺序返回结果
    results_iterator = executor.map(extract_llm_interview_questions, merge_text)

    # 使用 tqdm 包装迭代器以显示进度
    # total=len(merge_text) 告诉 tqdm 总共有多少个任务
    # desc 参数提供进度条的描述
    for result in tqdm(results_iterator, total=len(merge_text), desc="提取LLM问题", unit="文本"):
        # extract_llm_interview_questions 可能返回 None (出错) 或列表 (可能为空)
        if result is not None and isinstance(result, list):
            # 使用 extend 将找到的问题列表（即使是空列表）合并到最终结果中
            final_results.extend(result)
        # 如果 result is None，表示函数内部可能出错了（函数应该已经打印了错误信息）
        # 我们在这里可以选择不额外打印信息，或者添加计数器
        # elif result is None:
        #     pass # 静默处理错误

# --- 输出和保存最终结果 ---
print(f"\n处理完成！总共提取到 {len(final_results)} 个 LLM 相关问题。")

# print("\n提取到的问题预览 (前 20 条):")
# pprint(final_results[:20]) # 打印前20条预览

print(f"\n正在将结果保存到 {OUTPUT_FILENAME}...")
try:
    # 使用 'w' 模式打开文件（如果文件存在则覆盖）
    # ensure_ascii=False 确保中文字符能正确写入，而不是被转义
    # indent=2 使 JSON 文件格式化，更易读
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as outfile:
        json.dump(final_results, outfile, indent=2, ensure_ascii=False)
    print(f"结果已成功保存到 {OUTPUT_FILENAME}")
except IOError as e:
     print(f"错误：无法写入文件 {OUTPUT_FILENAME}。请检查权限或路径。错误信息: {e}")
except Exception as e:
    print(f"保存结果时发生未知错误: {e}")