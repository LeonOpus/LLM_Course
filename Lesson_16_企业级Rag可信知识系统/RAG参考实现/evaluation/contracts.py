"""纯数据契约与证据召回计分。它们不判断自然语言答案是否正确。"""
from collections import Counter
import math,re

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
def evidence_recall(required_groups, retrieved_evidence_ids):
    """每个必需信息组计一次；组内可有等价原文。无正例证据时为None。"""
    if not required_groups:return None
    found=set(retrieved_evidence_ids)
    return sum(bool(found.intersection(g['any_of'])) for g in required_groups)/len(required_groups)

def validate_dataset(cases, taxonomy, registry, evidence_index, complete=False):
    errors=[];seen_ids=set();seen_questions=set();atom_splits={};families=registry['families'];atoms=registry['atoms']
    def err(case,msg):errors.append(f"{case.get('case_id','?')}: {msg}")
    task_ids={x['id'] for x in taxonomy['primary_tasks']};formats={x['id'] for x in taxonomy['primary_source_format_targets']}
    for case in cases:
        missing=set(taxonomy['per_case_required_fields'])-case.keys()
        missing|={k for k in ['target_fact_ids','related_fact_family_ids','evidence_groups','scope_documents','smoke'] if k not in case}
        if missing:err(case,'missing fields '+','.join(sorted(missing)));continue
        ident=case['case_id'];question=re.sub(r'\s+','',case['question']).casefold()
        if not re.fullmatch(r'Q\d{3}',ident):err(case,'invalid case_id')
        if ident in seen_ids:err(case,'duplicate case_id')
        if not question or question in seen_questions:err(case,'empty or duplicate question')
        seen_ids.add(ident);seen_questions.add(question)
        if case['primary_task'] not in task_ids:err(case,'invalid primary_task')
        if case['primary_source_format'] not in formats:err(case,'invalid primary format')
        for key in ['source_formats','layout_challenges','evidence_span','query_styles','expected_behavior','difficulty']:
            dim=taxonomy['dimensions'][key];value=case[key];values=value if dim['cardinality']=='one_or_more' else [value]
            if not isinstance(values,list) or not values or any(x not in dim['values'] for x in values):err(case,'invalid taxonomy '+key)
            elif len(values)!=len(set(values)):err(case,'duplicate tags '+key)
        if case['primary_source_format'] not in case['source_formats']:err(case,'primary format absent from source formats')
        split=case['split'];related=[case['fact_family_id'],*case['related_fact_family_ids']]
        if split not in ['development','holdout']:err(case,'invalid split')
        if type(case['smoke']) is not bool or (case['smoke'] and split!='development'):err(case,'smoke must be development boolean')
        for family in related:
            if family not in families or families[family]['split']!=split:err(case,'family split mismatch')
        if not case['target_fact_ids']:err(case,'no target facts')
        for atom_id in case['target_fact_ids']:
            visited=set();atom=atom_id
            while atom in atoms and atoms[atom].get('alias_of'):
                if atom in visited:err(case,'atom alias cycle');break
                visited.add(atom);atom=atoms[atom]['alias_of']
            if atom not in atoms:err(case,'unknown target atom');continue
            owner=atoms[atom]['family_id']
            if owner not in related or families.get(owner,{}).get('split')!=split:err(case,'target atom split/owner mismatch')
            if atom in atom_splits and atom_splits[atom]!=split:err(case,'canonical target atom crosses splits')
            atom_splits[atom]=split
        points=case['gold_answer_points']
        if not points or len({x.get('id') for x in points})!=len(points) or any(not x.get('text') or type(x.get('required')) is not bool for x in points):err(case,'invalid answer rubric')
        evidences=case['gold_evidence'];eids=[e.get('evidence_id') for e in evidences]
        if len(eids)!=len(set(eids)):err(case,'duplicate evidence')
        for evidence in evidences:
            expected=evidence_index.get(evidence.get('evidence_id'))
            if not expected:err(case,'unknown evidence');continue
            for field in ['document_id','document_version','source_hash','locator']:
                if evidence.get(field)!=expected.get(field):err(case,'evidence mismatch '+field)
            if not evidence.get('evidence_text_or_fact') or type(evidence.get('required_for_answer')) is not bool:err(case,'incomplete evidence label')
            if expected['format'] not in case['source_formats']:err(case,'source format omitted')
            if expected['document_id'] not in case['scope_documents']:err(case,'evidence outside reviewed scope')
        groups=case['evidence_groups'];gids=[g.get('id') for g in groups]
        if len(gids)!=len(set(gids)):err(case,'duplicate evidence group')
        required={e['evidence_id'] for e in evidences if e.get('required_for_answer')};in_groups=set()
        for group in groups:
            options=group.get('any_of',[])
            if not options or len(options)!=len(set(options)) or not set(options)<=required:err(case,'invalid evidence group alternatives')
            in_groups.update(options)
        if required!=in_groups:err(case,'required evidence groups do not match evidence labels')
        if case['expected_behavior'] in ['answer','calculate_with_evidence'] and not groups:err(case,'answer requires positive evidence')
        if case['expected_behavior'] in ['refuse_insufficient_evidence','ask_clarification'] and (not case['missing_information'] or not case['scope_documents']):err(case,'negative/clarification needs missing info and review scope')
        if case['primary_task']=='T06' or case['expected_behavior']=='calculate_with_evidence':
            numeric=case['scoring_method'].get('numeric_checks',[])
            if not numeric:err(case,'numeric case needs checks')
            for check in numeric:
                if not check.get('unit') or not check.get('calculation') or type(check.get('expected')) not in [int,float] or not math.isfinite(check.get('expected',float('nan'))) or type(check.get('absolute_tolerance')) not in [int,float] or check.get('absolute_tolerance',-1)<0:err(case,'numeric check needs finite target, unit, calculation and tolerance')
        if case['primary_task']=='T04':
            visual=case.get('visual_dependency',{})
            if visual.get('status')!='verified' or not visual.get('required_region') or not visual.get('why_text_alone_insufficient'):err(case,'visual case needs dependency audit')
            anchors=visual.get('audited_evidence_ids',[])
            if not isinstance(anchors,list) or not anchors or any(a not in required for a in anchors):err(case,'visual audit must reference required gold evidence')
        if case['review_status'] not in ['draft','source_checked_by_author','independently_reviewed']:err(case,'invalid review status')
        if not isinstance(case['conversation_history'],list):err(case,'history must be a list')
    if complete:
        if len(cases)!=taxonomy['total_cases']:errors.append('complete dataset requires 200 cases')
        counts=Counter(c['split'] for c in cases)
        for split in ['development','holdout']:
            if counts[split]!=taxonomy['splits'][split]:errors.append('split quota mismatch '+split)
        if sum(c.get('smoke') is True for c in cases)!=taxonomy['splits']['smoke_subset_of_development']:errors.append('smoke quota mismatch')
        for task in taxonomy['primary_tasks']:
            for split in ['development','holdout']:
                if sum(c['primary_task']==task['id'] and c['split']==split for c in cases)!=task[split]:errors.append('task quota mismatch '+task['id']+'/'+split)
        for fmt in taxonomy['primary_source_format_targets']:
            if sum(c['primary_source_format']==fmt['id'] for c in cases)!=fmt['count']:errors.append('format quota mismatch '+fmt['id'])
        if any(c.get('review_status')=='draft' for c in cases):errors.append('unreviewed cases remain')
    return errors
