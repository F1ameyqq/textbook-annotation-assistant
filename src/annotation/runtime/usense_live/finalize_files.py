"""Local immutable file binding for finalize.py. No browser or network calls."""
import copy
import hashlib
import json
from pathlib import Path
from . import finalize as f
from . import insertion as i
from . import update as u

def _metadata_same(left,right):
    """Only local process metadata permits different serialization key order.

    Never use this for platform responses, plans, receipts, or native captures.
    """
    kwargs={'sort_keys':True,'ensure_ascii':False,'separators':(',',':'),'allow_nan':False}
    return json.dumps(left,**kwargs)==json.dumps(right,**kwargs)

def _ref(path):
    p=Path(path).resolve()
    u.require(p.is_file(),'EVIDENCE_FILE_MISSING',str(p))
    return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def _read_ref(ref):
    u.require(type(ref) is dict and set(ref)=={'path','sha256'} and Path(ref['path']).is_absolute(),
        'ABSOLUTE_IMMUTABLE_EVIDENCE_REF_REQUIRED')
    p=Path(ref['path'])
    u.require(_ref(p)['sha256']==ref['sha256'],'EVIDENCE_RAW_FILE_CHANGED',str(p))
    return u.loads(p.read_bytes())

def load_full_directory(path):
    root=Path(path)
    names=list(i.GLOBAL_KEYS)+[f'q{n}_{suffix}' for n in range(1,24) for suffix in i.SUFFIXES]
    full={name:u.loads((root/(name+'.json')).read_bytes()) for name in names}
    return i.load_full_capture(full,count=23)

def verify_audit_manifest(manifest,required_refs):
    u.require(manifest.get('schema')=='UsenseIndependentInsertAuditManifest/v1' and
        manifest.get('status')=='VERIFIED','INDEPENDENT_RAW_AUDIT_NOT_VERIFIED')
    u.require(type(manifest.get('files')) is list and bool(manifest['files']), 'FULL_RAW_AUDIT_MANIFEST_REQUIRED')
    records={}
    for row in manifest['files']:
        u.require(type(row) is dict and set(row)=={'path','sha256','role'} and Path(row['path']).is_absolute(),
            'AUDIT_MANIFEST_ORIGINAL_FILE_RECORD_REQUIRED')
        u.require(_ref(row['path'])['sha256']==row['sha256'],'AUDIT_ORIGINAL_FILE_CHANGED',row['path'])
        u.require(row['path'] not in records or records[row['path']]==row['sha256'], 'AUDIT_CONFLICTING_FILE_HASH')
        records[row['path']]=row['sha256']
    for role,ref in required_refs.items():
        # Later outer acceptance and its manifest cannot be self-hashed. The
        # aggregate host/index files are separately bound and checked by sender.
        if role in ('outer_acceptance','audit_manifest','reader_host_release','full_capture_index'):continue
        u.require(records.get(ref['path'])==ref['sha256'],'AUDIT_MANIFEST_MISSING_REQUIRED_ORIGINAL',role)
    return {'ok':True,'status':'AUDIT_ORIGINAL_RAW_BYTES_VERIFIED','records':len(manifest['files'])}

def load_predecessor(artifact_refs):
    u.require(type(artifact_refs) is dict and set(artifact_refs)=={'plan','receipt','comparison','outer_acceptance'},
        'FOUR_PHASE1_FILE_REFS_REQUIRED')
    objects={key:_read_ref(ref) for key,ref in artifact_refs.items()}
    outer=objects['outer_acceptance']
    execution=_read_ref(outer['evidence_refs']['writer_execution'])
    predecessor={'phase1_plan':objects['plan'],'phase1_receipt':objects['receipt'],
        'phase1_comparison':objects['comparison'],'runtime_actor_hashes':execution['runtime_actor_hashes'],
        'outer_acceptance':outer,'artifact_refs':copy.deepcopy(artifact_refs)}
    if 'observed_resolution_refs' in outer:
        refs=outer['observed_resolution_refs']
        u.require(type(refs) is dict and set(refs)=={'resolution','execution_evidence','audit_manifest'},
            'EXACT_RESOLVED_UNKNOWN_FILE_REFS_REQUIRED')
        predecessor['observed_resolution']={role:_read_ref(ref) for role,ref in refs.items()}
        predecessor['observed_resolution']['artifact_refs']=copy.deepcopy(refs)
    verify_predecessor_files(predecessor)
    return predecessor

