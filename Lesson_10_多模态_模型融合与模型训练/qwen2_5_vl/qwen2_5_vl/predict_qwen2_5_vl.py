"""本地 Qwen2.5-VL 图文推理：默认使用课程图片和本机已有模型。"""
import argparse
from pathlib import Path

import torch
from qwen_vl_utils import process_vision_info
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='/home/leon/Model/ModelScope/Qwen/Qwen2.5-VL-7B-Instruct')
    parser.add_argument('--image', default=str(HERE / 'coco_2014_caption/294574.jpg'))
    parser.add_argument('--question', default='请描述图片中主要物体以及它所处的场景。')
    parser.add_argument('--max-new-tokens', type=int, default=128)
    args = parser.parse_args()
    if not Path(args.image).is_file():
        parser.error('图片文件不存在')
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        args.model, dtype=torch.bfloat16, device_map='auto', local_files_only=True
    ).eval()
    processor = AutoProcessor.from_pretrained(args.model, local_files_only=True,
                                               min_pixels=256*28*28, max_pixels=512*28*28)
    messages = [{'role':'user','content':[{'type':'image','image':args.image},
                                         {'type':'text','text':args.question}]}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    images, videos = process_vision_info(messages)
    inputs = processor(text=[text], images=images, videos=videos, padding=True, return_tensors='pt')
    print('输入形状:', {k: tuple(v.shape) for k,v in inputs.items() if hasattr(v,'shape')}, flush=True)
    if 'image_grid_thw' in inputs:
        print('图像网格 (T,H,W):', inputs['image_grid_thw'].tolist(), flush=True)
    inputs = inputs.to(model.device)
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False)
    response = processor.batch_decode(generated[:, inputs.input_ids.shape[1]:],
                                      skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    print('模型回答:', response, flush=True)


if __name__ == '__main__':
    main()
