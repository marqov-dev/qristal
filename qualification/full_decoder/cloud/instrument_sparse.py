"""Trace-only sparse visitor profile, bound to one public source revision."""
import difflib
import hashlib
SOURCE_SHA256 = "09101fcad5a63a09ba349f188fa9d66677a933a20f55c51251231f181120fc2f"
BEGIN = "// QB_PROFILE_BEGIN\n"
END = "// QB_PROFILE_END\n"

def instrument(raw):
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
        raise ValueError("unexpected_sparse_source")
    original=raw.decode(); source=original
    def insert(anchor, code, after=False):
        nonlocal source
        if source.count(anchor)!=1: raise ValueError("profile_anchor")
        block=BEGIN+code+"\n"+END
        source=source.replace(anchor,anchor+block if after else block+anchor)
    insert('#include <cassert>\n', '#include <chrono>\n#include <map>\n#include <iostream>', True)
    insert('    xacc::quantum::SparseSimVisitor visitor(buffer->size());\n', r'''    using Clock = std::chrono::steady_clock;
    const auto started = Clock::now();
    const auto elapsed = [&]() { return std::chrono::duration_cast<std::chrono::microseconds>(Clock::now()-started).count(); };
    std::map<const xacc::Instruction*, size_t> roots;
    for (size_t i=0; i<compositeInstruction->nInstructions(); ++i)
      roots.emplace(compositeInstruction->getInstruction(i).get(), i);
    size_t nodes=0, enabled=0, accepts=0, phase=0;
    struct Cost { size_t calls=0; long long ns=0; };
    std::map<std::string, Cost> costs;
    const auto summary = [&](const char* event) {
      std::cout << "SPARSE_PROFILE " << event << " elapsed_us=" << elapsed()
                << " phase=" << phase << " nodes=" << nodes << " enabled=" << enabled
                << " accepts=" << accepts << std::endl;
      for (const auto& [name,cost] : costs)
        std::cout << "SPARSE_COST phase=" << phase << " gate=" << name
                  << " calls=" << cost.calls << " accept_ns=" << cost.ns << std::endl;
      costs.clear();
    };
    std::cout << "SPARSE_PROFILE begin elapsed_us=" << elapsed() << " phase=0 nodes=0 enabled=0 accepts=0" << std::endl;''')
    insert('      auto nextInst = it.next();\n', r'''      ++nodes;
      auto root=roots.find(nextInst.get());
      if (root!=roots.end() && root->second!=phase) {
        summary("phase_end"); phase=root->second;
      }
      if (nodes % 131072 == 0) summary("progress");''', True)
    insert('      if (nextInst->isEnabled()) {\n', '        ++enabled;', True)
    insert('          nextInst->accept(&visitor);\n', '          const auto before=Clock::now();')
    insert('          nextInst->accept(&visitor);\n', r'''          const auto duration=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now()-before).count();
          auto& cost=costs[nextInst->name()]; ++cost.calls; cost.ns+=duration; ++accepts;''', True)
    insert('    const auto measurements = visitor.sample(measureBitIdxs, m_shots);\n', '    summary("sample_begin");')
    insert('    const auto measurements = visitor.sample(measureBitIdxs, m_shots);\n', '    summary("sample_end");', True)
    restored=source
    while BEGIN in restored:
        a=restored.index(BEGIN);b=restored.index(END,a)+len(END)
        restored=restored[:a]+restored[b:]
    if restored!=original: raise ValueError("non_trace_change")
    patch=''.join(difflib.unified_diff(original.splitlines(True),source.splitlines(True),fromfile='SparseStateVecAccelerator.cpp',tofile='SparseStateVecAccelerator.profile.cpp'))
    encoded=source.encode()
    return encoded,patch,dict(source_sha256=SOURCE_SHA256,derived_sha256=hashlib.sha256(encoded).hexdigest(),patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),algorithm_statements_unchanged=True)
