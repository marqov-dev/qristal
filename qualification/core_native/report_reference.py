"""Compact console references; archive verification remains authoritative."""
import hashlib
import json
import tarfile

SCHEMA='qb.core-report-reference/v1'
MAX_REPORT_BYTES=16*1024*1024
IDENTITY={'bytes','sha256','report_sha256','receipt_sha256'}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity_ok(identity):
    return (isinstance(identity,dict) and set(identity)==IDENTITY
        and type(identity['bytes']) is int and identity['bytes']>0
        and all(isinstance(identity[k],str) and len(identity[k])==64
                and all(c in '0123456789abcdef' for c in identity[k])
                for k in IDENTITY-{'bytes'}))


def envelope(report):
    result={'kind':'qb-core-native/v1','schema':SCHEMA,'native_passed':False}
    for name in ('protocol_sha256','materials_sha256'):
        value=report.get(name)
        if isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value):result[name]=value
    identity=report.get('output_artifact')
    if (identity_ok(identity) and not report.get('output_artifact_error')
            and all(k in result for k in ('protocol_sha256','materials_sha256'))):
        result['output_artifact']=identity
        result['native_passed']=report.get('native_passed') is True
    else:result['error']='output_artifact_unavailable'
    return result


def resolve(path,identity,console,output):
    """Receive transport's console payload WITHOUT output_artifact; return full report."""
    if console.get('schema')!=SCHEMA:
        if 'schema' in console:raise ValueError('unknown console schema')
        verified=output.verify(path,identity,console)
        return verified,dict(console,output_artifact=identity),{'source':'legacy-full-console','console_artifact_binding':True}
    expected={'kind','schema','protocol_sha256','materials_sha256','native_passed'}
    if set(console)!=expected or console['kind']!='qb-core-native/v1' or type(console['native_passed']) is not bool:
        raise ValueError('console reference shape')
    if not identity_ok(identity) or path.stat().st_size!=identity['bytes'] or identity['bytes']>output.MAX_BYTES:
        raise ValueError('artifact identity')
    compressed_hash=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(1024*1024):compressed_hash.update(chunk)
    if compressed_hash.hexdigest()!=identity['sha256']:raise ValueError('archive hash')
    # The existing verifier checks all tar members, modes, links, receipts and hashes.
    # Only bounded report bytes are read here; never extract files to disk.
    report_bytes=None
    expanded_bytes=0
    with tarfile.open(path,'r|gz') as archive:
        for index,member in enumerate(archive):
            if index>=output.MAX_MEMBERS:raise ValueError('archive member bound')
            if member.size<0 or not (member.isfile() or member.isdir() or member.issym()):
                raise ValueError('archive member type/size')
            expanded_bytes+=member.size
            if expanded_bytes>output.MAX_BYTES:raise ValueError('archive expanded bound')
            if member.name=='report.json':
                if report_bytes is not None or not member.isfile() or not 0<member.size<=MAX_REPORT_BYTES:
                    raise ValueError('report member')
                report_bytes=archive.extractfile(member).read(MAX_REPORT_BYTES+1)
    if report_bytes is None or sha(report_bytes)!=identity['report_sha256']:raise ValueError('report identity')
    full=json.loads(report_bytes)
    if not isinstance(full,dict):raise ValueError('report shape')
    for name in ('kind','protocol_sha256','materials_sha256','native_passed'):
        if type(full.get(name)) is not type(console[name]) or full.get(name)!=console[name]:raise ValueError('console/report '+name)
    verified=output.verify(path,identity,full)
    provenance={'schema':'qb.core-console-reference-verification/v1','source':'compact-console-reference',
        'console_artifact_binding':True,'console_reference_sha256':sha(canonical(dict(console,output_artifact=identity))),
        'protocol_sha256':console['protocol_sha256'],'materials_sha256':console['materials_sha256'],
        'archive_sha256':identity['sha256'],'report_sha256':identity['report_sha256']}
    return verified,dict(full,output_artifact=identity),provenance


def recovered_record(report,provenance):
    return {'schema':'qb.core-recovered-report/v1','result':report,
            'source':provenance['source'],
            'console_artifact_binding':provenance['console_artifact_binding'],
            'provenance':provenance}
