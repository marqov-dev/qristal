"""Insert diagnostic output only into one hash-bound Core source revision."""
import difflib
import hashlib

SOURCE_SHA256 = "acc3dd0ec7297aaf56479c35b7ff86fdf73f042bb25e5317a52a21718922bd98"
BEGIN = "// QB_TRACE_BEGIN\n"
END = "// QB_TRACE_END\n"


def instrument(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("unexpected_core_source")
    original = raw.decode()
    source = original

    def insert(anchor, code, after=False):
        nonlocal source
        if source.count(anchor) != 1:
            raise ValueError("trace_anchor")
        block = BEGIN + code + "\n" + END
        source = source.replace(anchor, anchor + block if after else block + anchor)

    insert("  auto gateRegistry = xacc::getService<xacc::IRProvider>(\"quantum\");\n", '''  const auto qb_trace_start = std::chrono::steady_clock::now();
  const auto qb_trace = [&](const char* stage, long long count = -1) {
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - qb_trace_start).count();
    std::cout << "SEARCH_TRACE " << stage << " elapsed_ms=" << ms
              << " count=" << count << std::endl;
  };
  qb_trace("execute_begin");''')
    insert('    const bool expand_ok_inv_sp = inv_sp->expand({{"circ", state_prep}});\n',
           '    qb_trace("inverse_expand_begin");')
    insert('    assert(expand_ok_inv_sp);\n',
           '    qb_trace("inverse_expand_end", inv_sp->nInstructions());', after=True)
    insert('    auto qubits_state_prep_set = qristal::uniqueBitsQD(state_prep);\n',
           '    qb_trace("used_bits_begin");')
    insert('    auto qubits_state_prep_set = qristal::uniqueBitsQD(state_prep);\n',
           '    qb_trace("used_bits_end", qubits_state_prep_set.size());', after=True)
    anchor = '    mcz->expand({{"U", z_gate}, {"control-idx", controlled_bits}});\n'
    insert(anchor, '    qb_trace("mcz_expand_begin", controlled_bits.size());')
    insert(anchor, '    qb_trace("mcz_expand_end", mcz->nInstructions());', after=True)
    insert('    // amplitude amplification\n', '    qb_trace("amplification_begin", iterations);')
    insert('    std::vector<int> measured_indices;\n',
           '    qb_trace("amplification_end", exp_search_circuit->nInstructions());')
    anchor = '    qpu_->execute(temp_buffer_2, exp_search_circuit);\n'
    insert(anchor, '    qb_trace("backend_execute_begin", exp_search_circuit->nInstructions());')
    insert(anchor, '    qb_trace("backend_execute_end");', after=True)
    # Removal must recover every original byte: no algorithm statement is edited.
    restored = source
    while BEGIN in restored:
        start = restored.index(BEGIN)
        end = restored.index(END, start) + len(END)
        restored = restored[:start] + restored[end:]
    if restored != original:
        raise ValueError("non_trace_change")
    patch = ''.join(difflib.unified_diff(original.splitlines(True), source.splitlines(True),
                                      fromfile='exponential_search.cpp',
                                      tofile='exponential_search.traced.cpp'))
    encoded = source.encode()
    return encoded, patch, {
        'source_sha256': SOURCE_SHA256,
        'traced_sha256': hashlib.sha256(encoded).hexdigest(),
        'patch_sha256': hashlib.sha256(patch.encode()).hexdigest(),
        'algorithm_statements_unchanged': True,
        'counts_are_top_level_instructions': True,
    }
