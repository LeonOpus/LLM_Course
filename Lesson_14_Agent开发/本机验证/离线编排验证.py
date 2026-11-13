"""验证课程编排与并发流程；模型和搜索都是本地模拟，不调用外部 API。"""
import json
import sys
import threading
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deep_research import orchestrator as o, workers as w
from deep_research.tools import LLMResponse, SearchResponse, SearchResult

plan = {'query_type': {'type': 'breadth_first'}, 'worker_count': {'recommended': 2},
        'subtasks': [{'id': 'a', 'name': '市场', 'description': '市场概况', 'search_queries': ['市场']},
                     {'id': 'b', 'name': '技术', 'description': '技术概况', 'search_queries': ['技术']}],
        'report_structure': {}}
class LeadLLM:
    def __init__(self): self.n = 0
    def chat(self, **kwargs):
        results = [json.dumps(plan, ensure_ascii=False), '# 模拟研究报告\n两项子任务已汇总。', json.dumps({'overall_score': 90})]
        result = results[self.n]; self.n += 1
        return LLMResponse(content=result, model='mock')
class WorkerLLM:
    def chat(self, **kwargs):
        return LLMResponse(content=json.dumps({'task_id':'mock', 'summary':'模拟来源', 'key_findings':[], 'confidence_level':'low'}, ensure_ascii=False), model='mock')
barrier = threading.Barrier(2)
class Search:
    def search(self, query):
        barrier.wait(timeout=5)
        return SearchResponse(query=query, results=[SearchResult(title='示例', url='https://example.org/source', snippet='仅用于本地测试。')])
events = []
with patch.object(o, 'get_llm_client', return_value=LeadLLM()), \
     patch.object(w, 'get_llm_client', side_effect=WorkerLLM), \
     patch.object(w, 'get_search_client', side_effect=Search), \
     patch.dict(o.AGENT_CONFIG, {'min_iterations':1, 'max_iterations':1, 'quality_threshold':80}), \
     patch.object(w.time, 'sleep', return_value=None):
    state = o.Orchestrator(worker_factory=w.SearchWorker, max_workers=2,
                           on_progress=lambda stage, data: events.append(stage)).run('模拟调研')
assert state.status == 'completed', state.error_msg
assert len(state.worker_results) == 2
assert all(len(result['ooda_cycles']) == 1 for result in state.worker_results)
assert state.quality_score == 90
print('通过：两个 Worker 并行、各执行一次 OODA、汇总报告并完成质量检查。')
print('分数和报告都是模拟值；过程事件：', ', '.join(events))
