#pragma once
#include <map>
#include <iomanip>
#include "GateModifier.hpp"
namespace qb_inventory {
struct Stats {size_t nodes=0,leaves=0,eligible=0,estimated=0;std::map<std::string,size_t> names;};
inline void count(std::shared_ptr<xacc::Instruction> node,Stats& s,int depth=0,bool executable=true) {
  if(depth>128||++s.nodes>1000000)throw std::runtime_error("inventory_bound");
  if(!node->isComposite()){++s.leaves;if(executable&&node->isEnabled())++s.estimated;return;}
  ++s.names[node->name()];
  if(executable&&node->isEnabled())++s.estimated;
  bool direct=false;
  if(auto mod=dynamic_cast<xacc::quantum::ControlModifier*>(node.get())) {
    auto base=mod->getBaseInstruction();
    if(base&&base->isComposite()&&xacc::ir::asComposite(base)->nInstructions()==1) {
      auto gate=xacc::ir::asComposite(base)->getInstruction(0);
      const std::set<std::string> allowed{"X","Y","Z","H","Rx","Ry","Rz"};
      direct=allowed.count(gate->name())>0;
      if(direct)++s.eligible;
    }
  }
  for(auto child:xacc::ir::asComposite(node)->getInstructions())count(child,s,depth+1,executable&&node->isEnabled()&&!direct);
}
inline void emit(const char* kind,size_t index,std::shared_ptr<xacc::Instruction> circuit) {
  Stats s;count(circuit,s);
  std::cout<<"PREPARATION_INVENTORY {\"kind\":"<<std::quoted(kind)<<",\"index\":"<<index<<",\"name\":"<<std::quoted(circuit->name())<<",\"nodes\":"<<s.nodes<<",\"primitive_leaves\":"<<s.leaves<<",\"eligible_control_blocks\":"<<s.eligible<<",\"estimated_sparse_visits\":"<<s.estimated<<",\"composite_names\":{";
  bool first=true;for(auto [name,n]:s.names){if(!first)std::cout<<',';first=false;std::cout<<std::quoted(name)<<':'<<n;}std::cout<<"}}"<<std::endl;
}
inline void inventory(std::shared_ptr<xacc::CompositeInstruction> preparation) {
  emit("preparation",0,preparation);
  size_t index=0;for(auto child:preparation->getInstructions())emit("child",index++,child);
  auto inverse=std::dynamic_pointer_cast<xacc::CompositeInstruction>(xacc::getService<xacc::Instruction>("InverseCircuit"));
  if(!inverse||!inverse->expand({{"circ",preparation}}))throw std::runtime_error("inventory_inverse_failed");
  emit("legacy_inverse",0,inverse);
  std::cout<<"PREPARATION_INVENTORY_COMPLETE: construction only; no search or simulation"<<std::endl;
}
}
