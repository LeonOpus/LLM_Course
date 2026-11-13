import pytest
from rag_app.visual import request_body,observation_blocks
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
PNG=b'\x89PNG\r\n\x1a\nfixture'

def test_relation_prompt_is_opt_in_image_and_parameters_unchanged():
 a=request_body(PNG,'fixture');b=request_body(PNG,'fixture',prompt_version='visual-relations-m24-v2')
 assert a['messages'][1]==b['messages'][1] and a['messages'][0]!=b['messages'][0]
 assert {k:v for k,v in a.items() if k!='messages'}=={k:v for k,v in b.items() if k!='messages'}
 with pytest.raises(ValueError):request_body(PNG,'fixture',prompt_version='unknown')

def test_new_observation_identity_pins_prompt_version():
 region={'doc_id':'d','region_id':'r','source_sha256':'a'*64,'image_sha256':'b'*64,'locator':{'kind':'pdf','page':1,'block_id':'b'}}
 obs={'observations':[{'context':'图','text':'左框指向右框','uncertain':False}],'warnings':[]}
 a=observation_blocks(region,obs,'fixture');b=observation_blocks(region,obs,'fixture',prompt_version='visual-relations-m24-v2')
 assert a[0]['text']==b[0]['text'] and a[0]['locator']['block_id']!=b[0]['locator']['block_id']
 assert b[0]['metadata']['semantic_verified'] is False
