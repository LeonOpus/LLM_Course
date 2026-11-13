"""Select existing visual observations after a source review, never edit their text."""
from rag_app.visual import digest

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
def select_observations(packet,review):
    observations=packet['result']['observations']['observations']
    if (not isinstance(review,dict) or review.get('schema_version')!='visual-observation-selection/1'
        or review.get('bundle_sha256')!=packet['bundle_sha256']):raise ValueError('视觉筛选未绑定原始转写包')
    reviewer=review.get('reviewer',{})
    if reviewer.get('kind') not in {'model_assisted','human'} or not isinstance(reviewer.get('name'),str) or not reviewer['name'].strip():raise ValueError('视觉筛选缺少复核身份')
    rows=review.get('rows')
    if not isinstance(rows,list) or len(rows)!=len(observations):raise ValueError('视觉筛选须覆盖每条原始观察')
    seen=set();selected=[]
    for row in rows:
        index=row.get('index')
        if type(index) is not int or index in seen or not 0<=index<len(observations):raise ValueError('视觉筛选序号无效或重复')
        seen.add(index)
        if row.get('observation_sha256')!=digest(observations[index]):raise ValueError('原观察指纹已改变')
        if row.get('decision') not in {'retain','exclude'} or not isinstance(row.get('reason'),str) or not row['reason'].strip():raise ValueError('视觉筛选决定或理由无效')
        if row['decision']=='retain':
            if observations[index]['uncertain']:raise ValueError('不能将uncertain观察提升为确定事实')
            selected.append(index)
    if not selected:raise ValueError('筛选后没有可用观察，不能入库')
    meta={'review_sha256':digest(review),'reviewer_kind':reviewer['kind'],'semantic_verified':False}
    if 'warnings' in review:
        warnings=packet['result']['observations'].get('warnings',[]);wr=review['warnings'];seen=set();keep=[]
        if not isinstance(wr,list) or len(wr)!=len(warnings):raise ValueError('警告筛选须覆盖全部原始警告')
        for row in wr:
            i=row.get('index')
            if type(i) is not int or i in seen or not 0<=i<len(warnings):raise ValueError('警告序号无效或重复')
            seen.add(i)
            if row.get('warning_sha256')!=digest(warnings[i]):raise ValueError('警告指纹不匹配')
            if row.get('decision') not in {'retain','exclude'} or not isinstance(row.get('reason'),str) or not row['reason'].strip():raise ValueError('警告筛选决定或理由无效')
            if row['decision']=='retain':keep.append(i)
        meta['retained_warning_indices']=sorted(keep)
    return sorted(selected),meta
