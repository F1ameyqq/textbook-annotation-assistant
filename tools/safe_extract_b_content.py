"""Independently unpack a frozen B ZIP into a new directory; no producer code."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import stat
import zipfile


def extract(archive, destination, expected_sha256):
    raw=Path(archive).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('ARCHIVE_SHA256_CHANGED')
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('NEW_DIRECTORY_REQUIRED')
    with zipfile.ZipFile(archive) as z:
        seen=set(); members=[]
        for item in z.infolist():
            name=item.filename;p=PurePosixPath(name);w=PureWindowsPath(name)
            if not name or '\\' in name or ':' in name or p.is_absolute() or w.is_absolute() or w.drive or '..' in p.parts or name.startswith('/') or stat.S_ISLNK(item.external_attr>>16):
                raise ValueError('UNSAFE_ZIP_MEMBER')
            token='/'.join(p.parts).casefold()
            if token in seen:raise ValueError('DUPLICATE_ZIP_MEMBER')
            seen.add(token)
            if not (destination/Path(*p.parts)).resolve().is_relative_to(destination):raise ValueError('ZIP_ESCAPE')
            if not item.is_dir():members.append(item)
        destination.mkdir(parents=True,exist_ok=False)
        result=[]
        for item in members:
            body=z.read(item);target=destination/Path(*PurePosixPath(item.filename).parts)
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
            result.append({'path':item.filename,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
    return {'status':'SAFELY_EXTRACTED_NOT_CONTENT_ACCEPTED','archive_sha256':expected_sha256,'files':result,'destination':str(destination),'platform_requests':0}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','sha256','destination','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();result=extract(a.archive,a.destination,a.sha256)
    with Path(a.out).open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps({'status':result['status'],'files':len(result['files']),'platform_requests':0}))
