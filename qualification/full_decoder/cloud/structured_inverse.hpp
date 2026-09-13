// Qualification-only controlled-gate representation. Not a generic IR format.
#pragma once
#include "direct_mcz.hpp"
#include <cmath>

namespace qb_qualification {
inline bool rotation(const std::string& name) {
  return name=="Rx" || name=="Ry" || name=="Rz";
}
inline bool supported(const std::string& name) {
  return rotation(name) || name=="X" || name=="Y" || name=="Z" || name=="H";
}
class DirectControlled final : public xacc::quantum::Circuit,
                               public xacc::quantum::ControlModifier {
  int n_,target_; std::vector<int> controls_; std::string gate_;
  double angle_; bool enabled_=true;
public:
  DirectControlled(int n,std::vector<int> controls,int target,std::string gate,double angle=0)
    :Circuit("C-U"),n_(n),target_(target),controls_(std::move(controls)),gate_(gate),angle_(angle) {
    validate(n_,controls_,target_);
    if(!supported(gate_) || !std::isfinite(angle_) || (!rotation(gate_) && angle_!=0))
      throw std::invalid_argument("controlled_gate");
  }
  bool isEnabled() override{return enabled_;}
  void enable() override{enabled_=true;}
  void disable() override{enabled_=false;}
  std::vector<std::pair<std::string,size_t>> getControlQubits() const override {
    std::vector<std::pair<std::string,size_t>> result;
    for(int bit:controls_)result.emplace_back("q",bit);
    return result;
  }
  std::shared_ptr<xacc::Instruction> getBaseInstruction() const override {
    auto gates=xacc::getIRProvider("quantum");auto base=gates->createComposite("base");
    auto gate=rotation(gate_) ? gates->createInstruction(gate_,{size_t(target_)},{angle_})
                              :gates->createInstruction(gate_,{size_t(target_)});
    gate->setBufferNames({"q"});base->addInstruction(gate);return base;
  }
  std::shared_ptr<xacc::Instruction> clone() override {
    auto copy=std::make_shared<DirectControlled>(n_,controls_,target_,gate_,angle_);
    if(!enabled_)copy->disable();return copy;
  }
  void mapBits(std::vector<size_t> map) override {
    std::set<size_t> seen(map.begin(),map.end());
    if(map.size()!=size_t(n_) || seen.size()!=map.size() || *seen.rbegin()>=map.size())
      throw std::invalid_argument("controlled_map");
    for(int& bit:controls_)bit=map[bit];target_=map[target_];
  }
};

inline std::shared_ptr<xacc::Instruction> structured_inverse(
    const std::shared_ptr<xacc::Instruction>& input,int n) {
  if(!input)throw std::invalid_argument("inverse_null");
  if(input->isComposite()) {
    auto c=xacc::ir::asComposite(input);
    if(input->name()=="C-U") {
      auto modifier=dynamic_cast<xacc::quantum::ControlModifier*>(input.get());
      if(!modifier)throw std::invalid_argument("inverse_control_metadata");
      auto base=modifier->getBaseInstruction();
      if(!base || !base->isComposite() || xacc::ir::asComposite(base)->nInstructions()!=1)
        throw std::invalid_argument("inverse_control_base");
      auto gate=xacc::ir::asComposite(base)->getInstruction(0);
      if(gate->isComposite() || gate->bits().size()!=1 || gate->getBufferNames()!=std::vector<std::string>{"q"})
        throw std::invalid_argument("inverse_control_register");
      std::vector<int> controls;
      for(const auto& [reg,bit]:modifier->getControlQubits()) {
        if(reg!="q" || bit>=size_t(n))throw std::invalid_argument("inverse_control_register");
        controls.push_back(int(bit));
      }
      if(gate->bits()[0]>=size_t(n))throw std::invalid_argument("inverse_control_register");
      double angle=rotation(gate->name()) ? -gate->getParameter(0).as<double>():0;
      auto result=std::make_shared<DirectControlled>(n,controls,int(gate->bits()[0]),gate->name(),angle);
      if(!input->isEnabled())result->disable();return result;
    }
    if(c->nInstructions()==0)throw std::invalid_argument("inverse_empty_unknown");
    auto result=xacc::getIRProvider("quantum")->createComposite("structured_inverse");
    const auto children=c->getInstructions();
    for(auto it=children.rbegin();it!=children.rend();++it)
      result->addInstruction(structured_inverse(*it,n));
    if(!input->isEnabled())result->disable();return result;
  }
  if(!supported(input->name()) || input->bits().size()!=1 || input->bits()[0]>=size_t(n))
    throw std::invalid_argument("inverse_unsupported_leaf");
  auto result=input->clone();
  if(rotation(input->name())) {
    const double angle=input->getParameter(0).as<double>();
    if(!std::isfinite(angle))throw std::invalid_argument("inverse_nonfinite");
    result->setParameter(0,-angle);
  }
  return result;
}
} // namespace qb_qualification
