// Phase-sensitive tests of the public QFT provider through installed XACC/QPP.
#include "xacc.hpp"
#include "xacc_service.hpp"
#include "IRProvider.hpp"
#include <algorithm>
#include <cmath>
#include <complex>
#include <iomanip>
#include <iostream>
#include <link.h>
#include <cstring>
#include <stdexcept>

int main(int argc, char** argv) {
  std::cout << std::unitbuf << std::setprecision(17);
  std::cout << "CHECKPOINT qft_initialize_begin\n";
  xacc::Initialize(argc, argv);
  try {
    for (const std::string name : {"qft", "iqft"}) {
      if (!xacc::hasService<xacc::Instruction>(name)) throw std::runtime_error("missing_service:"+name);
      std::cout << "SERVICE_PRESENT: " << name << '\n';
    }
    if (!xacc::hasService<xacc::Accelerator>("qpp")) throw std::runtime_error("missing_qpp");
    int providers = 0;
    dl_iterate_phdr([](dl_phdr_info* info, size_t, void* data) {
      if (std::strstr(info->dlpi_name, "libmarqov_qft_qualification.so")) {
        ++*static_cast<int*>(data);
        std::cout << "LOADED_QFT_LIBRARY: " << info->dlpi_name << '\n';
      }
      return 0;
    }, &providers);
    if (providers != 1) throw std::runtime_error("qft_provider_count");
    auto gates = xacc::getIRProvider("quantum");
    auto qpp = xacc::getAccelerator("qpp");
    int cases = 0;
    for (int n=1; n<=3; ++n) {
      const int size = 1 << n;
      for (int input=0; input<size; ++input) {
        for (const std::string mode : {"basis", "qft", "iqft", "qft-iqft", "iqft-qft"}) {
          auto circuit = gates->createComposite("fourier_check");
          for (int bit=0; bit<n; ++bit) if (input & (1 << bit))
            circuit->addInstruction(gates->createInstruction("X", {static_cast<size_t>(bit)}));
          auto add = [&](const std::string& service) {
            auto generated = std::dynamic_pointer_cast<xacc::CompositeInstruction>(
                xacc::getService<xacc::Instruction>(service));
            if (!generated || generated->nInstructions()!=0 || !generated->expand({{"nq",n}}))
              throw std::runtime_error("fresh_expansion_failed:"+service);
            for (const auto& instruction : generated->getInstructions())
              circuit->addInstruction(instruction->clone());
          };
          if (mode=="qft" || mode=="qft-iqft") add("qft");
          if (mode=="iqft" || mode=="qft-iqft" || mode=="iqft-qft") add("iqft");
          if (mode=="iqft-qft") add("qft");
          qpp->execute(xacc::qalloc(n), circuit);
          auto wave = qpp->getExecutionInfo<xacc::ExecutionInfo::WaveFuncPtrType>(xacc::ExecutionInfo::WaveFuncKey);
          if (!wave || wave->size()!=static_cast<size_t>(size)) throw std::runtime_error("wave_shape");
          double max_error=0, norm=0;
          for (int output=0; output<size; ++output) {
            const auto expected = (mode=="qft" || mode=="iqft")
                ? std::polar(1/std::sqrt(double(size)), (mode=="qft" ? 1 : -1)*2*std::acos(-1.0)*input*output/size)
                : std::complex<double>(output==input ? 1 : 0, 0);
            const auto value = wave->at(output);
            if (!std::isfinite(value.real()) || !std::isfinite(value.imag())) throw std::runtime_error("nonfinite_wave");
            max_error=std::max(max_error,std::abs(value-expected));
            norm+=std::norm(value);
          }
          const double tolerance = (mode=="qft" || mode=="iqft") ? 1e-6 : 1e-10;
          std::cout << "QFT_CASE {\"qubits\":" << n << ",\"input\":" << input
                    << ",\"mode\":\"" << mode << "\",\"max_abs_error\":" << max_error
                    << ",\"norm_error\":" << std::abs(norm-1) << ",\"amplitudes\":[";
          for (int output=0; output<size; ++output) {
            if (output) std::cout << ',';
            std::cout << '[' << wave->at(output).real() << ',' << wave->at(output).imag() << ']';
          }
          std::cout << "]}\n";
          if (max_error>tolerance || std::abs(norm-1)>1e-10) throw std::runtime_error("fourier_reference_mismatch");
          ++cases;
        }
      }
    }
    if (cases!=70) throw std::runtime_error("case_count");
    std::cout << "PASS: 70 phase-sensitive QFT cases\n";
  } catch (const std::exception& error) {
    std::cerr << "FAIL: " << error.what() << '\n';
    xacc::Finalize();
    return 1;
  }
  xacc::Finalize();
  return 0;
}
