"""One source-bound experimental replacement, never a production patch tool."""
import difflib
import hashlib
from instrument_search import instrument

HEADER_SHA256='2aaed48725e109b6d0de1399da57f583683efcffeed01ce17d2c94e80872deba'


def replace(raw,header):
    if hashlib.sha256(header).hexdigest()!=HEADER_SHA256:raise ValueError('unqualified_mcz_header')
    traced,_,trace_identity=instrument(raw)
    source=traced.decode()
    anchor='    mcz->expand({{"U", z_gate}, {"control-idx", controlled_bits}});\n'
    if source.count(anchor)!=1:raise ValueError('mcz_anchor')
    replacement='''    if (qpu_->name() == "sparse-sim") {
      mcz = qb_qualification::make_mcz("sparse-sim", total_num_qubits,
                                     controlled_bits, qubits_state_prep.back());
    } else {
      mcz->expand({{"U", z_gate}, {"control-idx", controlled_bits}});
    }
'''
    source='#include "direct_mcz.hpp"\n'+source.replace(anchor,replacement)
    patch=''.join(difflib.unified_diff(raw.decode().splitlines(True),source.splitlines(True),
                                    fromfile='exponential_search.cpp',tofile='exponential_search.mcz-probe.cpp'))
    encoded=source.encode()
    return encoded,patch,dict(original_sha256=hashlib.sha256(raw).hexdigest(),
                             traced_predecessor_sha256=trace_identity['traced_sha256'],
                             derived_sha256=hashlib.sha256(encoded).hexdigest(),
                             patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
                             header_sha256=HEADER_SHA256,prototype_only=True,
                             original_decomposition_retained_for_other_backends=True)
