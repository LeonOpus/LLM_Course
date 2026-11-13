"""离线验证 Flask/SSE 与课程 Skill 读取；不会调用外部模型。"""
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

root=Path(__file__).resolve().parent.parent
project=root/'S6-第一周-AgentSkill'/'local_skills_agent_上传'
sys.path.insert(0,str(project))
os.environ['DASHSCOPE_API_KEY']='local-demo-placeholder'
os.environ['DASHSCOPE_BASE_URL']='http://127.0.0.1:9'
import web_app

calls=[]
def model_response(**kwargs):
    calls.append(kwargs)
    if len(calls)==1:
        block=SimpleNamespace(type='tool_use',name='read_file',id='tool-1',input={'file_path':str(project/'skills'/'data-analysis'/'SKILL.md')})
        return SimpleNamespace(stop_reason='tool_use',content=[block])
    result=kwargs['messages'][-1]['content'][0]
    assert result['tool_use_id']=='tool-1'
    assert 'data-analysis' in json.loads(result['content'])['content']
    return SimpleNamespace(stop_reason='end_turn',content=[SimpleNamespace(type='text',text='模拟完成')])
def events(response):
    return [json.loads(line[6:]) for line in response.data.decode().splitlines() if line.startswith('data: ')]
with tempfile.TemporaryDirectory(prefix='lesson15-') as temp, patch.object(web_app,'OUTPUT_DIR',Path(temp)), patch.object(web_app.client.messages,'create',side_effect=model_response):
    response=web_app.app.test_client().post('/run',json={'prompt':'请读取数据分析技能'})
    result=events(response); types=[e['type'] for e in result]
    assert response.status_code==200 and 'tool_call' in types and 'tool_result' in types and types[-1]=='done' and len(calls)==2
    print('模拟 Skill 加载和工具结果回传：通过；事件：',', '.join(types))
with tempfile.TemporaryDirectory(prefix='lesson15-') as temp, patch.object(web_app,'OUTPUT_DIR',Path(temp)), patch.object(web_app.client.messages,'create',side_effect=RuntimeError('模拟连接失败')):
    response=web_app.app.test_client().post('/run',json={'prompt':'验证错误处理'})
    types=[e['type'] for e in events(response)]
    assert types[-2:]==['error','done']
    print('模型失败后结束 SSE：通过；最后事件：',types[-2:])
