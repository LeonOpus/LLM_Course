import os
import sys
import json
import asyncio
from typing import AsyncGenerator, Dict, Any
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="NanoQwen Pretrain API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
model = None
tokenizer = None

class ChatRequest(BaseModel):
    message: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512

class ChatResponse(BaseModel):
    response: str
    status: str = "success"

def load_model():
    """加载vLLM模型"""
    global model, tokenizer
    
    print("正在加载NanoQwen预训练模型...")
    
    # 加载tokenizer
    tokenizer = AutoTokenizer.from_pretrained('./model/')
    
    # 加载vLLM模型
    model = LLM(
        model="./out/",  # 使用本地模型路径
        trust_remote_code=True,
        tensor_parallel_size=1,  # 根据GPU数量调整
        gpu_memory_utilization=0.8,
        max_model_len=2048,
        dtype="bfloat16"
    )
    
    print("模型加载完成！")

@app.on_event("startup")
async def startup_event():
    """启动时加载模型"""
    load_model()

@app.get("/")
async def root():
    return {"message": "NanoQwen Pretrain API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": model is not None}

async def generate_stream(prompt: str, temperature: float, top_p: float, max_tokens: int) -> AsyncGenerator[str, None]:
    """流式生成文本"""
    try:
        # 设置采样参数
        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=True
        )
        
        # 使用vLLM生成
        outputs = model.generate([prompt], sampling_params)
        
        for output in outputs:
            for token in output.outputs[0].token_ids:
                # 解码token
                decoded_token = tokenizer.decode([token], skip_special_tokens=True)
                if decoded_token:
                    yield f"data: {json.dumps({'token': decoded_token, 'finished': False})}\n\n"
        
        # 发送完成信号
        yield f"data: {json.dumps({'token': '', 'finished': True})}\n\n"
        
    except Exception as e:
        error_msg = f"生成过程中出现错误: {str(e)}"
        yield f"data: {json.dumps({'error': error_msg, 'finished': True})}\n\n"

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口"""
    # 构建预训练模型的输入格式
    prompt = f"<|im_start|>user\n{request.message}<|im_end|>\n<|im_start|>assistant\n"
    
    return StreamingResponse(
        generate_stream(
            prompt=prompt,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens
        ),
        media_type="text/plain"
    )

@app.post("/chat")
async def chat(request: ChatRequest):
    """非流式聊天接口"""
    try:
        # 构建预训练模型的输入格式
        prompt = f"<|im_start|>user\n{request.message}<|im_end|>\n<|im_start|>assistant\n"
        
        # 设置采样参数
        sampling_params = SamplingParams(
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens,
            stream=False
        )
        
        # 生成回复
        outputs = model.generate([prompt], sampling_params)
        response = outputs[0].outputs[0].text
        
        return ChatResponse(response=response)
        
    except Exception as e:
        return ChatResponse(response=f"错误: {str(e)}", status="error")

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    ) 