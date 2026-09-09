#include "xacc.hpp"
#include "xacc_service.hpp"
#include "Algorithm.hpp"
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
  xacc::Initialize(argc, argv);
  try {
    for (const std::string backend : {"qpp", "aer", "sparse-sim"}) {
      for (const auto& symbols : {std::vector<int>{1,3}, std::vector<int>{1,1,0,1,3}, std::vector<int>{0,0,0,0,0}}) {
        std::vector<std::vector<float>> table;
        std::vector<int> bits;
        for (int symbol : symbols) {
          std::vector<float> row(4,0); row[symbol]=1; table.push_back(row);
          bits.push_back(bits.size()); bits.push_back(bits.size());
        }
        auto acc=xacc::getAccelerator(backend, {{"shots",128}});
        auto decoder=xacc::getAlgorithm("simplified-decoder", {{"probability_table",table},{"qubits_string",bits},{"qpu",acc}});
        auto buffer=xacc::qalloc(bits.size());decoder->execute(buffer);
        auto info=buffer->getInformation();
        const std::string expected = symbols.size()==2 ? "0111" : symbols[0] ? "010111" : "";
        if (info.at("best_beam").as<std::string>() != expected || info.at("nb_beams").as<int>() != 1 || info.at("beam_count_0").as<int>() != 128)
          throw std::runtime_error("Incorrect installed decoder output on " + backend);
        std::cout << "PASS: " << backend << " symbols=" << symbols.size() << " beam=" << expected << std::endl;
      }
    }
  } catch (const std::exception& e) { std::cerr << e.what() << std::endl; xacc::Finalize(); return 1; }
  xacc::Finalize();return 0;
}
