from pathlib import Path
from typing import Literal
from pydantic import SecretStr,Field,field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[2]
class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_file=ROOT/'.env',env_file_encoding='utf-8',extra='ignore')
    bailian_base_url:str='https://dashscope.aliyuncs.com/compatible-mode/v1'
    chat_model:str='qwen-plus'
    vision_model:str='qwen3-vl-plus'
    libreoffice_bin:str=''
    libreoffice_fontconfig:str=''
    embedding_model:str='text-embedding-v4'
    embedding_dim:int=Field(default=1024,gt=0)
    milvus_uri:str='http://127.0.0.1:19530'
    milvus_token:SecretStr=SecretStr('')
    milvus_full_text:bool=False
    query_rewrite:Literal['off','contextual']='off'
    source_scope:Literal['off','explicit']='off'
    generation_policy: Literal['baseline','evidence_ledger','complete_answer','bounded_answer']='baseline'
    context_max_chars:int=Field(default=30000,ge=1,le=120000,strict=True)
    context_policy: Literal['baseline','parent_section']='baseline'
    retrieval_mode:Literal['dense','bm25','hybrid']='dense'
    rerank_url:str=''
    rerank_model:str='gte-rerank-v2'
    chunk_strategy:Literal['baseline','table_rows','table_context','multipage_rows','multipage_context']='baseline'
    milvus_collection:str='rag_course_chunks_v1'
    runtime_dir: Path=ROOT/'runtime'
    dashscope_api_key: SecretStr=SecretStr('')
    alibaba_cloud_access_key_id: SecretStr=SecretStr('')
    alibaba_cloud_access_key_secret: SecretStr=SecretStr('')
    alibaba_cloud_security_token: SecretStr=SecretStr('')
    docmind_endpoint: str='docmind-api.cn-hangzhou.aliyuncs.com'
    @field_validator("context_max_chars",mode="before")
    @classmethod
    def parse_context_budget(cls,value):
        if isinstance(value,str) and value.strip().isascii() and value.strip().isdecimal():return int(value.strip())
        return value

    def configured(self):
        return {'bailian':bool(self.dashscope_api_key.get_secret_value()),'docmind':bool(self.alibaba_cloud_access_key_id.get_secret_value() and self.alibaba_cloud_access_key_secret.get_secret_value()),'rerank':bool(self.dashscope_api_key.get_secret_value() and self.rerank_url)}
