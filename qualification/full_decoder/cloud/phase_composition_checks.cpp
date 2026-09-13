// Reuse the pinned qualification helpers; this is a separate native protocol.
#define main inverse_fixture_main
#include "inverse_checks.cpp"
#undef main

int main(int argc,char** argv) {
  std::cout<<std::setprecision(17);xacc::Initialize(argc,argv);
  try {
    gates=xacc::getIRProvider("quantum");
#ifdef __linux__
    dl_iterate_phdr([](dl_phdr_info* info,size_t,void*){if(std::string(info->dlpi_name).starts_with("/work/"))std::cout<<"LOADED_RUNTIME_LIBRARY: "<<info->dlpi_name<<std::endl;return 0;},nullptr);
#endif
    auto qpp=xacc::getAccelerator("qpp");int candidates=0,legacy_cases=0;
    for(double angle:{.37,-.37,.9,-.9})for(std::string route:{"candidate","legacy"}) {
      auto circuit=gates->createComposite("phase_composition");
      // Inner control 0 is 1; outer control 2 is coherent. Target 1 starts 0.
      circuit->addInstruction(gates->createInstruction("X",{0}));
      circuit->addInstruction(gates->createInstruction("H",{2}));
      if(route=="candidate") {
        circuit->addInstruction(std::make_shared<DirectControlled>(3,std::vector<int>{0,2},1,"Rx",-angle));
      } else {
        auto inverse=primitive_inverse(Layout{3,{0},1},"Rx",angle);
        auto outer=std::dynamic_pointer_cast<xacc::CompositeInstruction>(xacc::getService<xacc::Instruction>("C-U"));
        require(outer&&outer->expand({{"U",inverse},{"control-idx",2}}),"outer_expand_failed");
        // This is controlled compiled IR, deliberately distinct from controlling
        // the original single-gate metadata before decomposition.
        auto flat=gates->createComposite("outer_primitive");
        xacc::InstructionIterator it(outer);
        while(it.hasNext()){auto node=it.next();if(node->isEnabled()&&!node->isComposite())flat->addInstruction(node->clone());}
        require(flat->nInstructions()>0,"outer_empty");circuit->addInstruction(flat);
      }
      circuit->addInstruction(std::make_shared<DirectControlled>(3,std::vector<int>{0,2},1,"Rx",angle));
      circuit->addInstruction(gates->createInstruction("H",{2}));
      circuit=composite(lower_qpp(circuit));
      for(int repetition=0;repetition<2;++repetition) {
        qpp->execute(xacc::qalloc(3),circuit);
        auto wave=qpp->getExecutionInfo<xacc::ExecutionInfo::WaveFuncPtrType>(xacc::ExecutionInfo::WaveFuncKey);
        require(wave&&wave->size()==8,"composition_shape");double p1=0;
        for(size_t x=0;x<8;++x){require(std::isfinite(wave->at(x).real())&&std::isfinite(wave->at(x).imag()),"nonfinite_state");if(x&4)p1+=std::norm(wave->at(x));}
        if(route=="candidate")require(p1<1e-20,"candidate_interference_failed");
        if(repetition==1){std::cout<<"COMPOSITION {\"route\":\""<<route<<"\",\"angle\":"<<angle<<",\"outer_one_probability\":"<<p1<<",\"amplitudes\":[";for(size_t x=0;x<8;++x){if(x)std::cout<<',';std::cout<<'['<<wave->at(x).real()<<','<<wave->at(x).imag()<<']';}std::cout<<"]}"<<std::endl;}
      }
      if(route=="candidate")++candidates;else ++legacy_cases;
    }
    std::cout<<"PASS: "<<candidates<<" candidate interference checks; "<<legacy_cases<<" legacy composition observations"<<std::endl;
    xacc::Finalize();return 0;
  }catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<std::endl;return 1;}
}
