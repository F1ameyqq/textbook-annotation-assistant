"""Record nested children used by compatibility/isolation, without env dumps."""
from datetime import datetime,timezone
import json,locale,os,subprocess,time
from ops import OUT,sha,write


def install(label):
    original = subprocess.Popen
    records = []
    directory = OUT / "nested-processes" / label
    directory.mkdir(parents=True, exist_ok=False)

    class RecordedPopen(original):
        def __init__(self, args, *positional, **kwargs):
            self._audit_dir = directory / ("child-%02d" % (len(records) + 1))
            self._audit_dir.mkdir()
            self._audit_streams = [(self._audit_dir / name).open("xb") for name in ("stdout.txt", "stderr.txt")]
            self._audit_record = {"argv": args, "cwd": str(kwargs.get("cwd") or os.getcwd()), "registered_at": datetime.now(timezone.utc).isoformat(), "timeout_seconds": 30, "input_scope": "fixed R7 inputs/product source index in parent registered run", "environment": "not serialized"}
            self._audit_record['parent_product_source_index_sha256']=sha((OUT/'runs'/label/'product-source-index.json').read_bytes())
            self._audit_record['raw_input_pins_sha256']=sha((OUT/'raw-input-pins.json').read_bytes())
            self._audit_text=bool(kwargs.get('text')or kwargs.get('universal_newlines')or kwargs.get('encoding')or kwargs.get('errors'))
            self._audit_encoding=kwargs.pop('encoding',None)or locale.getpreferredencoding(False)
            self._audit_errors=kwargs.pop('errors',None)or'strict'
            kwargs.pop('text',None);kwargs.pop('universal_newlines',None)
            write(self._audit_dir / "registration.json", self._audit_record)
            self._audit_tick = time.monotonic()
            super().__init__(args, *positional, **kwargs)
            self._audit_record["pid"] = self.pid
            write(self._audit_dir / "started.json", self._audit_record)
            records.append(self)

        def communicate(self, input=None, timeout=None):
            try:
                if isinstance(input,str):input=input.encode(self._audit_encoding,self._audit_errors)
                result = super().communicate(input=input, timeout=30 if timeout is None else min(timeout, 30))
            except subprocess.TimeoutExpired:
                self.kill()
                result = super().communicate()
                self._audit_record["timed_out"] = True
            for handle, body in zip(self._audit_streams, result):
                if body is not None:
                    handle.write(body)
                handle.close()
            self._audit_record.update(exit_code=self.returncode, alive=self.poll() is None, elapsed_seconds=time.monotonic() - self._audit_tick, timed_out=self._audit_record.get("timed_out", False))
            write(self._audit_dir / "exit.json", self._audit_record)
            if self._audit_text:
                return tuple(body.decode(self._audit_encoding,self._audit_errors).replace('\r\n','\n').replace('\r','\n')if body is not None else None for body in result)
            return result

    subprocess.Popen = RecordedPopen
    return records, lambda: setattr(subprocess, "Popen", original)
