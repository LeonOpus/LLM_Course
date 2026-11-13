"""一条文档记录一个 JSON；SQLite 负责提交与重启后的保存。"""
import json
import time
from contextlib import contextmanager
from rag_app.core import transition
import sqlite3
from pathlib import Path

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class Store:
    def __init__(self, root):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.db=self.root/'documents.sqlite3'
        with self.connect() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS documents (doc_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
    @contextmanager
    def connect(self):
        conn=sqlite3.connect(self.db,timeout=15)
        try:
            with conn:yield conn
        finally:conn.close()
    def get(self,doc_id):
        with self.connect() as conn:
            row=conn.execute('SELECT payload FROM documents WHERE doc_id=?',(doc_id,)).fetchone()
        if row is None: raise KeyError(doc_id)
        return json.loads(row[0])
    def put(self,doc):
        with self.connect() as conn:
            conn.execute('INSERT OR REPLACE INTO documents VALUES (?,?)',(doc['doc_id'],json.dumps(doc,ensure_ascii=False)))
    def list(self):
        with self.connect() as conn: rows=conn.execute('SELECT payload FROM documents ORDER BY rowid DESC').fetchall()
        return [json.loads(row[0]) for row in rows]
    def directory(self,doc_id):
        self.get(doc_id)  # 外部 ID 必须先匹配已登记的文档，不能拼任意路径。
        return self.root/'documents'/doc_id

    def create(self,doc_id,name,kind,sha256):
        item={'doc_id':doc_id,'name':name,'kind':kind,'extension':Path(name).suffix.lower(),
              'sha256':sha256,'status':'uploaded','stage':'upload','block_count':0,'chunk_count':0,
              'error':None,'created_at':time.time()}
        try:
            with self.connect() as conn:
                conn.execute('INSERT INTO documents VALUES (?,?)',(doc_id,json.dumps(item,ensure_ascii=False)))
        except sqlite3.IntegrityError:raise ValueError('文档编号已存在，不能覆盖') from None
        return item
    def move(self,doc_id,target,**fields):
        if fields.keys()-{'error','chunk_count','block_count','stage','parser_options','indexed_at'}:
            raise ValueError('不能通过状态接口修改原件身份')
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row=conn.execute('SELECT payload FROM documents WHERE doc_id=?',(doc_id,)).fetchone()
            if row is None:raise KeyError(doc_id)
            item=json.loads(row[0]);item['status']=transition(item['status'],target)
            item.update(fields);item['updated_at']=time.time()
            conn.execute('UPDATE documents SET payload=? WHERE doc_id=?',(json.dumps(item,ensure_ascii=False),doc_id))
        return item
