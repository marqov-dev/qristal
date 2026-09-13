#include <qristal/core/session.hpp>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

int main() {
  for (const bool bell : {false, true}) {
    qristal::session sim;
    sim.qn = 2; sim.sn = 256; sim.acc = "qpp";
    sim.noplacement = true; sim.nooptimise = true;
    sim.instring = std::string("__qpu__ void probe(qreg q) { OPENQASM 2.0; include \"qelib1.inc\"; creg c[2]; ")
      + (bell ? "h q[0]; cx q[0], q[1]; " : "")
      + "measure q[0] -> c[0]; measure q[1] -> c[1]; }";
    sim.run();
    int total = 0;
    std::map<std::string, int> counts;
    for (const auto& [bits, count] : sim.results()) {
      if (bits.size() != 2 || count < 0) throw std::runtime_error("invalid counts");
      std::string key;
      for (const bool bit : bits) key += bit ? '1' : '0';
      counts[key] += count; total += count;
    }
    if (total != 256 || counts.size() != (bell ? 2u : 1u) || counts["00"] <= 0
        || (bell && counts["11"] <= 0)) throw std::runtime_error("fixture counts mismatch");
    std::cout << "CORE_CPP " << (bell ? "bell" : "identity") << " shots=" << total << '\n';
  }
  std::cout << "PASS: installed Core C++ QPP identity and Bell\n";
}
