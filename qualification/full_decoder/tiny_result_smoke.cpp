#include <qristal/decoder/quantum_decoder.hpp>
#include <iostream>
#include <stdexcept>

// Predeclared result-contract smoke. Run only under an external time/resource bound.
int main(int argc, char** argv) {
  xacc::Initialize(argc, argv);
  try {
    auto backend = xacc::getAccelerator("sparse-sim", {{"shots",1}});
    qristal::QuantumDecoder decoder;
    std::vector<int> ancilla(15);
    std::iota(ancilla.begin(), ancilla.end(), 9);
    if (!decoder.initialize({
        {"probability_table", std::vector<std::vector<float>>{{0,1}}},
        {"iteration",1}, {"N_TRIALS",4}, {"method",std::string("canonical")},
        {"BestScore",0}, {"qubits_metric",std::vector<int>{0}},
        {"qubits_string",std::vector<int>{1}}, {"qubits_init_null",std::vector<int>{2}},
        {"qubits_init_repeat",std::vector<int>{3}}, {"qubits_superfluous_flags",std::vector<int>{4}},
        {"qubits_total_metric_buffer",std::vector<int>{}},
        {"qubits_beam_metric",std::vector<int>{5,6}},
        {"qubits_best_score",std::vector<int>{7,8}}, {"qubits_ancilla_pool",ancilla},
        {"qpu",backend}})) throw std::runtime_error("tiny fixture initialization rejected");
    auto buffer = xacc::qalloc(24);
    decoder.execute(buffer);
    const auto info = buffer->getInformation();
    const bool found = info.at("has-improving-candidate").as<bool>();
    const int score = info.at("best-score").as<int>();
    const auto bits = info.at("best-string").as<std::string>();
    if (info.at("initial-score").as<int>() != 0 ||
        info.at("trials-completed").as<int>() != 4 ||
        info.at("method").as<std::string>() != "canonical" ||
        info.at("result-kind").as<std::string>() != "quantized-search-observation")
      throw std::runtime_error("invalid caller result metadata");
    if (found) {
      if (score <= 0 || score > 3 || bits != "1")
        throw std::runtime_error("improving candidate disagrees with deterministic oracle");
      std::cout << "OBSERVATION: tiny-oracle-candidate score=" << score << " bits=1\n";
    } else {
      if (score != 0 || !bits.empty()) throw std::runtime_error("invalid no-improvement result");
      std::cout << "INCONCLUSIVE: no improving candidate in four trials\n";
    }
    std::cout << "PASS: caller result contract (not full Decoder correctness)\n";
  } catch (const std::exception& e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    xacc::Finalize();
    return 1;
  }
  xacc::Finalize();
  return 0;
}
