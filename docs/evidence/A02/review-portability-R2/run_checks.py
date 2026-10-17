"""Independent R2 actual subprocess matrix; no author runner and no source worktree execution."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

OUT=Path(__file__).resolve().parent;ROOT=Path('D:/1800')
data=json.loads((OUT/'bootstrap.json').read_text(encoding='utf-8'))
STAGE=Path(data['stage']);BASE=Path(data['exports']['base']['root']);CANDIDATE=Path(data['exports']['candidate']['root'])
GIT=Path(shutil.which('git'));PROBE=OUT/'probe.py';COMMIT=data['target_commit']
commands=[]
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def local_git(cwd,*args):
    argv=[str(GIT),'-c','core.autocrlf=false','-c','core.hooksPath='+str(STAGE/'empty hooks'),*args]
    run=subprocess.run(argv,cwd=cwd,capture_output=True)
    assert run.returncode==0,(argv,run.stderr.decode(errors='replace'))
    return run.stdout.decode().strip()
def check_unknown(events):
    result=next(e['result'] for e in events if e['event']=='result')
    assert result['checkout_commit'] is None and 'unknown' in result['status'] and 'verified' not in result['status']
def command(label,root,mode,no_git=False,expected=0,extra=None):
    folder=OUT/('runtime-final' if '--resume' in sys.argv else 'runtime')/label;folder.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',PYTHONPATH=str(root/'src'),TEMP=str(STAGE/'tmp'),TMP=str(STAGE/'tmp'))
    removed=[]
    for name in list(env):
        if name.startswith('GIT_'):
            removed.append(name);del env[name]
    env['PATH']=str(STAGE/'empty tool path') if no_git else str(GIT.parent)+os.pathsep+os.environ.get('PATH','')
    argv=[sys.executable,'-B',str(PROBE),'--root',str(root),'--mode',mode]+(extra or [])
    run=subprocess.run(argv,cwd=root,env=env,capture_output=True)
    (folder/'stdout.txt').write_bytes(run.stdout);(folder/'stderr.txt').write_bytes(run.stderr)
    events=[json.loads(line) for line in run.stdout.decode('utf-8').splitlines() if line.startswith('{')]
    record={'label':label,'argv':argv,'cwd':str(root),'PATH':env['PATH'],'git_executable':shutil.which('git',path=env['PATH']),
        'removed_git_variable_names':removed,'exit_code':run.returncode,'expected_exit_code':expected,
        'stdout':str((folder/'stdout.txt').relative_to(OUT)),'stderr':str((folder/'stderr.txt').relative_to(OUT)),
        'probe_source':'probe.py','events':events}
    commands.append(record);save(folder/'command.json',record);save(OUT/'commands-in-progress.json',commands)
    assert run.returncode==expected,(label,run.returncode,run.stderr.decode(errors='replace'))
    environment=events[0];assert environment['event']=='environment'
    if no_git:
        assert environment['git_executable'] is None and not environment['git_os_probe']['started']
        assert environment['git_os_probe']['type']=='FileNotFoundError'
    if mode=='identity' and expected==0 and label!='checkout-real':check_unknown(events)
    if mode.startswith('tests'):
        result=next(e for e in events if e.get('event')=='tests-result')
        expected_count=62 if mode=='tests-discovery' else 1
        assert result['tests_run']==expected_count and result['skipped']==0
        if not expected:assert result['successful'] and result['failures']==result['errors']==0
    print(label,run.returncode,flush=True);return events
def main():
    for name in ('empty tool path','tmp','empty hooks'): (STAGE/name).mkdir(exist_ok='--resume' in sys.argv)
    assert shutil.which('git',path=str(STAGE/'empty tool path')) is None
    # A normal local fixture checkout: candidate code bytes exactly match frozen export.
    checkout=STAGE/'normal local checkout'
    if '--resume' not in sys.argv:
        shutil.copytree(CANDIDATE,checkout)
        local_git(checkout,'init');local_git(checkout,'add','.')
        local_git(checkout,'-c','user.name=A02 Independent Review','-c','user.email=review@example.invalid','-c','commit.gpgsign=false','commit','-m','Local frozen R2 identity fixture')
    fixture_head=local_git(checkout,'rev-parse','HEAD');assert Path(local_git(checkout,'rev-parse','--show-toplevel')).resolve()==checkout.resolve()
    nested=checkout/'nested raw export'
    if '--resume' not in sys.argv:shutil.copytree(CANDIDATE,nested)
    assert Path(local_git(nested,'rev-parse','--show-toplevel')).resolve()==checkout.resolve()
    assert local_git(nested,'rev-parse','HEAD')==fixture_head
    damaged=STAGE/'damaged source'
    if '--resume' not in sys.argv:
        shutil.copytree(CANDIDATE,damaged)
        changed=damaged/'src/annotation/__init__.py';raw=changed.read_bytes();assert raw;changed.write_bytes(bytes([raw[0]^1])+raw[1:])
    save(OUT/'fixture-checkout.json',{'root':str(checkout),'head':fixture_head,'source_files_exact_commit':COMMIT,
        'note':'Independent local Git fixture containing exact exported subset; fixture HEAD deliberately differs from delivery commit. No remote and no executor/main branch changes.',
        'nested_root':str(nested),'nested_detected_parent_head':fixture_head,'damaged_relative_file':'src/annotation/__init__.py'})
    command('base-real-noGit',BASE,'identity',True,1)
    command('base-original-noGit',BASE,'tests-original',True,1)
    command('base-original-withGit',BASE,'tests-original')
    command('candidate-real-noGit',CANDIDATE,'identity',True)
    command('candidate-original-noGit',CANDIDATE,'tests-original',True)
    command('candidate-original-withGit',CANDIDATE,'tests-original')
    command('candidate-raw-withGit',CANDIDATE,'identity')
    ev=command('checkout-real',checkout,'identity');assert next(e['result']['checkout_commit'] for e in ev if e['event']=='result')==fixture_head
    command('nested-real-withGit',nested,'identity')
    command('nested-real-noGit',nested,'identity',True)
    binding=['--identity-repo',str(Path('C:/Users/ASUS/.codex/worktrees/a02-planner-mock/1800')),'--commit',COMMIT]
    command('binding-noGit',CANDIDATE,'binding',True,1,binding)
    good=command('binding-positive',CANDIDATE,'binding',False,0,binding)
    value=next(e['result'] for e in good if e['event']=='result');assert value['declared_commit']==COMMIT and value['checkout_commit'] is None and value['source_sha256']
    command('binding-damaged',damaged,'binding',False,1,binding)
    command('binding-invalid-commit',CANDIDATE,'binding',False,1,['--identity-repo',str(checkout),'--commit','0000000000000000000000000000000000000000'])
    command('binding-invalid-repository',CANDIDATE,'binding',False,1,['--identity-repo',str(nested),'--commit',COMMIT])
    second=command('second-real-path-disappears',checkout,'second-real',False,0,['--no-git-path',str(STAGE/'empty tool path')])
    check_unknown(second);trace=next(e for e in second if e['event']=='real-spawn-trace');assert len(trace['calls'])==2 and trace['calls'][0]['started'] and not trace['calls'][1]['started']
    command('binding-git-disappears',CANDIDATE,'binding-git-disappears',False,1,binding+['--no-git-path',str(STAGE/'empty tool path')])
    command('mock-finite-faults',CANDIDATE,'mock-faults')
    command('a02-discovery-real-noGit',CANDIDATE,'tests-discovery',True)
    command('a02-discovery-withGit',CANDIDATE,'tests-discovery')
    save(OUT/'commands.json',{'target_commit':COMMIT,'commands':commands,'all_expected_exit_codes_observed':True,
        'synchronous_children_returned':True,'background_helpers_started':0,'platform_network_browser_model_calls':0})
    print(json.dumps({'commands':len(commands),'expected_nonzero':sum(c['expected_exit_code']!=0 for c in commands),
        'discovery_tests_per_environment':62,'original_test_skipped':False,'all_expected':True}))
if __name__=='__main__':
    if '--finish' in sys.argv:
        commands.extend(json.loads((OUT/'commands-in-progress.json').read_text(encoding='utf-8')))
        for record in commands:
            assert record['exit_code']==record['expected_exit_code']
            if record['label']=='a02-discovery-real-noGit':
                observed=next(e for e in record['events'] if e.get('event')=='tests-result')
                assert observed['tests_run']==62 and observed['successful'] and observed['skipped']==observed['errors']==observed['failures']==0
        command('a02-discovery-withGit',CANDIDATE,'tests-discovery')
        save(OUT/'commands.json',{'target_commit':COMMIT,'commands':commands,'all_expected_exit_codes_observed':True,
            'synchronous_children_returned':True,'background_helpers_started':0,'platform_network_browser_model_calls':0})
        print(json.dumps({'commands':len(commands),'expected_nonzero':sum(c['expected_exit_code']!=0 for c in commands),
            'discovery_tests_per_environment':62,'original_test_skipped':False,'all_expected':True}))
    else:main()
