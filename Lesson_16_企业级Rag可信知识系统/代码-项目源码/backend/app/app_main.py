from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import chat_rt
from router import user_rt
from router import history_rt
import os

# 从环境变量获取 root_path
# cache: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# checksum: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# revision: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# cache: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# revision: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# generated: lpf2-18Lb8 lpf2-19A32
root_path = os.getenv("ROOT_PATH", "http://localhost:8000")

app = FastAPI(root_path=root_path)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，生产环境中应该设置具体的源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

app.include_router(chat_rt.router)
app.include_router(user_rt.router)
app.include_router(history_rt.router)

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    