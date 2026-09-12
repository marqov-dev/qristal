#include <qristal/decoder/quantum_decoder.hpp>
#include <iostream>
#include <stdexcept>
#include <chrono>
#ifdef __linux__
#include <link.h>
#include <cstring>
#endif

// Predeclared result-contract smoke. Run only under an external time/resource bound.
int main(int argc, char** argv) {
  std::cout << std::unitbuf;
  const auto start = std::chrono::steady_clock::now();
  auto checkpoint = [&](const char* label) {
    std::cout << "CHECKPOINT " << label << " elapsed_ms="
              << std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-start).count()
              << std::endl;
  };
  checkpoint("initialize_begin");
  xacc::Initialize(argc, argv);
  try {
    checkpoint("initialize_complete");
#ifdef __linux__
    int loaded_search_libraries = 0;
    dl_iterate_phdr([](dl_phdr_info* info, size_t, void* data) {
      if (std::strstr(info->dlpi_name, "libalgorithm_es.so")) {
        ++*static_cast<int*>(data);
        std::cout << "LOADED_CORE_LIBRARY: " << info->dlpi_name << std::endl;
      }
      return 0;
    }, &loaded_search_libraries);
    if (loaded_search_libraries != 1)
      throw std::runtime_error("expected exactly one loaded Core search library");
#endif
    for (const std::string service : {"qft", "iqft"}) {
      if (!xacc::hasService<xacc::Instruction>(service))
        throw std::runtime_error("missing required public XACC service: " + service);
      std::cout << "SERVICE_PRESENT: " << service << std::endl;
    }
    if (!xacc::hasService<xacc::Accelerator>("sparse-sim") ||
        !xacc::hasService<xacc::Algorithm>("exponential-search"))
      throw std::runtime_error("required Decoder backend/algorithm missing");
    auto backend = xacc::getAccelerator("sparse-sim", {{"shots",1}});
    checkpoint("services_ready");
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
    checkpoint("decoder_initialized");
    auto buffer = xacc::qalloc(24);
    checkpoint("decoder_execute_begin");
    decoder.execute(buffer);
    checkpoint("decoder_execute_complete");
    const auto info = buffer->getInformation();
    const int candidate_flag = info.at("has-improving-candidate").as<int>();
    if (candidate_flag != 0 && candidate_flag != 1)
      throw std::runtime_error("candidate flag must be encoded as integer 0 or 1");
    const bool found = candidate_flag == 1;
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
