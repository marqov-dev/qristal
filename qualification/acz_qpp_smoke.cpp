#include "xacc.hpp"
#include "xacc_service.hpp"
#include <iostream>
#include <stdexcept>
int main(int argc, char** argv) {
  const bool installed = argc == 2 && std::string(argv[1]) == "--installed";
  if (!installed) {
  xacc::addPluginSearchPath("/work/build-xacc/quantum/gate");
  xacc::addPluginSearchPath("/work/build-xacc/quantum/annealing");
  xacc::addPluginSearchPath("/work/build-xacc/quantum/provider");
  xacc::addPluginSearchPath("/work/build-xacc/quantum/plugins/qpp");
  xacc::addPluginSearchPath("/work/build-xacc/xacc/utils/exprtk_parsing");
  }
  xacc::Initialize();
  auto provider=xacc::getIRProvider("quantum");
  auto accelerator=xacc::getAccelerator("qpp",{{"shots",1024}});
  unsigned checked=0;
  for(unsigned control=0;control<2;++control) for(unsigned control_value=0;control_value<2;++control_value) {
    unsigned target=1-control;
    auto circuit=provider->createComposite("acz_interference");
    auto add=[&](const std::string& name,std::vector<std::size_t> bits){circuit->addInstruction(provider->createInstruction(name,bits));};
    if(control_value)add("X",{control});
    add("H",{target});
    add("ACZ",{control,target});
    add("H",{target});
    add("Measure",{0});add("Measure",{1});
    auto buffer=xacc::qalloc(2);accelerator->execute(buffer,circuit);
    // qpp emits q0 first; target flips only when control is zero.
    std::string expected="00";expected[control]='0'+control_value;expected[target]='0'+(1-control_value);
    auto counts=buffer->getMeasurementCounts();
    if(counts.size()!=1 || counts[expected]!=1024) {buffer->print();throw std::runtime_error("ACZ interference mismatch");}
    ++checked;
  }
  auto bell=provider->createComposite("bell");
  bell->addInstruction(provider->createInstruction("H",{0}));
  bell->addInstruction(provider->createInstruction("CNOT",{0,1}));
  bell->addInstruction(provider->createInstruction("Measure",{0}));
  bell->addInstruction(provider->createInstruction("Measure",{1}));
  auto buffer=xacc::qalloc(2);accelerator->execute(buffer,bell);auto counts=buffer->getMeasurementCounts();
  if(counts.size()!=2 || counts["00"]+counts["11"]!=1024 || counts["00"]<300 || counts["11"]<300)throw std::runtime_error("Bell mismatch");
  std::cout<<"PASS: ACZ registered, four interference circuits and Bell executed using rebuilt upstream qpp. Bell "<<counts["00"]<<"/"<<counts["11"]<<"\n";
  std::cout << "Plugin source: " << (installed ? "installed prefix" : "build tree") << "\n";
  xacc::Finalize();
}
