#include "direct_mcz.hpp"
#include <qristal/core/circuit_builder.hpp>
#include <cmath>
#include <complex>
#include <iomanip>
#include <iostream>
#ifdef __linux__
#include <link.h>
#endif
#include <cstring>

using CircuitPtr = std::shared_ptr<xacc::CompositeInstruction>;
struct Layout { int n; std::vector<int> controls; int target; };
const std::vector<Layout> layouts{{2,{0},1},{3,{1,2},0},{4,{0,1,3},2},
                                {5,{0,1,2,3},4},{5,{4,0},2},{5,{0,4},2}};
void require(bool ok, const char* reason) { if (!ok) throw std::runtime_error(reason); }
CircuitPtr clone(CircuitPtr c) { return xacc::ir::asComposite(c->clone()); }
CircuitPtr block_for(const std::string& backend, const Layout& l, const std::string& mode) {
  auto c = qb_qualification::make_mcz(mode=="fallback" ? "unqualified-backend" : backend,
                                     l.n,l.controls,l.target);
  if (mode=="fallback") {
    require(c->nInstructions()>0,"fallback_not_materialized");
    auto flat=xacc::getIRProvider("quantum")->createComposite("fallback_leaves");
    xacc::InstructionIterator it(c);
    while(it.hasNext()) {auto next=it.next();if(!next->isComposite() && next->isEnabled())flat->addInstruction(next->clone());}
    require(flat->nInstructions()>0,"fallback_empty");
    return flat; // Force actual primitive execution, not backend metadata shortcut.
  }
  else require(c->nInstructions()==0,"direct_unexpected_children");
  if (mode=="clone") {
    auto copied=clone(c);
    c->disable();
    require(copied->isEnabled(),"clone_state_alias");
    c=copied;
  }
  if (mode=="inverse") {
    auto inv=std::dynamic_pointer_cast<xacc::CompositeInstruction>(
        xacc::getService<xacc::Instruction>("InverseCircuit"));
    require(inv && inv->expand({{"circ",c}}),"inverse_failed");
    c=inv;
  }
  if (mode=="disabled") c->disable();
  if (mode=="mapped") {
    std::vector<size_t> map(l.n);
    for (int bit=0;bit<l.n;++bit) map[bit]=l.n-1-bit;
    c->mapBits(map);
  }
  return c;
}
Layout effective(Layout l, const std::string& mode) {
  if (mode=="mapped") {
    for (int& bit:l.controls) bit=l.n-1-bit;
    l.target=l.n-1-l.target;
  }
  return l;
}
void print_layout(const Layout& l) {
  std::cout << "\"qubits\":" << l.n << ",\"target\":" << l.target << ",\"controls\":[";
  for (size_t i=0;i<l.controls.size();++i) {if(i)std::cout<<',';std::cout<<l.controls[i];}
  std::cout<<']';
}
void qpp_checks() {
  auto gates=xacc::getIRProvider("quantum"); auto qpp=xacc::getAccelerator("qpp");
  int cases=0;
  for (size_t index=0;index<layouts.size();++index) {
    const auto l=layouts[index];
    for (const std::string mode:{"direct","clone","inverse","pair","fallback","disabled","mapped"}) {
      const auto e=effective(l,mode);
      auto circuit=gates->createComposite("mcz_complex_check");
      // Product state has nonzero, complex amplitudes on every computational basis input.
      for (int bit=0;bit<l.n;++bit) {
        circuit->addInstruction(gates->createInstruction("H",{static_cast<size_t>(bit)}));
        circuit->addInstruction(gates->createInstruction("Rz",{static_cast<size_t>(bit)},
                                {0.13*(bit+1)}));
      }
      auto block=block_for("qpp",l,mode);
      auto wrapper=gates->createComposite("nested_wrapper"); wrapper->addInstruction(block);
      if(mode=="pair")wrapper->addInstruction(clone(block));
      circuit->addInstruction(wrapper);
      if(mode!="disabled") {
        auto used=qristal::uniqueBitsQD(wrapper);
        std::set<size_t> expected(e.controls.begin(),e.controls.end());expected.insert(e.target);
        require(used==expected,"used_bit_metadata");
      }
      // Repeat the very same IR object: visitors must restore temporary disable state.
      for(int repetition=0;repetition<2;++repetition) {
        qpp->execute(xacc::qalloc(l.n),circuit);
        auto wave=qpp->getExecutionInfo<xacc::ExecutionInfo::WaveFuncPtrType>(xacc::ExecutionInfo::WaveFuncKey);
        require(wave && wave->size()==size_t(1<<l.n),"wave_shape");
        double maximum=0,norm=0;
        for(int basis=0;basis<(1<<l.n);++basis) {
          double phase=0;
          for(int bit=0;bit<l.n;++bit)phase+=((basis>>bit)&1 ? 1:-1)*0.13*(bit+1)/2;
          auto expected=std::polar(1/std::sqrt(double(1<<l.n)),phase);
          bool active=(basis>>e.target)&1;
          for(int bit:e.controls)active=active && ((basis>>bit)&1);
          if(active && mode!="pair" && mode!="disabled")expected=-expected;
          const auto v=wave->at(basis);
          require(std::isfinite(v.real())&&std::isfinite(v.imag()),"nonfinite");
          maximum=std::max(maximum,std::abs(v-expected));norm+=std::norm(v);
        }
        require(maximum<1e-10 && std::abs(norm-1)<1e-10,"phase_oracle_mismatch");
        if(repetition==1) {
          std::cout<<"MCZ_STATE {\"layout\":"<<index<<",\"mode\":\""<<mode<<"\",";
          print_layout(e);std::cout<<",\"max_abs_error\":"<<maximum<<",\"amplitudes\":[";
          for(size_t k=0;k<wave->size();++k) {if(k)std::cout<<',';std::cout<<'['<<wave->at(k).real()<<','<<wave->at(k).imag()<<']';}
          std::cout<<"]}\n";
        }
      }
      ++cases;
    }
  }
  require(cases==42,"qpp_case_count");std::cout<<"PASS: 42 MCZ complex-state cases, each repeated twice\n";
}
void sparse_checks() {
  auto gates=xacc::getIRProvider("quantum");
  auto sparse=xacc::getAccelerator("sparse-sim",{{"shots",64}});
  int cases=0;
  for(int k:{1,2,3,4,18}) {
    Layout l{k+1,{},k};for(int bit=0;bit<k;++bit)l.controls.push_back(bit);
    std::vector<int> patterns;
    if(k==18)patterns={(1<<k)-1,(1<<k)-2};
    else for(int p=0;p<(1<<k);++p)patterns.push_back(p);
    for(int pattern:patterns)for(const std::string mode:{"direct","clone","inverse","pair","fallback"}) {
      if(k==18 && mode=="fallback")continue; // Do not recreate the measured eager-expansion stall.
      auto circuit=gates->createComposite("mcz_interference");
      for(int bit=0;bit<k;++bit)if((pattern>>bit)&1)
        circuit->addInstruction(gates->createInstruction("X",{static_cast<size_t>(bit)}));
      circuit->addInstruction(gates->createInstruction("H",{static_cast<size_t>(k)}));
      auto block=block_for("sparse-sim",l,mode);
      auto wrapper=gates->createComposite("nested_wrapper");wrapper->addInstruction(block);
      if(mode=="pair")wrapper->addInstruction(clone(block));
      circuit->addInstruction(wrapper);
      circuit->addInstruction(gates->createInstruction("H",{static_cast<size_t>(k)}));
      for(int bit=0;bit<=k;++bit)circuit->addInstruction(gates->createInstruction("Measure",{static_cast<size_t>(bit)}));
      std::string expected;
      for(int bit=0;bit<k;++bit)expected+=((pattern>>bit)&1)?'1':'0';
      expected+=(pattern==((1<<k)-1)&&mode!="pair")?'1':'0';
      for(int rep=0;rep<2;++rep) {
        auto buffer=xacc::qalloc(l.n);sparse->execute(buffer,circuit);
        require(buffer->getMeasurementCounts()==std::map<std::string,int>{{expected,64}},"sparse_interference_mismatch");
      }
      std::cout<<"MCZ_SPARSE {\"controls\":"<<k<<",\"pattern\":"<<pattern
               <<",\"mode\":\""<<mode<<"\",\"counts\":{\""<<expected<<"\":64}}\n";
      ++cases;
    }
  }
  require(cases==158,"sparse_case_count");std::cout<<"PASS: 158 MCZ sparse interference cases, each repeated twice\n";
}
void negative_checks() {
  int count=0;
  for(const Layout l:std::vector<Layout>{{2,{},1},{3,{0,0},2},{3,{0,1},1},{3,{-1},1},{3,{3},1},{3,{0},3},{1,{0},0}}) {
    bool rejected=false;
    try{qb_qualification::make_mcz("qpp",l.n,l.controls,l.target);}catch(const std::invalid_argument&){rejected=true;}
    require(rejected,"invalid_accepted");++count;
  }
  auto b=qb_qualification::make_mcz("qpp",3,{0,1},2);
  for(const std::vector<size_t> map:std::vector<std::vector<size_t>>{{0,1},{0,0,2},{0,1,3}}) {
    bool rejected=false;try{b->mapBits(map);}catch(const std::invalid_argument&){rejected=true;}
    require(rejected,"map_accepted");++count;
  }
  auto copy=clone(b);b->disable();require(copy->isEnabled(),"clone_disabled_alias");
  auto disabled_copy=clone(b);require(!disabled_copy->isEnabled(),"clone_lost_disabled");
  require(count==10,"negative_count");std::cout<<"PASS: 10 MCZ rejected inputs and clone enabled-state checks\n";
}
int main(int argc,char**argv) {
  std::cout<<std::unitbuf<<std::setprecision(17);
  if(argc!=2)return 2;const std::string mode=argv[1];
  xacc::Initialize();
  try {
#ifdef __linux__
    dl_iterate_phdr([](dl_phdr_info*info,size_t,void*) {
      if(std::strncmp(info->dlpi_name,"/work/",6)==0)std::cout<<"LOADED_RUNTIME_LIBRARY: "<<info->dlpi_name<<'\n';
      return 0;
    },nullptr);
#endif
    if(mode=="qpp")qpp_checks();else if(mode=="sparse")sparse_checks();
    else if(mode=="negative")negative_checks();else throw std::runtime_error("unknown_mode");
  } catch(const std::exception&e){std::cerr<<"FAIL: "<<e.what()<<'\n';xacc::Finalize();return 1;}
  xacc::Finalize();return 0;
}
