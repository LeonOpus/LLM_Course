import csv
import base64
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from openai import OpenAI  # 确保安装 openai

# Initialize OpenAI client
client = OpenAI(api_key="")  # ← 填你的API KEY

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Function to label the image
def label_image(image_path):
    try:
        base64_image = encode_image(image_path)
        response = client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "用贴吧暴躁老哥的语气描述一下这张图，不超过200字"},
                        {"type": "input_image", "image_url": f"data:image/jpeg;base64,{base64_image}"},
                    ],
                }
            ],
        )
        return response.output_text
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None
    
# 注意！⚠️，在你的实际的使用场景当中，在调用了牛逼的多模态模型之后，一定要加以人工的校验，有了只一步之后，在一个特定的领域，你就能得到一个比gpt、gemini这些牛逼的模型咋在你的特定领域表现更好的model

# Read the CSV and get image paths
def read_image_paths(csv_path):
    image_paths = []
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            image_paths.append(row['image_path'])
    return image_paths

# Save results to a new CSV
def save_results(results, output_csv_path):
    with open(output_csv_path, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['image_path', 'caption'])  # Header
        for image_path, caption in results:
            writer.writerow([image_path, caption])

# Main function
def main(input_csv_path, output_csv_path):
    image_paths = read_image_paths(input_csv_path)
    results = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(label_image, path): path for path in image_paths}
        # tqdm包裹 as_completed，实时显示进度
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing images"):
            path = futures[future]
            try:
                caption = future.result()
                if caption is not None:
                    results.append((path, caption))
                else:
                    results.append((path, "Error generating caption"))
            except Exception as e:
                print(f"Exception for {path}: {e}")
                results.append((path, "Exception occurred"))

    save_results(results, output_csv_path)
    print(f"✅ Finished! Saved to {output_csv_path}")

# Example usage
if __name__ == "__main__":
    input_csv = "./coco-2024-dataset.csv"    # 输入你的CSV路径
    output_csv = "gpt_labeled_dataset_copy.csv"  # 输出的新CSV路径
    main(input_csv, output_csv)
