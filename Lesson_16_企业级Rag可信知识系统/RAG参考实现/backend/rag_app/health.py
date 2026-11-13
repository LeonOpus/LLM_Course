"""M15A：只公开配置元数据；不把Key存在冒充服务可连接。"""
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def public_health(settings,formats):
    return {'status':'ok','service':'rag-backend','configured':settings.configured(),'verification':'configuration_only',
            'supported_extensions':sorted(formats),'strategies':['baseline','rerank'],
            'index_configuration':{'chunk_strategy':settings.chunk_strategy,'collection':settings.milvus_collection},
            'context_configuration':{'context_policy':settings.context_policy},
            'query_configuration':{'retrieval_mode':settings.retrieval_mode,'query_rewrite':settings.query_rewrite,
                                   'generation_policy':settings.generation_policy},
            'models':{'chat':settings.chat_model,'embedding':settings.embedding_model,'dimension':settings.embedding_dim}}
