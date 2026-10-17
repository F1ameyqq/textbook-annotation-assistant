"""Build a separate, unverified source-region draft; cached by default."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from prepare_content_revision_b import _read,local_path
from annotation.recognition.baseline import file_digest,load_source


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('layout','crop','legacy','canvas','roles','evidence','graph','base-check','review','previous','out'):
        p.add_argument('--'+name,type=local_path,required=True)
    p.add_argument('--answer-id',required=True)
    p.add_argument('--source',type=local_path,action='append',required=True)
    p.add_argument('--observations',type=local_path)
    p.add_argument('--runs',type=local_path,help='replay an existing source-bound pixel plan')
    p.add_argument('--collect',action='store_true',help='explicit new local CPU OCR of body and whole-row fallback')
    a=p.parse_args(argv)
    if a.collect==bool(a.observations):p.error('choose exactly --collect or --observations')
    if a.out.exists():p.error('output directory already exists; preserve earlier trials')
    from PIL import Image
    from annotation.recognition.region_runs import plan_region_runs
    from annotation.recognition.region_ocr import collect_region_observations,validate_region_observations
    from annotation.recognition.region_draft import build_region_draft,make_region_draft_plan
    from annotation.recognition.content_revision import apply_content_revision,build_content_quality,reference
    from annotation.recognition.content_revision_quality import audit_content_application,audit_content_quality
    watched={}
    def watch(path,sha):
        path=Path(path).resolve()
        if path in watched and watched[path]!=sha:raise ValueError('source or input has conflicting expected bytes')
        watched[path]=sha
    def read_input(path):
        value,sha=_read(path);watch(path,sha)
        return value
    def check_inputs():
        if any(file_digest(path)!=sha for path,sha in watched.items()):raise ValueError('source or input changed while preparing draft')
    layout,legacy,canvas,roles,e,g,c,r,previous=[read_input(getattr(a,k)) for k in ('layout','legacy','canvas','roles','evidence','graph','base_check','review','previous')]
    cached=read_input(a.observations) if a.observations else None
    plan=read_input(a.runs) if a.runs else cached['payload']['plan_archive'] if cached else None
    if plan is not None and (plan['payload']['layout_archive']!=layout or plan['payload']['layout_ref']!=reference(layout)):
        raise ValueError('plan layout differs from explicit layout')
    source=layout['payload'];assets={}
    watch(a.crop,source['crop_sha256'])
    for manifest in a.source:
        snapshot=read_input(manifest)
        doc,members=load_source(manifest)
        if doc!=snapshot:raise ValueError('source manifest changed while loading')
        if doc['book_id']!=layout['book_id']:raise ValueError('source belongs to another book')
        for asset,path in members:
            if asset['asset_id'] in assets:raise ValueError('duplicate source asset')
            assets[asset['asset_id']]=(asset,path);watch(path,asset['sha256'])
    check_inputs()
    asset,path=assets[source['asset_id']]
    if (asset['sha256']!=source['source_sha256'] or [asset['width'],asset['height']]!=source['source_size']):raise ValueError('original source differs from layout')
    with Image.open(path) as original,Image.open(a.crop) as crop:
        tile=original.convert('RGB').crop(source['crop_bbox'])
        if tile.size!=crop.size or tile.tobytes()!=crop.convert('RGB').tobytes():raise ValueError('original crop pixels differ')
    if plan is None:plan=plan_region_runs(layout,a.crop)
    check_inputs()
    a.out.mkdir(parents=True)
    def save(name,value):
        with (a.out/(name+'.json')).open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
    save('runs',plan)
    obs=collect_region_observations(plan,a.crop) if a.collect else cached
    save('observations',obs)
    audit=validate_region_observations(plan,obs,a.crop)
    save('observation-check',audit)
    if audit['payload'].get('accepted') is not True:raise ValueError('source observation audit rejected')
    draft=build_region_draft(plan,obs,legacy,canvas,roles,a.crop)
    save('draft',draft)
    from annotation.recognition.region_report import render_region_report
    (a.out/'report.html').write_text(render_region_report(draft,a.crop),encoding='utf-8')
    author=dict(kind='SYNTHETIC_TEST' if draft['producer']['execution_kind']=='SYNTHETIC_TEST' else 'MODEL_DRAFT',id='automatic-region-observations',note='Deterministic first draft from recorded source OCR and derived formula candidates; no reference transcription consumed; not human approved.')
    revision=make_region_draft_plan(e,g,c,draft,answer_id=a.answer_id,previous_plan=previous,author=author,crop_path=a.crop)
    app=apply_content_revision(e,g,c,revision);check=build_content_quality(e,g,c,revision,app,r)
    app_audit=audit_content_application(e,g,c,revision,app);qa=audit_content_quality(e,g,c,revision,app,r,check)
    if not app_audit['payload']['accepted'] or not qa['payload']['accepted']:raise ValueError('content projection rejected')
    check_inputs()
    values={'content-plan':revision,'application':app,'graph':app['payload']['graph'],'check':check,'application-audit':app_audit,'quality-audit':qa}
    summary=dict(decision='HOLD',complete=False,transcription_verified=False,business_acceptance=False,platform_actions=[],
        mode='NEW_LOCAL_CPU' if a.collect else 'CACHED_OBSERVATIONS',new_model_calls=sum(len(u['variants']) for u in obs['payload']['units']) if a.collect else 0,
        declared_runs=len(obs['payload']['units']),body_slots=len(plan['payload']['body_slots']),rows=len(draft['payload']['rows']),fractions=len(draft['payload']['fractions']),
        derived_compositions=sum(len(f['composed_candidates']) for f in draft['payload']['fractions']),
        graph_ref=reference(app['payload']['graph']),quality_ref=reference(check),plan_ref=reference(revision),
        source_pixels_equal=True,inputs_unchanged=True,issues=len(check['payload']['issues']))
    for name,value in {**values,'summary':summary}.items():
        save(name,value)
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print(json.dumps(dict(decision='HOLD',complete=False,error=dict(type=type(exc).__name__,message=str(exc)[:700]),platform_actions=[]),ensure_ascii=False),flush=True)
        raise SystemExit(1)
