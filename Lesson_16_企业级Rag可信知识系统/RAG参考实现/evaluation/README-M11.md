# M11 评估工具与复核字段

本目录的 runtime.py / reporting.py 只使用 Python 标准库。教师的完整 evaluation/tests 另有 PDF/PPT 原件核验测试，需要教师固定运行时；学生 M11 包只含32项运行器/报告测试。

## 输入输出

- run读取materials/m06/development.jsonl和package.json。smoke从开发集选择smoke=true；拒绝holdout与draft。
- 所有题共享整套登记语料，按原件SHA绑定运行时doc_id。额外ready文档、同一原件重复ready、缺失原件都拒绝。不要为某道题指定它的gold scope。
- 写入新的运行目录，保存cases.json、corpus.json、documents-before/after.json、manifest.json、records.jsonl、summary.json。
- manifest记录config、题集/语料/记录指纹、实际trace中的模型/提示版本/上下文预算/向量配置。中途变化或缺信息则comparable=false。
- 本版run中三次连续请求失败后停止，后面的题标not_run。没有自动重试；修复后用新运行目录。
- report和compare重新读取冻结记录并检查指纹，不能直接编辑summary.json制造成绩。指纹用于发现意外改动，不是防恶意篡改的数字签名。

## 复核JSON的约定

true=确认通过，false=确认未通过，null=尚未确认。必须写真正核对后的reason，不能整份替换null。

| 字段 | 核对内容 |
|---|---|
| reviewer.kind/name | human或model_assisted及复核者；模型辅助结果显示provisional_model_assisted |
| record_sha256 | 自动生成的逐题记录指纹；答案变动后重新复核 |
| behavior.correct | 回答/拒答/澄清是否符合题意；程序还会检查返回status |
| points[].passed | 对照gold_answer_points逐条评估，true时answer_quote必须是答案原文 |
| critical_errors[].present | 是否出现关键错误；true会让答案判错，需答案摘录 |
| numeric_checks[] | name对应数值规则；通过时填observed数值、unit单位、answer_quote摘录，程序核对容差 |
| retrieval_groups/context_groups | 按每个必需证据组判断；任何组仍null，本题该层召回率保持未知 |
| citations[].supported | 这条实际引用能否支持答案中的主张，须给答案摘录和证据摘录 |
| citation_complete.complete | 所有应有依据的主张是否都有足够引用；编号存在不等于完整 |

必需证据组命中的links示例（编号仅为结构示意）：

```json
{
  "group_id": "g1",
  "found": true,
  "reason": "同一版本原件，指定表格的型号、数值和单位均被保留",
  "links": [{
    "evidence_id": "e1",
    "chunk_ids": ["c1"],
    "source_quote": "X100功率180W",
    "retrieved_quote": "X100功率180W"
  }]
}
```

程序检查组成员、片段存在、来源文档/原件SHA、摘录存在。跨片段时chunk_ids按实际证据顺序填写，retrieved_quote在用换行拼接后的文本中匹配。这些结构检查不能代替人工判断是否同一行、同一适用条件、同一图。尤其视觉题必须看指定原图，不能仅因数字相同就通过。found=false需要已检查完整候选的理由；没看完用null。

## 分母与边界

- answer_accuracy是“已复核子集正确率”，同时显示n/total/pending。接口失败未进入语义复核，留在pending，并另外显示execution_counts；不能把这部分藏起来声称端到端成功率。
- evidence recall先算每题的必需证据组命中比例，再对已确认题宏平均。无正例组为不适用，不计为1。
- 没有任何引用时citation_precision不适用；应回答的题缺引用不能据此通过RAG成功检查。
- compare只统计两侧都已确认的配对题，逐题列gain/regression/unchanged/pending。样本不完整时不能把子集差值当完整题集提升。
- 模型辅助评分尚未接入实际百炼调用。本版用人工复核JSON；AI编程助手可整理格式与提出建议，不能假称已独立人工确认。
- tokens只汇总回答响应已返回的total_tokens；不代表Embedding、重排、DocMind、裁判的总用量。cost保持null，直到有实际费率及完整调用用量。
- 单次报告为HTML，原compare输出精简JSON。M11B增加应用内评估面板：用tools/export_comparison_view.py导出带轨迹的比较文件后导入；更多分层分析与真实效果仍待后续实验。
