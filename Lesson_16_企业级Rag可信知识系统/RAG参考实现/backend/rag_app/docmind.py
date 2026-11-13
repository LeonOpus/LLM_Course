"""DocMind 异步任务：提交一次、保存 job_id、轮询并完整下载布局。

联网云解析用于离线入库阶段；不是本地 OCR。原始响应仅写入 runtime，
不放进课件或版本库。提交超时不自动重试，以免重复产生付费任务。
"""
from hashlib import sha256
import inspect
import json
import re
import time
from pathlib import Path
from alibabacloud_docmind_api20220711.client import Client
from alibabacloud_docmind_api20220711 import models
from alibabacloud_tea_openapi.models import Config
from alibabacloud_tea_util.models import RuntimeOptions
from rag_app.providers import ProviderError

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def save_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(path)

def unpack(value):
    if hasattr(value,'to_map'): value=value.to_map()
    if isinstance(value,str): value=json.loads(value)
    if not isinstance(value,dict): raise ProviderError('DocMind 响应 Data 不是预期对象')
    return value

class DocMindBusinessError(ProviderError):
    pass

def check_business_error(body,cache,phase):
    """HTTP 200 can still carry a DocMind business failure; never echo Message."""
    code=body.get('Code')
    if code is None or str(code)=='200': return
    safe=str(code) if re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',str(code)) else 'unrecognized'
    save_json(cache/f'{phase}-error.json',{'phase':phase,'code':safe})
    hint='核对 RAM 用户的 DocMind 授权与服务开通状态' if safe=='NoPermission' else '按官方错误码检查服务、配额与参数'
    raise DocMindBusinessError(f'DocMind {phase} 业务错误 {safe}：{hint}；未自动重试')

class DocMind:
    def __init__(self,settings,client=None):
        if not settings.configured()['docmind']:
            raise ProviderError('缺少 DocMind AccessKey ID/Secret：它们与百炼 API Key 不同')
        self.client=client or Client(Config(
            access_key_id=settings.alibaba_cloud_access_key_id.get_secret_value(),
            access_key_secret=settings.alibaba_cloud_access_key_secret.get_secret_value(),
            security_token=settings.alibaba_cloud_security_token.get_secret_value() or None,
            endpoint=settings.docmind_endpoint,connect_timeout=15000,read_timeout=120000))

    def parse(self,path,cache_dir,enhance=False,timeout=1800):
        path=Path(path); cache=Path(cache_dir);cache.mkdir(parents=True,exist_ok=True)
        job_file=cache/'job.json'
        source_hash=sha256(path.read_bytes()).hexdigest()
        if job_file.exists():
            job=json.loads(job_file.read_text(encoding='utf-8'))
            if job.get('source_sha256') != source_hash:
                raise ProviderError('原始文件已改变：请使用新的解析缓存目录')
            if bool(job['enhance']) != bool(enhance):
                raise ProviderError('解析增强配置已改变：请建立新的解析版本，不能复用旧任务')
            job_id=job['job_id']
        else:
            if (cache/'submission-uncertain.json').exists():
                raise ProviderError('上次提交结果不确定：核对控制台任务后再人工恢复，系统不会再次付费提交')
            settings={'file_name':path.name,'llm_enhancement':enhance,'formula_enhancement':False}
            supported=inspect.signature(models.SubmitDocParserJobAdvanceRequest).parameters
            if 'output_format' in supported: settings['output_format']=['markdown','visualLayoutInfo']
            if enhance and 'enhancement_mode' in supported: settings['enhancement_mode']='VLM'
            with path.open('rb') as f:
                request=models.SubmitDocParserJobAdvanceRequest(file_url_object=f,**settings)
                try:
                    response=self.client.submit_doc_parser_job_advance(request,RuntimeOptions(autoretry=False))
                    body=unpack(response.body)
                    # Persist identifiers before interpreting Data; do not persist provider Message.
                    save_json(cache/'submission-response.json',{
                        'code':body.get('Code'),
                        'request_id':body.get('RequestId'),
                        'data':body.get('Data'),
                    })
                    check_business_error(body,cache,'submit')
                    data=unpack(body.get('Data'))
                    job_id=data.get('Id')
                    if not job_id: raise ValueError('missing id')
                except DocMindBusinessError:
                    raise
                except Exception:
                    # 无 job_id 的超时不能推断服务端未提交。保留显式不确定状态。
                    save_json(cache/'submission-uncertain.json',{'status':'unknown','action':'check_docmind_console_before_retry'})
                    raise ProviderError('DocMind 提交未获得任务号：先检查控制台，确认没有重复任务后再重试') from None
            job={'source_sha256':source_hash,'job_id':job_id,'enhance':enhance,'submitted_at':time.time(),'submitted_settings':settings,
                 'sdk_has_output_format':'output_format' in supported}
            save_json(job_file,job)
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:
                body=unpack(self.client.query_doc_parser_status(models.QueryDocParserStatusRequest(id=job_id)).body)
                check_business_error(body,cache,'query')
                data=unpack(body.get('Data'))
            except ProviderError:
                raise
            except Exception:
                raise ProviderError('DocMind 状态查询失败；已保存任务号，可恢复查询，不必再次提交文件') from None
            save_json(cache/'status.json',body)
            status=str(data.get('Status','')).lower()
            if status=='success': break
            if status in {'fail','failed'}: raise ProviderError('DocMind 解析失败：到控制台按保存的任务号查看原因')
            time.sleep(5)
        else: raise ProviderError('DocMind 仍在处理：已保存任务号，稍后恢复查询')
        layouts=[];offset=0;step=100
        while offset<100000:
            try:
                body=unpack(self.client.get_doc_parser_result(models.GetDocParserResultRequest(id=job_id,layout_num=offset,layout_step_size=step)).body)
                check_business_error(body,cache,'result')
                data=unpack(body.get('Data')); batch=data['layouts']
                if not isinstance(batch,list): raise ValueError()
            except ProviderError:
                raise
            except Exception:
                raise ProviderError('DocMind 下载结果失败：保留任务号，重试结果下载；原始结果需及时落盘') from None
            save_json(cache/f'result-{offset:06d}.json',body)
            layouts.extend(batch);offset+=len(batch)
            if len(batch)<step: break
        else: raise ProviderError('布局数量超过保护上限，检查结果分页是否重复')
        if not layouts: raise ProviderError('DocMind 成功但没有文本布局，请核对文档与解析模式')
        save_json(cache/'layouts.json',layouts)
        return layouts
