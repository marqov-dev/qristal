// Qualification prototype only. Do not export this representation or dispatch
// it to a backend that has not implemented ControlModifier visitation.
#pragma once
#include "xacc.hpp"
#include "xacc_service.hpp"
#include "Circuit.hpp"
#include "GateModifier.hpp"
#include "IRProvider.hpp"
#include <numeric>
#include <set>
#include <stdexcept>

namespace qb_qualification {
inline void validate(int n, const std::vector<int>& controls, int target) {
  if (n < 2 || target < 0 || target >= n || controls.empty())
    throw std::invalid_argument("mcz_shape");
  std::set<int> seen;
  for (int bit : controls)
    if (bit < 0 || bit >= n || bit == target || !seen.insert(bit).second)
      throw std::invalid_argument("mcz_controls");
}

class DirectMCZ final : public xacc::quantum::Circuit,
                        public xacc::quantum::ControlModifier {
  int n_, target_;
  std::vector<int> controls_;
public:
  DirectMCZ(int n, std::vector<int> controls, int target)
      : Circuit("C-U"), n_(n), target_(target), controls_(std::move(controls)) {
    validate(n_, controls_, target_);
  }
  std::shared_ptr<xacc::Instruction> getBaseInstruction() const override {
    auto gates = xacc::getIRProvider("quantum");
    auto base = gates->createComposite("z_gate");
    auto z = gates->createInstruction("Z", {static_cast<size_t>(target_)});
    z->setBufferNames({"q"});
    base->addInstruction(z);
    return base;
  }
  std::vector<std::pair<std::string, size_t>> getControlQubits() const override {
    std::vector<std::pair<std::string, size_t>> result;
    for (int bit : controls_) result.emplace_back("q", bit);
    return result;
  }
  std::shared_ptr<xacc::Instruction> clone() override {
    auto copy = std::make_shared<DirectMCZ>(n_, controls_, target_);
    if (!isEnabled()) copy->disable();
    return copy;
  }
  void mapBits(std::vector<size_t> map) override {
    // This narrow prototype accepts full register permutations only.
    if (map.size() != static_cast<size_t>(n_)) throw std::invalid_argument("mcz_map");
    std::set<size_t> seen(map.begin(), map.end());
    if (seen.size() != map.size() || *seen.rbegin() >= map.size())
      throw std::invalid_argument("mcz_map");
    for (int& bit : controls_) bit = map[bit];
    target_ = map[target_];
  }
};

inline std::shared_ptr<xacc::CompositeInstruction> make_mcz(
    const std::string& backend, int n, const std::vector<int>& controls, int target) {
  validate(n, controls, target);
  if (backend == "qpp" || backend == "sparse-sim")
    return std::make_shared<DirectMCZ>(n, controls, target);
  // Retain the upstream decomposition for all other backend names.
  auto gates = xacc::getIRProvider("quantum");
  auto base = gates->createComposite("z_gate");
  auto z = gates->createInstruction("Z", {static_cast<size_t>(target)});
  z->setBufferNames({"q"});
  base->addInstruction(z);
  auto block = std::dynamic_pointer_cast<xacc::CompositeInstruction>(
      xacc::getService<xacc::Instruction>("C-U"));
  if (!block || !block->expand({{"U", base}, {"control-idx", controls}}))
    throw std::runtime_error("mcz_fallback_failed");
  return block;
}
} // namespace qb_qualification
