# RAG 实操课 · 参考实现

这是课程做完之后应该长成的样子：一个能把业务资料读进知识库、按问题找出依据、逐句标出处、还能量化自己好坏的设备知识库系统。

**它只是参考。** 你可以只读代码，可以跑起来点一点，也可以完全不看、自己按 26 步做一遍。怎么用由你决定。只是有一句话值得先说：照着抄一遍，和自己踩过坑再做出来，面试时能讲出来的东西差很远。这门课真正的产出是你的规格、你的基线报告和你那份「改了什么、哪些题变好、哪些题变差」的复盘，这些抄不来。

包里只有源码和配置，没有依赖、没有运行数据、没有业务资料。业务资料在你下载的材料包里。

---

## 一、先装四样东西

和课程第 2 节一样。已经装过就跳过。

| 工具 | 用途 | 验证 |
|---|---|---|
| uv + Python 3.12 | 后端 | `uv --version`、`uv python install 3.12` |
| Node.js 20 以上 | 前端 | `node --version` |
| Docker Desktop | 跑 Milvus 向量库 | `docker version` 要同时有 Client 和 Server |
| 阿里云账号 | 百炼 + DocMind | 见下面第三步 |

Windows 用 PowerShell，命令同 macOS，只有安装方式不同。

## 二、装依赖

解压后进入 `RAG参考实现/` 目录。

```bash
cd backend && uv sync --frozen --python 3.12 && cd ..
cd frontend && npm ci && cd ..
```

Windows 的 npm 要写成 `npm.cmd ci`。

## 三、配密钥

```bash
cp .env.example .env
```

用编辑器打开 `.env`，填三个值：

| 变量 | 从哪来 |
|---|---|
| `DASHSCOPE_API_KEY` | 阿里云百炼控制台的 API Key 页面 |
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | 阿里云 RAM 用户的 AccessKey |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | 同上，只显示一次 |

百炼 Key 和 DocMind 的 AccessKey 是两套东西，不能互填。RAM 用户要挂 `AliyunDocmindFullAccess` 策略，DocMind 的「文档解析（大模型版）」要先开通，否则会返回 HTTP 200 但业务码 `NoPermission`。

`.env` 不要提交、不要贴进任何对话框。

## 四、起 Milvus

在 `RAG参考实现/` 目录：

```bash
docker compose -f infra/compose.yaml up -d --wait --wait-timeout 240
docker compose -f infra/compose.yaml ps
```

应看到 `etcd`、`minio`、`milvus` 三个都是 healthy。首次拉镜像要几分钟。

停：`docker compose -f infra/compose.yaml stop`。**不要加 `-v`**，那会删掉数据卷。

## 五、起服务

两个终端，各自保持开着。

终端一，后端：

```bash
uv run --directory backend --frozen uvicorn rag_app.main:app --host 127.0.0.1 --port 8000
```

终端二，前端：

```bash
cd frontend
RAG_API_TARGET=http://127.0.0.1:8000 npm run dev -- --port 5173 --strictPort
```

Windows PowerShell 的环境变量写法：`$env:RAG_API_TARGET="http://127.0.0.1:8000"; npm.cmd run dev -- --port 5173 --strictPort`

浏览器打开 **http://127.0.0.1:5173**。

## 六、先确认三件事都通

打开左侧「环境检查」。配置存在、连得上、调用成功是三件不同的事，页面分开显示。

- 后端进程：`http://127.0.0.1:8000/api/health` 返回 `status: ok`。这只说明进程在。
- Milvus：`http://127.0.0.1:8000/api/services/milvus` 的 `reachable` 为 true。首次 `collection_exists` 是 false，第一次入库才会建。
- 百炼和 DocMind：各发一次最小请求再下结论。

## 七、走一遍完整链路

1. **知识库** → 选材料包里 `02-知识库资料/工单记录与咨询/D34-售后工单记录.csv` → 上传 → 仅解析。CSV 走本地解析，不花钱，8 行变 8 块。
2. 同一页 → 预览切块 → 开始入库。这一步调百炼算向量，开始计费。
3. **检索调试** → 问「WO-004 是什么型号」，top_k 填 5 → 只看候选，不生成答案。
4. **知识问答** → 问同一个问题 → 看回答、右侧引用、点开引用看原文。
5. 再传一份 PDF（比如 `产品手册与选型/D01-X100产品与运行手册.pdf`），走 DocMind 解析，观察状态从「解析中」变成「已解析」。
6. **质量评估** → 导入评估运行器导出的比较 JSON，看七个指标和逐题差异。

空知识库时提问应该明确回答「现有资料不足以确认」，不会编。这是设计，不是故障。

## 八、跑测试

```bash
cd backend && uv run --frozen pytest          # 后端
cd frontend && npm test                        # 前端
```

## 九、包里有什么

| 路径 | 内容 |
|---|---|
| `backend/rag_app/` | 上传、DocMind 解析、多格式定位、切块、向量化、Milvus 入库、检索、生成、引用校验、用量记录 |
| `backend/tests/` | 后端测试，可当作行为说明来读 |
| `frontend/src/` | 五个页面：知识问答、知识库、检索调试、质量评估、环境检查 |
| `evaluation/` | 评估运行器与评分：七个指标、证据组召回、逐题比较 |
| `specs/` | 需求、架构、接口契约、12 条验收 |
| `tools/` | Milvus 连通检查、评估入口等脚本 |
| `infra/compose.yaml` | Milvus 三件套 |
| `.env.example` | 配置模板 |

**不在包里**：Python 和 Node 依赖（按第二步装）、业务资料（在材料包里）、运行数据和历史实验记录、课程讲义。

## 十、关键参数在哪

默认是课程最后一轮的配置，不是起点配置：

| 参数 | 值 | 位置 |
|---|---|---|
| 向量模型 | `text-embedding-v4`，1024 维 | `.env` |
| 生成模型 | `qwen-plus`，temperature 0 | `.env` |
| 候选数 / 最终上下文 | 30 / 最多 15 | 前端请求与 `.env` |
| 上下文正文预算 | 30000 字符 | `.env` 的 `CONTEXT_MAX_CHARS` |

课程里从 10 / 5 / 6000 起步，到后面才对照这组更大的配置。想复现课程的基线，把这三个数改回去。

## 十一、卡住了怎么查

| 现象 | 先看哪里 |
|---|---|
| 页面打不开 | 后端是否在跑；端口 5173 是否被占 |
| 页面显示请求失败 | 后端终端有没有报错；代理是否指向 8000 |
| `connection refused` 19530 | Docker 没起，或 milvus 容器还在启动中 |
| DocMind 返回 NoPermission | RAM 用户没挂策略，或服务没开通 |
| 向量维度不一致 | `.env` 的维度和已建集合不一致，换个集合名重建 |
| 入库一半失败 | 状态应是 failed 不是 ready，看后端日志定位是哪一批 |

把不含密钥的报错原文交给编程助手定位，不要凭猜测改配置。

---

本课程的设备、公司、工单和政策均为教学虚构，不能用于真实设备的选型、接线或维修。