def verify_predecessor_files(predecessor):
    mapping={'plan':'phase1_plan','receipt':'phase1_receipt','comparison':'phase1_comparison','outer_acceptance':'outer_acceptance'}
    for role,key in mapping.items():
        u.require(u.json_same(_read_ref(predecessor['artifact_refs'][role]),predecessor[key]),
            'EMBEDDED_PHASE1_ARTIFACT_CHANGED',role)
    outer=predecessor['outer_acceptance']
    evidence={role:_read_ref(ref) for role,ref in outer['evidence_refs'].items()}
    execution=evidence['writer_execution']
    u.require(u.json_same(execution['runtime_actor_hashes'],predecessor['runtime_actor_hashes']),
        'ACTOR_HASHES_NOT_FROM_REAL_PHASE1_EXECUTION')
    u.require(execution['status']==outer['writer_status'] and execution['post_attempts']==outer['post_attempts'] and
        u.json_same(execution['post_layers'],outer['post_layers']) and execution['plan_sha256']==outer['phase1_plan_sha256'] and
        execution['receipt_sha256']==predecessor['artifact_refs']['receipt']['sha256'],
        'OUTER_ACCEPTANCE_CONTRADICTS_ORIGINAL_WRITER')
    u.require(u.json_same(evidence['raw_receipt'],predecessor['phase1_receipt']) and
        u.json_same(evidence['comparison'],predecessor['phase1_comparison']), 'OUTER_RAW_ARTIFACT_MISMATCH')
    # Host/process, ledger and all raw-read captures are additionally inspected by
    # the native sender. This layer binds every original file without rewriting it.
    if 'observed_resolution' in predecessor:
        bundle=predecessor['observed_resolution']
        u.require(u.json_same(bundle['artifact_refs'],outer.get('observed_resolution_refs')),
            'RESOLUTION_REFERENCES_NOT_BOUND_BY_OUTER')
        for role,ref in bundle['artifact_refs'].items():
            u.require(u.json_same(_read_ref(ref),bundle[role]),'RESOLUTION_RAW_FILE_CONTENT_CHANGED',role)
        actual=bundle['execution_evidence']
        u.require(_metadata_same(actual['writer_process'],evidence['writer_host_release']) and
            _metadata_same(actual['writer_process']['result'],execution) and
            _metadata_same(actual['reader_processes'],evidence['reader_host_release']['processes']) and
            _metadata_same(actual['ledger_intent'],evidence['ledger_intent']), 'RESOLUTION_ORIGINAL_EXECUTION_NOT_BOUND')
        verify_audit_manifest(bundle['audit_manifest'],
            {**predecessor['artifact_refs'],**outer['evidence_refs'],**bundle['artifact_refs']})
    return {'ok':True,'status':'LOCAL_PREDECESSOR_FILES_HASH_AND_CONTENT_BOUND'}

def approved_main_content(candidate_path,crop_proof_path,review_path):
    candidate_ref,proof_ref,review_ref=map(_ref,(candidate_path,crop_proof_path,review_path))
    c,p,r=map(_read_ref,(candidate_ref,proof_ref,review_ref))
    u.require(c['root_review_ref']==review_ref['path'] and c['root_review']['sha256']==review_ref['sha256'] and
        c['remote_crop_fetch_proof']['sha256']==proof_ref['sha256'] and
        r.get('crop_fetch_proof_sha256')==proof_ref['sha256'], 'ROOT_REVIEW_OR_CROP_PROOF_CHANGED')
    u.require(r.get('status')=='PASS_SOURCE_CONTENT_AND_BOUNDARIES' and r.get('main_answer')=='C' and
        r.get('variant_answer')=='B', 'ROOT_Q7_SOURCE_REVIEW_NOT_PASS')
    actual={x['key']:x for x in p['results']}
    source_evidence=[]
    for frame in c['planned_frames']:
        source={'path':frame['source']['path'],'sha256':frame['source']['sha256']}
        # Original source/crop are binary; verify raw hashes without JSON decoding.
        u.require(_ref(source['path'])['sha256']==source['sha256'],'SOURCE_IMAGE_CHANGED')
        if source not in source_evidence:source_evidence.append(source)
        result=actual[frame['key']]
        u.require(result['status']==200 and result['sha256']==frame['crop_sha256'] and
            result['url']==frame['image_path'] and result['source_sha256']==source['sha256'] and
            u.json_same(result['bbox'],frame['bbox']) and
            _ref(result['file'])['sha256']==result['sha256'] and
            _ref(frame['crop']['path'])['sha256']==frame['crop_sha256'], 'REMOTE_CROP_RAW_BYTES_CHANGED')
    return {'candidate_ref':candidate_ref['path'],'candidate_sha256':candidate_ref['sha256'],'candidate':c,
        'review_ref':review_ref['path'],'review_sha256':review_ref['sha256'],
        'crop_evidence_ref':proof_ref['path'],'crop_evidence_sha256':proof_ref['sha256'],
        'source_evidence':source_evidence}

def materialize_main(candidate_path,crop_proof_path,review_path,before_full,predecessor):
    if isinstance(before_full,(str,Path)):before_full=load_full_directory(before_full)
    if set(predecessor)=={'plan','receipt','comparison','outer_acceptance'}:
        predecessor=load_predecessor(predecessor)
    else:verify_predecessor_files(predecessor)
    approved=approved_main_content(candidate_path,crop_proof_path,review_path)
    return f.make_finalize_plan(before_full,approved,predecessor)

def verify_evidence_files(plan):
    f.validate_finalize_plan(plan)
    verify_predecessor_files(plan['predecessor'])
    ap=plan['approved_main_content']
    current=approved_main_content(ap['candidate_ref'],ap['crop_evidence_ref'],ap['review_ref'])
    u.require(u.json_same(current,ap),'APPROVED_MAIN_EVIDENCE_CHANGED')
    return {'ok':True,'status':'ALL_FINALIZE_EVIDENCE_FILES_BOUND'}
