from copy import deepcopy
import pytest
from rag_app.visual_selection import select_observations
from rag_app.visual import digest
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
OBS=[{'context':'x','text':'图中写DRAIN','uncertain':False},{'context':'x','text':'图中写DRAN','uncertain':False}]
PACKET={'bundle_sha256':'a'*64,'result':{'observations':{'observations':OBS}}}
def review():return {'schema_version':'visual-observation-selection/1','bundle_sha256':'a'*64,'reviewer':{'kind':'model_assisted','name':'test'},'rows':[{'index':i,'observation_sha256':digest(x),'decision':'retain' if i==0 else 'exclude','reason':'与原图核对：保留原件一致的观察，排除错字'} for i,x in enumerate(OBS)]}
def test_selection_preserves_original_text_and_packet():
 before=deepcopy(PACKET);indices,meta=select_observations(PACKET,review())
 assert indices==[0] and PACKET==before and meta['reviewer_kind']=='model_assisted'
@pytest.mark.parametrize('change',['wrong_bundle','wrong_observation','duplicate','missing','all_excluded'])
def test_invalid_selection_is_rejected(change):
 r=review()
 if change=='wrong_bundle':r['bundle_sha256']='b'*64
 if change=='wrong_observation':r['rows'][0]['observation_sha256']='b'*64
 if change=='duplicate':r['rows'][1]=deepcopy(r['rows'][0])
 if change=='missing':r['rows'].pop()
 if change=='all_excluded':r['rows'][0]['decision']='exclude'
 with pytest.raises(ValueError):select_observations(PACKET,r)

def test_warning_selection_is_bound_and_can_exclude_all_without_editing_raw():
 p=deepcopy(PACKET);p['result']['observations']['warnings']=['没有单位']
 r=review();r['warnings']=[{'index':0,'warning_sha256':digest('没有单位'),'decision':'exclude','reason':'原图标明元；原模型警告错误。'}]
 _,meta=select_observations(p,r)
 assert meta['retained_warning_indices']==[] and p['result']['observations']['warnings']==['没有单位']
 r['warnings'][0]['warning_sha256']='b'*64
 with pytest.raises(ValueError):select_observations(p,r)
