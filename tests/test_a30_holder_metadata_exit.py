"""Synthetic Windows API fault cases; no browser, workload, platform, or model launches."""
from pathlib import Path
import ctypes,importlib.util,time,unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('a30_holder_metadata',ROOT/'tools/owned_process.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def fail(code):
    def call(*args):ctypes.set_last_error(code);return 0
    return call

def times(h,created,*rest):
    created._obj.dwHighDateTime=1;created._obj.dwLowDateTime=2;return 1

class HolderMetadataExit(unittest.TestCase):
    def result(self):return {'observed_processes':[],'errors':[]}

    def test_open_access_denied_is_not_skipped(self):
        r=self.result();held={}
        with patch.object(m,'OpenProcess',fail(5)),self.assertRaises(PermissionError):m.observe(123,held,r)
        self.assertEqual(r['last_stage']['api'],'OpenProcess');self.assertFalse(held)
        self.assertNotIn('observation_skips',r)

    def test_open_invalid_pid_is_explicitly_recorded(self):
        r=self.result()
        with patch.object(m,'OpenProcess',fail(87)):m.observe(123,{},r)
        self.assertEqual(r['observation_skips'][0]['winerror'],87)

    def test_gettimes_denied_after_exit_keeps_handle_and_unknown_metadata(self):
        r=self.result();held={}
        with patch.object(m,'OpenProcess',return_value=77),patch.object(m,'GetTimes',fail(5)),patch.object(m,'Wait',return_value=0):
            m.observe(123,held,r)
        self.assertEqual(held[123][0],77);item=held[123][1]
        self.assertIsNone(item['creation_filetime']);self.assertEqual(item['metadata_status'],'UNAVAILABLE_AFTER_PROVEN_EXIT')
        self.assertEqual(item['metadata_failure']['api'],'GetProcessTimes')

    def test_image_denied_alive_raises_with_handle_owned(self):
        r=self.result();held={}
        with patch.object(m,'OpenProcess',return_value=77),patch.object(m,'GetTimes',times),patch.object(m,'ImageName',fail(5)),patch.object(m,'Wait',return_value=258),self.assertRaises(PermissionError):
            m.observe(123,held,r)
        self.assertEqual(held[123][1]['creation_filetime'],(1<<32)|2)
        self.assertEqual(held[123][1]['metadata_failure']['held_handle_wait_result'],258)
        self.assertEqual(r['last_stage']['pid'],123)

    def test_image_denied_wait_failed_preserves_both_errors(self):
        r=self.result();held={}
        def wait(*args):ctypes.set_last_error(6);return 0xffffffff
        with patch.object(m,'OpenProcess',return_value=77),patch.object(m,'GetTimes',times),patch.object(m,'ImageName',fail(5)),patch.object(m,'Wait',wait),self.assertRaises(PermissionError):
            m.observe(123,held,r)
        detail=held[123][1]['metadata_failure']
        self.assertEqual((detail['winerror'],detail['held_handle_wait_winerror']),(5,6))

    def test_image_denied_after_exit_is_finite_nonfatal_case(self):
        r=self.result();held={}
        with patch.object(m,'OpenProcess',return_value=77),patch.object(m,'GetTimes',times),patch.object(m,'ImageName',fail(5)),patch.object(m,'Wait',return_value=0):
            m.observe(123,held,r)
        self.assertIsNone(held[123][1]['image']);self.assertEqual(held[123][1]['metadata_status'],'UNAVAILABLE_AFTER_PROVEN_EXIT')
        self.assertFalse(r['errors'])

    def test_unrelated_metadata_error_is_not_relaxed(self):
        with patch.object(m,'OpenProcess',return_value=77),patch.object(m,'GetTimes',times),patch.object(m,'ImageName',fail(6)),patch.object(m,'Wait',return_value=0),self.assertRaises(OSError):
            m.observe(123,{},self.result())

    def test_cleanup_uses_original_handles_with_bounded_wait_and_closes_after_error(self):
        r=self.result();r['errors']=[{'type':'ORIGINAL_FAILURE'}]
        held={1:(81,{'pid':1}),2:(82,{'pid':2})};waits=[];closed=[]
        def wait(h,ms):waits.append((h,ms));return 0
        def code(h,out):
            if h==81:ctypes.set_last_error(5);return 0
            out._obj.value=0;return 1
        with patch.object(m,'Wait',wait),patch.object(m,'GetExit',code),patch.object(m,'Close',lambda h:closed.append(h) or 1):
            m.release_held(held,r,time.monotonic()+1)
        self.assertEqual(closed,[81,82]);self.assertTrue(all(0<ms<=1000 for _,ms in waits))
        self.assertEqual(r['errors'][0]['type'],'ORIGINAL_FAILURE');self.assertEqual(r['errors'][1]['api'],'GetExitCodeProcess')
        self.assertEqual(held[2][1]['exit_code'],0)

    def test_cleanup_wait_failed_and_timeout_remain_distinct(self):
        r=self.result();held={1:(81,{'pid':1}),2:(82,{'pid':2})};closed=[]
        def wait(h,ms):ctypes.set_last_error(6);return 0xffffffff if h==81 else 258
        with patch.object(m,'Wait',wait),patch.object(m,'Close',lambda h:closed.append(h) or 1):m.release_held(held,r,time.monotonic())
        self.assertEqual(held[1][1]['exit_wait_status'],'WAIT_FAILED');self.assertEqual(held[2][1]['exit_wait_status'],'TIMEOUT')
        self.assertEqual(closed,[81,82]);self.assertEqual(r['errors'][0]['winerror'],6)

if __name__=='__main__':unittest.main(verbosity=2,failfast=True)
