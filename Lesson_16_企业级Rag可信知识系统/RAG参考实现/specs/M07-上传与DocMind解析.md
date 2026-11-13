# M07 / 上传、解析任务与原始结果

## 用户故事

作为不了解后端的新手，我要选择一份文件，分别看见上传和解析状态，查看解析文本，下载原文核对；失败时知道检查哪里，不把上传或任务接受当成成功。

## 范围与接口

保留M05健康检查。新增以下接口，默认本机8000，前端5173代理/api。

| 接口 | 成功 | 关键失败 |
|---|---|---|
| POST /api/documents，multipart字段file | 201，doc_id/name/kind/status=uploaded | 空文件400；不支持415；超过教学50MB上限413 |
| GET /api/documents | 200，数组，包含持久化status/error/block_count | 不能用预设数组替代真实元数据 |
| POST /api/documents/{doc_id}/parse | 202，accepted=true与同一doc_id | 未知404；处理中或已解析冲突409 |
| GET /api/documents/{doc_id}/blocks | 200，文本块数组 | 未知404；未产出结果409 |
| GET /api/documents/{doc_id}/source | 原始文件字节 | 未知404 |

PDF、Word、Excel、PPT、图片、HTML、MD、TXT使用DocMind，CSV用UTF-8原生读取。上传扩展名白名单不等于已验证文件内容，更不等于复杂版式解析质量通过。页码转换和表格辅助函数为给定教学底座，5.8继续核验其语义边界。

## 状态和持久化

正常：uploaded → parsing → parsed。异常：uploaded/parsing → failed；恢复：failed → parsing → parsed。仅解析不产生向量、不连接Milvus、不调用百炼，不能出现ready。

SQLite保留元数据；runtime/documents/{doc_id}/source.ext保存原件，blocks.json保存统一块。云解析的docmind子目录保存job.json、status.json、分页result-*.json与layouts.json；SDK响应只在本机runtime，不写入公开截图和提交记录。

DocMind提交一次后保存job_id；查询失败用同一任务恢复。无任务号的提交异常记录submission-uncertain.json，不自动重发。源SHA或增强设置改变不能复用旧任务。官方异步接口状态Success/success成功，Fail失败；读取时不区分大小写，兼容failed。分页offset累加实际layout数，直到不足请求数量，不能只下载第一页。

## 验收

- AC-03：上传201仍是uploaded；空文件/不支持扩展名拒绝；原件下载与上传字节一致；重启后状态存在。
- AC-04-local：固定SDK测试覆盖提交、恢复、分页、源变化、选项变化、不确定提交、Fail终态。固定响应只证明程序行为。
- AC-04-live：学生实际上传一份课程PDF和一份Office分别调用DocMind，保存真实任务/响应，状态parsed，逐页抽查文本与原文；无真实调用时必须写pending。
- 前端不能把202改写成“解析成功”，必须继续读取文档列表；状态刷新失败明确显示上次结果可能过期。
- 完成M05已有测试，新增M07后端20项（含M05健康2项）、前端14项（含M05健康7项）与构建；本数量是参考包契约，不是对所有可能错误的覆盖承诺。

## SDD → TDD步骤

继续编辑5.4建立的specs/tasks.json、specs/api-contract.md、specs/acceptance.json。AC-04保持原编号，在additional_checks区分AC-04-local和AC-04-live；未调用真实服务时总项保持pending。本地验收拆开记录HTTP上传与浏览器文件选择上传，不能相互替代。选择文件后须点击“上传文件”，上传与解析是两次操作。

先阅读本规格和tests；准备可导入的接口壳；运行测试记录缺失功能；每次实现一个小段，再运行相同测试；最后真实浏览器走上传/解析/原文核对。参考起始/完成包用于回放，不是学生原创过程的证明。

## 服务边界

“离线解析”是提问前的文档处理阶段，DocMind仍需联网。202只表示本机接受任务；测试里的临时客户端会等待后台函数完成，这不等于真实浏览器也同步等待。

本节单进程BackgroundTasks和SQLite支持本机教学；它们不是高可用任务队列。进程被关闭后需要恢复已保存的任务。5.9才引入向量入库，5.11才开始模型基线评价。
