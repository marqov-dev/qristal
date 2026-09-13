"""Hash-bound, observation-only sparse diagnostic derivatives."""
import hashlib
from instrument_sparse import SOURCE_SHA256 as VISITOR_SHA
HEADER_SHA = "d5ca70133540351ec8619ee95a3f161c850826cb565d199f8440ac7da751f4ca"
BEGIN='// QB_STATE_BEGIN\n'
END='// QB_STATE_END\n'

def derive(raw, expected, insertions):
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('source_identity')
    original=raw.decode();source=original
    for anchor,code in insertions:
        if source.count(anchor)!=1:raise ValueError('probe_anchor')
        source=source.replace(anchor,BEGIN+code+'\n'+END+anchor)
    restored=source
    while BEGIN in restored:
        a=restored.index(BEGIN);b=restored.index(END,a)+len(END)
        restored=restored[:a]+restored[b:]
    if restored!=original:raise ValueError('non_observation_change')
    return source.encode()

def header(raw):
    return derive(raw,HEADER_SHA,[('\tstd::set<std::string> operations_done;',r'''    struct QBStats { size_t states, operations, h, rx, ry;
      bool operator==(const QBStats&) const = default; };
    QBStats qb_stats() const {
      return {_quantum_state->get_wavefunction_size(), _queued_operations.size(),
        static_cast<size_t>(std::count(_queue_H.begin(),_queue_H.end(),true)),
        static_cast<size_t>(std::count(_queue_Rx.begin(),_queue_Rx.end(),true)),
        static_cast<size_t>(std::count(_queue_Ry.begin(),_queue_Ry.end(),true))};
    }''')])

def visitor(raw):
    return derive(raw,VISITOR_SHA,[
      ('#include <cassert>', '#include <chrono>\n#include <map>'),
      ('  SparseSimVisitor(size_t nbQubits)', '  auto qb_stats() const { return m_sim.qb_stats(); }'),
      ('    std::vector<size_t> measureBitIdxs;',r'''    using Clock=std::chrono::steady_clock;
    const auto begin=Clock::now();
    size_t nodes=0,phase=0;
    std::map<const xacc::Instruction*,size_t> roots;
    for(size_t i=0;i<compositeInstruction->nInstructions();++i)
      roots.emplace(compositeInstruction->getInstruction(i).get(),i);
    auto observe=[&](const char* event) {
      const auto s=visitor.qb_stats();
      std::cout<<"SPARSE_STATE {\"event\":\""<<event<<"\",\"phase\":"<<phase
        <<",\"nodes\":"<<nodes<<",\"elapsed_us\":"
        <<std::chrono::duration_cast<std::chrono::microseconds>(Clock::now()-begin).count()
        <<",\"states\":"<<s.states<<",\"operations\":"<<s.operations
        <<",\"h\":"<<s.h<<",\"rx\":"<<s.rx<<",\"ry\":"<<s.ry<<"}"<<std::endl;
    };
    observe("begin");'''),
      ('      if (nextInst->isEnabled()) {',r'''      ++nodes;
      auto root=roots.find(nextInst.get());
      if(root!=roots.end()&&root->second!=phase) {
        observe("phase_end");phase=root->second;observe("phase_begin");
      }
      if(nodes%8192==0)observe("sample");'''),
      ('    const auto measurements = visitor.sample(measureBitIdxs, m_shots);','    observe("sample_begin");'),
      ('    buffer->setMeasurements(measurements);','    observe("sample_end");')])
