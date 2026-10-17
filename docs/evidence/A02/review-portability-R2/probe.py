"""Independent bounded identity checks. Real spawn faults and mocks are labelled separately."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
import unittest
from unittest.mock import patch

def emit(value):print(json.dumps(value,ensure_ascii=False),flush=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def execute():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--mode',required=True);parser.add_argument('--identity-repo',type=Path)
    parser.add_argument('--commit');parser.add_argument('--no-git-path')
    args=parser.parse_args();root=args.root.resolve();identity_path=root/'examples/a02/R1/identity.py'
    spec=importlib.util.spec_from_file_location('independent_identity',identity_path)
    identity=importlib.util.module_from_spec(spec);spec.loader.exec_module(identity)
    real_run=subprocess.run
    try:
        raw=real_run(['git','--version'],cwd=root,capture_output=True,text=True)
        launch={'started':True,'exit_code':raw.returncode,'stdout':raw.stdout,'stderr':raw.stderr}
    except OSError as e:launch={'started':False,'type':type(e).__name__,'message':str(e)}
    emit({'event':'environment','argv':sys.argv,'cwd':str(Path.cwd()),'root':str(root),'PATH':os.environ.get('PATH'),
        'git_executable':shutil.which('git'),'git_os_probe':launch,'dot_git_exists':(root/'.git').exists(),
        'identity_import':str(Path(identity.__file__).resolve()),'identity_sha256':sha(identity_path),
        'python':sys.version,'executable':sys.executable})
    if args.mode=='tests-original' or args.mode=='tests-discovery':
        sys.path[:0]=[str(root/'src'),str(root/'tests')]
        if args.mode=='tests-original':suite=unittest.defaultTestLoader.loadTestsFromName('test_a02_r1.A02R1Tests.test_export_subdirectory_cannot_borrow_enclosing_git_head')
        else:suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_a02*.py')
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        imports={}
        for name,module in list(sys.modules.items()):
            p=getattr(module,'__file__',None)
            if p and (name.startswith('annotation') or name.startswith('test_a02')):
                path=Path(p).resolve();path.relative_to(root);imports[name]={'path':str(path),'sha256':sha(path)}
        for name in ('test_a02_r1','test_a02_portability_r2'):
            test=sys.modules.get(name)
            if test and hasattr(test,'identity'):
                path=Path(test.identity.__file__).resolve();imports[name+'.identity']={'path':str(path),'sha256':sha(path)}
        if 'test_a02_portability_r2' in sys.modules:
            imports['test_a02_portability_r2.IDENTITY']={'path':str(root/'examples/a02/R1/identity.py'),'sha256':sha(identity_path)}
        emit({'event':'tests-result','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'skipped':len(result.skipped),'successful':result.wasSuccessful(),'actual_imports':imports})
        return 0 if result.wasSuccessful() else 1
    if args.mode=='identity':
        emit({'event':'result','result':identity.git_identity(root)})
    elif args.mode=='binding':
        emit({'event':'result','result':identity.source_binding(root,args.commit,args.identity_repo)})
    elif args.mode in ('second-real','binding-git-disappears'):
        events=[]
        def recording_run(argv,*a,**kw):
            event={'argv':argv,'cwd':str(kw.get('cwd')),'PATH':os.environ.get('PATH')}
            try:
                result=real_run(argv,*a,**kw);event.update(started=True,exit_code=result.returncode,stdout=result.stdout)
            except OSError as e:
                event.update(started=False,error_type=type(e).__name__,message=str(e));events.append(event);raise
            events.append(event)
            if args.mode=='second-real' and argv==['git','rev-parse','--show-toplevel'] and result.returncode==0:
                os.environ['PATH']=args.no_git_path
            if args.mode=='binding-git-disappears' and argv==['git','rev-parse','HEAD'] and result.returncode==0:
                os.environ['PATH']=args.no_git_path
            return result
        with patch.object(subprocess,'run',side_effect=recording_run):
            try:
                value=identity.git_identity(root) if args.mode=='second-real' else identity.source_binding(root,args.commit,args.identity_repo)
            except Exception as e:
                emit({'event':'real-spawn-trace','method':'First actual Git call(s), then child PATH changed before next real OS spawn; no fabricated subprocess result.','calls':events})
                raise
        emit({'event':'real-spawn-trace','method':'Actual OS calls with child PATH changed only after first successful toplevel; no simulated return values.',
            'calls':events,'git_after_path_change':shutil.which('git')})
        emit({'event':'result','result':value})
    elif args.mode=='mock-faults':
        cases=[];top=subprocess.CompletedProcess([],0,stdout=str(root))
        for label,error in [('missing',FileNotFoundError('independent second-call missing')),('denied',PermissionError('independent second-call denied')),
                            ('nonzero',subprocess.CalledProcessError(128,['git','rev-parse','HEAD']))]:
            with patch.object(subprocess,'run',return_value=top) as first,patch.object(subprocess,'check_output',side_effect=error) as second:
                value=identity.git_identity(root)
                assert value['checkout_commit'] is None and 'unknown' in value['status']
                cases.append({'case':label,'evidence_type':'MOCK_ONLY','calls':[first.call_args.args[0],second.call_args.args[0]],'result':value})
        with patch.object(subprocess,'run',return_value=top),patch.object(subprocess,'check_output',return_value=' \n'):
            value=identity.git_identity(root);assert value['checkout_commit'] is None and 'unknown' in value['status']
            cases.append({'case':'empty-head','evidence_type':'MOCK_ONLY','result':value})
        with patch.object(subprocess,'run',return_value=subprocess.CompletedProcess([],128,stdout='')) as first,patch.object(subprocess,'check_output') as second:
            value=identity.git_identity(root);assert value['checkout_commit'] is None and not second.called
            cases.append({'case':'first-nonzero','evidence_type':'MOCK_ONLY','head_called':second.called,'result':value})
        emit({'event':'result','method':'All cases in this result are mocks; not real noGit proof.','cases':cases})
    else:raise ValueError(args.mode)
    assert sha(identity_path)==sha(Path(identity.__file__)), 'Loaded identity bytes changed'
    return 0

if __name__=='__main__':
    try:sys.exit(execute())
    except Exception as error:
        emit({'event':'rejected-or-error','type':type(error).__name__,'message':str(error),'binding_returned':False})
        traceback.print_exc();sys.exit(1)
