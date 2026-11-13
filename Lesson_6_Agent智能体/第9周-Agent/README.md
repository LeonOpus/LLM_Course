明白了！我来把配置部分也加上去，下面是更新后的 `README.md`：

---

```markdown
# 项目环境配置说明

## 1. 创建 Conda 虚拟环境

使用 Conda 创建一个名为 `agent` 的 Python 3.10 虚拟环境：

```bash
conda create -n agent python=3.10
```

激活环境：

```bash
conda activate agent
```

## 2. 安装依赖

确保你在项目根目录下，然后运行以下命令安装依赖：

```bash
pip install -r requirements.txt
```

## 3. 配置 API 密钥

在 `websearch/config/config.yaml` 文件中，填写你的 API 密钥：

```yaml
openai_api_key: "你的OpenAI API Key"
serper_api_key: "你的Serper API Key"
```


## 4. 启动项目

依赖和密钥配置完成后，按照项目说明运行notebook即可。

