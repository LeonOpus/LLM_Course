"""Generate the human-readable experiment report from checked-in raw summaries."""
import csv
import json
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
results=ROOT/'results'
rows=[]
for concurrency in (1,2,4):
    for repeat in (1,2,3):
        directory=results/f'20261116_confirm_c{concurrency}_r{repeat}'
        data=json.loads((directory/'summary.json').read_text(encoding='utf8'))
        if data['concurrency']!=concurrency or data['requests']!=24 or data['success']+data['failed']!=24:
            raise ValueError('结果数量或参数与测试方案不一致: '+str(directory))
        with (directory/'gpu.csv').open(encoding='utf8',newline='') as f:
            samples=list(csv.DictReader(f))
        mem=[int(x['memory_used_mib']) for x in samples if x['memory_used_mib'].isdigit()]
        rows.append({'repeat':repeat,'peak_sample_mib':max(mem) if mem else None,**data})

for item in rows:
    if item['ttft_ms']['n']!=item['success'] or item['tpot_ms']['n']!=item['success']:
        raise ValueError('本次报告要求所有成功请求均有 TTFT 与 TPOT')

lines=['# 单卡 Qwen 推理部署与测试报告','',
'## 1. 结论与边界','',
'本次在一张 RTX 3090 上启动本地 Qwen2.5-1.5B-Instruct，完成 API 功能测试与固定并发的客户端流式测试。并发 1、2、4 各重复 3 次；每次 24 个请求，正式复测合计 216 个请求。',
'以下数字只适用于本次硬件、模型、版本、短输入、48 token 上限及客户端脚本；不是客户数据、线上 SLA、模型质量评分或昇腾结果。', '',
'## 2. 环境与测试条件','',
'- 1 × RTX 3090 24 GiB，驱动 560.35.03；模型 Qwen2.5-1.5B-Instruct，权重与配置 SHA256 见 [环境记录](../results/20261116_environment.json)。',
'- 现有 vLLM 环境的包元数据为 0.6.3，模块版本显示 `dev`；PyTorch 2.4.0+cu121。FP16，max model length 1024，GPU memory utilization 0.45，eager，prefix caching 关闭。',
'- 实际监听 127.0.0.1:18101；每次预热 2 次，6 条短中文问题循环，max output 48，temperature 0；闭环并发，按 1→2→4 循环三轮。',
'- 执行了 6 项真实 API 测试和 3 项压测脚本单元测试，最终均通过。详细测试及 500 排障见 [问题排查记录](问题排查记录.md)。', '',
'## 3. 每次复测结果','',
'| 并发 | 轮次 | 成功/请求 | 平均 TTFT ms | 平均 TPOT ms | E2E P95 ms | 输出吞吐 token/s | 采样显存峰值 MiB |',
'|---:|---:|---:|---:|---:|---:|---:|---:|']
for d in rows:
    mem=str(d['peak_sample_mib']) if d['peak_sample_mib'] is not None else '未采到'
    lines.append(f"| {d['concurrency']} | {d['repeat']} | {d['success']}/{d['requests']} | {d['ttft_ms']['mean']:.2f} | {d['tpot_ms']['mean']:.2f} | {d['e2e_ms']['p95']:.2f} | {d['output_throughput_tokens_s']:.2f} | {mem} |")
lines += ['', '平均值和 P95 是每次测试内成功请求的统计；显存峰值是 0.5 秒抽样看到的整卡显存，并包含预热，不能视为进程独占显存或精确峰值。每轮仅 24 个请求，P95 不适合代表长期线上长尾。','',
'## 4. 对照观察','']
for c in (1,2,4):
    group=[r for r in rows if r['concurrency']==c]
    mean=lambda key:statistics.mean(r[key] for r in group)
    ttft=statistics.mean(r['ttft_ms']['mean'] for r in group)
    tpot=statistics.mean(r['tpot_ms']['mean'] for r in group)
    throughput=mean('output_throughput_tokens_s')
    prompt=statistics.mean(r['prompt_tokens']['mean'] for r in group)
    output=statistics.mean(r['output_tokens']['mean'] for r in group)
    lines.append(f'- 并发 {c}：三轮平均 TTFT {ttft:.2f} ms，TPOT {tpot:.2f} ms，输出吞吐 {throughput:.2f} token/s；平均输入 {prompt:.2f} token、输出 {output:.2f} token。')
lines += ['', '在这组短请求实验中，并发增大时总输出吞吐提高，同时首个可见文本块的平均等待也增加。吞吐和延迟是不同指标，变化方向不必一致；这些数据本身不能证明 GPU、调度器或通信是瓶颈，也不能推断更高并发下仍保持同样趋势。', '',
'## 5. 数据质量与限制','',
'- 正式复测前另有一组 9 次探索测试：期间采集模型权重指纹与部分测试时间重叠，因此保留在 `results/20261116_c*_r*`，未作为上表结论依据。正式复测开始前指纹采集已完成。',
'- 固定的 6 条问题会重复出现；输入长度较短，输出上限 48，且只是闭环测试；不能代表长上下文、不同到达速率或真实线上混合业务。',
'- TTFT 指首次非空文本块，不保证首 token；TPOT 以客户端 E2E 和服务端输出 token 数近似计算，包含结束信号开销。SSE 可能一次返回多个 token。详见 [测试方案](测试方案.md)。',
'- 单独请求模型解释 KV Cache 时，返回内容错误地将其说成缓存模型参数与输入以减少加载时间；见 `results/20261116_sample_response.json`。这只是一个人工核查样例，不是系统性精度评估。',
'- 没有进行性能 profiling、质量评估、长时间稳定性测试或负载均衡/多卡/NPU 实验；无法据此声称性能已经优化或定位了性能根因。',
'- 本次项目脚本由 Codex 协助设计和执行。若用于简历，应区分本人理解、复现及后续独立完成的部分。', '',
'## 6. 原始记录','',
'每次目录包含 `summary.json`、`requests.jsonl`、`gpu.csv`，测试环境、模型文件摘要以及一次 pilot 同在 [results](../results/) 中。运行命令、失败处理、统计口径详见 [测试方案](测试方案.md) 和项目 [README](../README.md)。','']
(ROOT/'docs'/'测试报告.md').write_text('\n'.join(lines),encoding='utf8')
print('测试报告已生成。')
