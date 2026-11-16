# 项目 01：大模型推理部署与测试

这是一个以**推理部署和测试交付**为目标的个人实践：在单张 NVIDIA GPU 上启动本地 Qwen 模型，检查 API 的功能和异常处理，再用流式请求对比不同并发下的首字延迟、每输出 token 平均时间和吞吐。

本次项目由 Codex 协助编写脚本、执行并整理结果；适合跟着复现和学习，不能直接当作本人独立开发经历。这里的数据来自本机测试，不代表客户现场、昇腾 NPU 或生产服务。

## 交付物

- [跟着做：一次完整测试交付练习](docs/跟着做_实训任务.md)
- [测试方案与指标口径](docs/测试方案.md)
- [测试报告与结果分析](docs/测试报告.md)
- [问题排查记录](docs/问题排查记录.md)
- [逐请求原始结果](results/)：每次执行都有 `requests.jsonl`、`summary.json` 和 `gpu.csv`。
- [API 测试](tests/test_api.py)和[压测脚本测试](tests/test_benchmark.py)。
- [环境与模型指纹](results/20261116_environment.json)。不包含模型权重；需要自行准备。

## 本次环境与已知范围

- 硬件：1 × RTX 3090，24 GiB 显存；NVIDIA 驱动 560.35.03。
- 模型：本地 Qwen2.5-1.5B-Instruct；服务使用 FP16、最大上下文 1024、eager 模式，显存利用率配置 0.45。
- 模型服务：服务器现有的 `2026_vllm-test` 环境，pip 包元数据为 vLLM 0.6.3，但模块版本字符串为 `dev`，因此不能把它视作已经验证过的标准发行版。PyTorch 2.4.0+cu121。
- 测试客户端：现有 `llm-course` Python 环境的 `httpx` 和 `pytest`，并非 vLLM 官方 benchmark。
- vLLM 仅绑定本机端口 `127.0.0.1:18101`，不需要云 API。它没有配置鉴权，不应直接对公网开放。
- 此环境的原版 vLLM 提前绑定所有网卡，项目启动脚本对指定端口作本地绑定修正；这并不意味着所有 vLLM 版本都有这个问题。启动后务必用 `ss` 检查。
- 当前项目仅在上述机器和开发环境上验证；没有验证容器部署、昇腾、多卡、高可用、长期稳定性和精度评估。

## 从头复现

本机分别使用两个现有 conda 环境。若在其他机器使用，需先建立自己的兼容环境并准备模型；**不要默认依赖或绝对路径在其他机器存在**。

### 1. 启动服务

在第一个终端：

```bash
cd /home/leon/GitHub/LLM_Course/Project_01_LLM推理部署与测试
/home/leon/miniconda3/envs/2026_vllm-test/bin/python scripts/serve_loopback.py \
  --model /home/leon/Model/ModelScope/Qwen/Qwen2.5-1.5B-Instruct --port 18101
```

等待日志显示启动完成，另开终端确认端口只监听 `127.0.0.1:18101`，并检查健康接口：

```bash
ss -ltn | grep ':18101'
curl --noproxy '*' -fsS http://127.0.0.1:18101/health
```

如果端口不是 127.0.0.1，立即按 Ctrl+C 停止服务，不要继续使用。模型首次加载可能需要等待。结束后在服务终端按 Ctrl+C，再检查端口已释放。

### 2. 接口测试

```bash
/home/leon/miniconda3/envs/llm-course/bin/python -m pytest tests -q
```

其中 6 项测试需要启动本地服务：健康、模型列表、普通生成、流式生成、不存在的模型、非法生成长度；另 3 项测试压测脚本的百分位和流式错误处理，不依赖实际服务。

### 3. 测试并发

每次结果目录必须是新目录，防止误覆盖旧数据：

```bash
/home/leon/miniconda3/envs/llm-course/bin/python scripts/benchmark.py \
  --concurrency 2 --requests 24 --warmup 2 --output-tokens 48 \
  --output-dir results/my_c2_run1
```

把 `--concurrency` 分别改为 1、2、4，并保持其他条件一致。脚本只接受本地 HTTP 地址；它通过流式响应请求服务器返回 token 使用量。TTFT 取客户端收到第一个非空文本块的时间，TPOT 用 `(E2E − TTFT) / (输出 token 数 − 1)` 估算，具体边界和限制见测试方案。

## 目录

```text
configs/    参数样例
scripts/    本地安全启动、压测、环境记录
tests/      接口和脚本测试
results/    本次原始结果和环境记录
docs/       方案、报告、问题复盘
```
