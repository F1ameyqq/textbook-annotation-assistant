"""Preserve one static post-functional audit correction, without product calls."""
from evidence import OUT,raw,sha,write
old=OUT/'runs/process-audit-01'
write(OUT/'post-functional-metadata-correction.json',{
 'correction_count':1,'kind':'STATIC_AUDIT_WRAPPER_VS_PERSISTED_OBSERVATION_COMPARISON',
 'first_run':'runs/process-audit-01','first_exit_code':1,'first_pid':19828,
 'first_entry_sha256':sha((old/'entry-source.py').read_bytes()),
 'first_stderr_sha256':sha((old/'stderr.log').read_bytes()),'first_stdout_sha256':sha((old/'stdout.log').read_bytes()),
 'first_error':(old/'stderr.log').read_text(encoding='utf8'),
 'corrected_source':'scripts/process_review.py','corrected_source_sha256':sha((OUT/'scripts/process_review.py').read_bytes()),
 'frozen_source_basis':{'path':'src/annotation/delivery/mock/persistent.py','sha256':sha(raw('src/annotation/delivery/mock/persistent.py')),'lines':[476,477,478,479]},
 'change':'Compare every persisted observation field; require exactly four wrapper fields and verify actual resource bytes, hashes and JSON bodies independently.',
 'first_failure_preserved':True,'product_calls':0,'functional_reruns':0,'functional_driver_changes':0,'database_changes':0,
 'further_static_corrections_authorized':False})
print('{"static_metadata_correction":1,"product_calls":0,"functional_reruns":0}')
