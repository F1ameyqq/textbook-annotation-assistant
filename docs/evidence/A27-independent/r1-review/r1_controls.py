import importlib.util,json,os,subprocess,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

PRIVATE=Path('D:/1800/.local/stages/a27-independent-20261023')
PRODUCT=PRIVATE/'candidate-ebca4c71/product'
OUTPUT=Path(os.environ['A27_OUTPUT'])
spec=importlib.util.spec_from_file_location('r1_independent_fixtures',PRODUCT/'tests/test_a27_stability.py')
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
recovery,raw=fixtures.recovery,fixtures.raw

def bundle_at(name):
    root=OUTPUT/name;root.mkdir()
    b=fixtures.SyntheticBundle(root);b.calls=[];b.after_configure=None;b.fail_reader=False
    return b

class R1Controls(unittest.TestCase):
    def test_01_exact_original_witness_row_is_rejected(self):
        p=PRIVATE/'candidate-ebca4c71/delivery/frozen-review-inputs/profile-alias-witness.json'
        data=p.read_bytes()
        self.assertEqual(fixtures.sha(data),'616fd5b65ed843a4446bd0651696281c9d766cccebccd5bb273f8eaf22fe5824')
        old=json.loads(data)
        profile=Path(old['profile'])
        self.assertTrue(profile.is_relative_to(PRIVATE/'test-output'))
        self.assertTrue(Path(old['alias']).samefile(profile))
        self.assertEqual(old['dispatched_commands'],['configure','capture'])
        mocked=Mock(return_value=SimpleNamespace(returncode=0,stdout=raw(old['os_observer_rows'])))
        with self.assertRaisesRegex(fixtures.BindingError,'RECOVERY_PROFILE_IN_USE'):
            recovery.exclusive_profile(profile,run=mocked)
        print(json.dumps({'control':'R1-I01','original_witness_sha256':fixtures.sha(data),'exact_row_rejected':'RECOVERY_PROFILE_IN_USE','real_OS_query':False}))

    def test_02_nonlocal_or_relative_argument_rejected_before_stat(self):
        cases=['relative-profile','C:relative-profile','\\\\example.invalid\\share\\profile',
               '\\\\?\\UNC\\example.invalid\\share\\profile','\\\\.\\UNC\\example.invalid\\share\\profile']
        for value in cases:
            with self.subTest(value=value),patch.object(recovery.os,'stat',side_effect=AssertionError('FORBIDDEN_PATH_STAT')) as stat_call:
                with self.assertRaisesRegex(fixtures.BindingError,'RECOVERY_PROFILE_ARGUMENT_UNKNOWN'):
                    recovery.directory_identity(value)
                stat_call.assert_not_called()
        print(json.dumps({'control':'R1-I02','pre_stat_rejections':len(cases),'network_or_directory_lookup':0}))

    def test_03_distinct_prefix_directory_actual_entry_and_single_spend(self):
        b=bundle_at('different-profile');args=b.request()
        other=b.profile.with_name(b.profile.name+'-unrelated');other.mkdir()
        rows=[{'ProcessId':303,'CreationDate':'synthetic-only',
               'CommandLine':subprocess.list2cmdline(['msedge.exe','--user-data-dir='+str(other)])}]
        mock_query=Mock(return_value=SimpleNamespace(returncode=0,stdout=raw(rows)))
        observed=[]
        def observe(p):
            value=recovery.exclusive_profile(p,run=mock_query);observed.append(value);return value
        before=recovery.ledger_snapshot(b.ledger)
        result=recovery.execute(*args,run_child=b.child,observe=observe)
        self.assertEqual(result['status'],'READBACK_MATCHED_AFTER_OS_RELEASE')
        self.assertEqual(b.calls,['configure','capture'])
        self.assertEqual(len(observed),2)
        self.assertEqual(recovery.ledger_snapshot(b.ledger),before)
        self.assertEqual(list(b.ledger.glob('*.accepted.json')),[])
        with self.assertRaises(ValueError):recovery.execute(*args,run_child=b.child,observe=observe)
        self.assertEqual(b.calls,['configure','capture'])
        proof={'control':'R1-I03','different_directory':True,'calls':b.calls,'posts':0,
               'ledger_unchanged':True,'standard_markers':0,'repeat_dispatch_blocked':True,
               'result':result,'observations':observed}
        (OUTPUT/'different-profile-entry-result.json').write_bytes(raw(proof)+b'\n')
        print(json.dumps({k:v for k,v in proof.items() if k not in ('result','observations')}))

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
