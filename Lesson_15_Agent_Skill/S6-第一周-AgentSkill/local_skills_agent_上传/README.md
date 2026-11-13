# Local Agent Skills

基于阿里sdk的本地 Agent Skills 实现，通过 Anthropic SDK 兼容接口调用。

## 环境变量配置

运行前需要设置以下环境变量：

| 变量名 | 说明 |
|--------|------|
| `DASHSCOPE_API_KEY` | 阿里百炼平台 API Key（必需） |
| `DASHSCOPE_BASE_URL` | 百炼服务 Base URL（必需） |

API Key 获取方式：登录 [阿里云百炼平台](https://bailian.console.aliyun.com/)，在「API-KEY管理」中创建。

**macOS / Linux：**

```bash
export DASHSCOPE_API_KEY="sk-xxx"
export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

如需永久生效，将上述命令添加到 `~/.bashrc` 或 `~/.zshrc` 中，然后执行 `source ~/.zshrc`。

**Windows（PowerShell）：**

```powershell
$env:DASHSCOPE_API_KEY="sk-xxx"
$env:DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

```

## 安装

```bash
pip install -r requirements.txt
```

## 运行

### Web UI（推荐）

```bash
python web_app.py
```

启动后在浏览器打开 http://localhost:5080 即可使用。

Web UI 支持：
- 多模型切换（Qwen3-Max / Kimi K2.5 / GLM-5 / Qwen3-Coder-Plus）
- 实时查看 Agent 每一步的推理过程（SSE 流式输出）
- 查看生成的文件和图片

### 命令行

```bash
# 列出本地 Skill
python local_skills_agent.py list

# 测试（数据分析）
python local_skills_agent.py test

# 自由提问
python local_skills_agent.py "你的请求"
```

## 添加自定义 Skill

在 `skills/` 下创建目录，包含 `SKILL.md`：

```
skills/
└── my-skill/
    └── SKILL.md    # 必须包含 YAML frontmatter（name + description）
```
