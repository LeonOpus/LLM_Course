<!-- LPV2:cmFnL1JBRy0wNC3pobnnm67mupDnoIEuemlw:3cd5caae56f9d19974f0bda3620ed6ab44785444bb65d17f9ab002bd10fc807c:rel-k1:HCDNHSA5DLULKGU5EW3JQEHRGE:cb13ef709f4b00a8c6ccc9db55bae1b5 -->
# 后端启动

cd backend

## 步骤1：需下载nltk包，修改docker-compose.yml文件中nltk的挂载路径

## 步骤2：修改.env文件中 DASHSCOPE_API_KEY

## 启动后端服务
docker compose up -d --build

查看后端日志：docker logs -f swxy_api


# 前端启动

cd frontend

npm install
npm run dev

# 访问服务
http://localhost:5181/





