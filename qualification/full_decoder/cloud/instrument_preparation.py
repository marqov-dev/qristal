"""Insert a bounded construction inventory and intentional stop before search."""
import hashlib
SOURCE_SHA256="9d5cba948c0a80cc5b3e2d5aae3cc2b508692513c66813287821d892b55dd181"
def instrument(raw):
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:raise ValueError('decoder_source_changed')
    anchor='                    qubits_next_metric, qubits_total_metric_buffer);\n'
    text=raw.decode()
    if text.count(anchor)!=1:raise ValueError('inventory_anchor')
    result=text.replace(anchor,anchor+'    qb_inventory::inventory(state_prep_circ);\n    throw std::runtime_error("QB_INVENTORY_ONLY_STOP");\n')
    # Header must follow the original includes because it uses XACC definitions.
    anchor='namespace qristal {'
    if result.count(anchor)!=1:raise ValueError('namespace_anchor')
    result=result.replace(anchor,'#include "preparation_inventory.hpp"\n'+anchor)
    return result.encode()
