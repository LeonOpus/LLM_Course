import json
import os
import concurrent.futures
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import logging
import time # Optional: for logging save times

# --- 配置 ---
INPUT_JSON_FILE = 'extracted_llm_questions.json' # 输入文件名
OUTPUT_JSON_FILE = 'gpt_a_processed_results.json' # 输出文件名
MAX_WORKERS = 16 # 并发线程数
SAVE_INTERVAL = 1000 # 每处理多少条数据保存一次

# --- 日志设置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')

# --- 导入你的 GPT 函数 ---
try:
    from llm import gpt_a
    logging.info("Successfully imported 'gpt_a' function from llm module.")
except ImportError:
    logging.error("Error: Could not import 'gpt_a' from 'llm.py'. Make sure the file exists and is accessible.")
    exit(1)
except AttributeError:
    logging.error("Error: Function 'gpt_a' not found within 'llm.py'.")
    exit(1)

# --- 核心处理函数 (与之前类似) ---

def load_questions(filepath: str) -> List[str]:
    """从 JSON 文件加载问题列表"""
    logging.info(f"Loading questions from: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("JSON file does not contain a list.")
        questions = [item for item in data if isinstance(item, str)]
        if len(questions) != len(data):
             logging.warning(f"Some items in the JSON list were not strings and were ignored.")
        if not questions:
             logging.warning(f"No valid string questions found in {filepath}")
             return []
        logging.info(f"Successfully loaded {len(questions)} questions.")
        return questions
    except FileNotFoundError:
        logging.error(f"Error: Input file not found at {filepath}")
        return []
    except json.JSONDecodeError:
        logging.error(f"Error: Could not decode JSON from {filepath}")
        return []
    except ValueError as ve:
        logging.error(f"Error loading questions: {ve}")
        return []

def process_single_question(question: str) -> Optional[Dict[str, str]]:
    """调用 gpt_a 处理单个问题，并处理可能的错误。"""
    if not question or not isinstance(question, str):
        logging.warning(f"Skipping invalid input item: {question!r}")
        return None
    try:
        # 调用你的 GPT 函数
        logging.debug(f"Processing question: {question[:50]}...")
        gpt_result = gpt_a(question)
        if not isinstance(gpt_result, str):
             logging.warning(f"gpt_a did not return a string for input '{question[:50]}...'. Got: {type(gpt_result)}. Skipping.")
             return None
        logging.debug(f"Successfully processed: {question[:50]}...")
        return {"input": question, "output": gpt_result}
    except Exception as e:
        # 捕获 gpt_a 执行期间可能发生的任何错误
        # 使用 False 避免打印过多重复的 Traceback，除非调试需要
        logging.error(f"Error processing question '{question[:50]}...': {e}", exc_info=False)
        return None # 返回 None 表示此问题处理失败

def save_results(results: List[Dict[str, str]], filepath: str, is_intermediate=False):
    """将结果列表保存到 JSON 文件 (覆盖)"""
    save_type = "Intermediate" if is_intermediate else "Final"
    logging.info(f"[{save_type} Save] Saving {len(results)} results to: {filepath}")
    start_time = time.time()
    try:
        # 每次都覆盖写入完整的结果列表
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        end_time = time.time()
        logging.info(f"[{save_type} Save] Successfully saved {len(results)} results in {end_time - start_time:.2f} seconds.")
    except IOError as e:
        logging.error(f"[{save_type} Save] Error saving results to {filepath}: {e}")
    except TypeError as e:
         logging.error(f"[{save_type} Save] Error: Could not serialize results to JSON: {e}")


# --- 主执行逻辑 ---
if __name__ == "__main__":
    logging.info(f"Starting concurrent processing script. Results saved every {SAVE_INTERVAL} items.")

    # 1. 加载问题
    questions_to_process = load_questions(INPUT_JSON_FILE)

    if not questions_to_process:
        logging.warning("No questions loaded or file error. Exiting.")
        exit(1)

    # 2. 使用线程池并发处理
    all_processed_results = [] # 存储所有成功的结果
    futures = [] # 存储 Future 对象
    successful_count = 0
    failed_count = 0
    total_tasks = len(questions_to_process)

    logging.info(f"Submitting {total_tasks} questions to thread pool (max_workers={MAX_WORKERS})...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        for question in questions_to_process:
            future = executor.submit(process_single_question, question)
            futures.append(future)

        logging.info(f"All {total_tasks} tasks submitted. Waiting for results...")

        # 使用 as_completed 处理完成的任务，并用 tqdm 显示进度
        # 注意：as_completed 不保证按提交顺序返回结果
        for future in tqdm(concurrent.futures.as_completed(futures), total=total_tasks, desc="Processing Questions"):
            try:
                # 获取任务结果 (如果任务中发生异常，这里会重新抛出)
                result = future.result()
                if result is not None:
                    all_processed_results.append(result)
                    successful_count += 1

                    # 检查是否达到保存间隔
                    if successful_count > 0 and successful_count % SAVE_INTERVAL == 0:
                        save_results(all_processed_results, OUTPUT_JSON_FILE, is_intermediate=True)
                else:
                    # process_single_question 返回了 None (通常是输入无效或处理时记录了警告)
                    failed_count += 1 # 可以看作是跳过或失败
            except Exception as e:
                # future.result() 抛出了在 worker 线程中未被捕获的异常
                logging.error(f"An unexpected error occurred retrieving result: {e}", exc_info=False)
                failed_count += 1

    logging.info(f"Processing loop finished. Successful: {successful_count}, Failed/Skipped: {failed_count}")

    # 3. 最后保存一次，确保所有结果都被写入
    if all_processed_results:
        # 检查自上次保存后是否有新结果
        if successful_count % SAVE_INTERVAL != 0:
             logging.info("Performing final save...")
             save_results(all_processed_results, OUTPUT_JSON_FILE, is_intermediate=False)
        else:
             logging.info("Last save interval covered all results. No separate final save needed.")
    else:
        logging.warning("No questions were successfully processed. Output file will not be created or may be empty.")

    logging.info("Script finished.")