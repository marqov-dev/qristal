"""Record publication separately from subsequent native qualification."""
import json
import os
from pathlib import Path
import re


def record(root, digest, revision, run, attempt, metadata):
    if not re.fullmatch(r'sha256:[a-f0-9]{64}',digest) or not re.fullmatch('[a-f0-9]{40}',revision):
        raise ValueError('release_identity')
    if not run.isdigit() or not attempt.isdigit():
        raise ValueError('workflow_identity')
    context=json.loads((root/'release-context.json').read_text())
    if context['source_revision'] != revision or metadata['containerimage.digest'] != digest:
        raise ValueError('publication_binding')
    value={'schema':'marqov.cpu-release/v1','image':'ghcr.io/marqov-dev/qristal-cpu@'+digest,
           'source_revision':revision,'workflow_run':f'https://github.com/marqov-dev/qristal/actions/runs/{run}/attempts/{attempt}',
           'context':context,'status':'published_candidate_pending_acquired_checks','hosted_available':False}
    (root/'release.json').write_text(json.dumps(value,indent=2)+'\n')
    (root/'build-metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')


if __name__ == '__main__':
    record(Path('.cpu-release'),os.environ['DIGEST'],os.environ['GITHUB_SHA'],os.environ['GITHUB_RUN_ID'],
           os.environ['GITHUB_RUN_ATTEMPT'],json.loads(os.environ['BUILD_METADATA']))
