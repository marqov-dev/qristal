#include "structured_inverse.hpp"
#include <complex>
#include <iomanip>
#include <iostream>
#include <limits>
#ifdef __linux__
#include <link.h>
#endif
using namespace qb_qualification;
using C=std::complex<double>;
using Vec=std::vector<C>;
using Ptr=std::shared_ptr<xacc::CompositeInstruction>;
struct Layout {int n;std::vector<int> controls;int target;};
const std::vector<Layout> layouts{{3,{0},1},{4,{3,0},2}};
const std::vector<std::pair<std::string,double>> ops{{"X",0},{"Y",0},{"Z",0},{"H",0},{"Rx",.37},{"Rx",-.37},{"Ry",.37},{"Ry",-.37},{"Rz",.37},{"Rz",-.37}};
void require(bool b,const char* why){if(!b)throw std::runtime_error(why);}
std::shared_ptr<xacc::IRProvider> gates;
Ptr composite(std::shared_ptr<xacc::Instruction> x){return xacc::ir::asComposite(x);}
// Independent dense 2x2 mathematics; does not use the inverse implementation.
Vec apply(Vec v,Layout l,std::string gate,double angle) {
  C a=1,b=0,c=0,d=1;const C I(0,1);
  if(gate=="X"){a=d=0;b=c=1;}
  else if(gate=="Y"){a=d=0;b=-I;c=I;}
  else if(gate=="Z"){d=-1;}
  else if(gate=="H"){a=b=c=1/std::sqrt(2.);d=-a;}
  else if(gate=="Rx"){a=d=std::cos(angle/2);b=c=-I*std::sin(angle/2);}
  else if(gate=="Ry"){a=d=std::cos(angle/2);b=-std::sin(angle/2);c=-b;}
  else if(gate=="Rz"){a=std::exp(-I*angle/2.);d=std::exp(I*angle/2.);}
  else throw std::runtime_error("oracle_unknown");
  for(int zero=0;zero<(1<<l.n);++zero) {
    if((zero>>l.target)&1)continue;
    bool active=true;for(int control:l.controls)active=active&&((zero>>control)&1);
    if(!active)continue;
    int one=zero|(1<<l.target);auto x=v[zero],y=v[one];v[zero]=a*x+b*y;v[one]=c*x+d*y;
  }
  return v;
}
Vec preparation(int n) {
  Vec v(1<<n);
  for(int x=0;x<(1<<n);++x){double phase=0;for(int bit=0;bit<n;++bit)phase+=((x>>bit)&1?1:-1)*.13*(bit+1)/2.;v[x]=std::polar(1/std::sqrt(double(1<<n)),phase);}
  return v;
}
Ptr populated(Layout l,std::string name,double angle) {
  DirectControlled direct(l.n,l.controls,l.target,name,angle);
  auto block=std::dynamic_pointer_cast<xacc::CompositeInstruction>(xacc::getService<xacc::Instruction>("C-U"));
  require(block&&block->expand({{"U",composite(direct.getBaseInstruction())},{"control-idx",l.controls}}),"fallback_expand");return block;
}
Ptr primitive_inverse(Layout l,std::string name,double angle) {
  auto block=populated(l,name,angle);auto inv=std::dynamic_pointer_cast<xacc::CompositeInstruction>(xacc::getService<xacc::Instruction>("InverseCircuit"));
  require(inv&&inv->expand({{"circ",block}}),"fallback_inverse");
  auto flat=gates->createComposite("forced_primitive");xacc::InstructionIterator it(inv);
  while(it.hasNext()){auto leaf=it.next();if(leaf->isEnabled()&&!leaf->isComposite())flat->addInstruction(leaf->clone());}
  require(flat->nInstructions()>0,"fallback_empty");return flat;
}
// Selected QPP only accepts direct controlled X/Y/Z. Lower H/rotations to
// the existing primitive decomposition, retaining the tested inverse metadata.
std::shared_ptr<xacc::Instruction> lower_qpp(std::shared_ptr<xacc::Instruction> input) {
  if(!input->isEnabled())return gates->createComposite("disabled_lowered");
  if(!input->isComposite())return input->clone();
  if(auto mod=dynamic_cast<xacc::quantum::ControlModifier*>(input.get())) {
    auto base=composite(mod->getBaseInstruction());auto gate=base->getInstruction(0);
    if(gate->name()=="X"||gate->name()=="Y"||gate->name()=="Z")return input->clone();
    std::vector<int> controls;for(auto [reg,bit]:mod->getControlQubits()){require(reg=="q","lower_register");controls.push_back(bit);}
    auto block=std::dynamic_pointer_cast<xacc::CompositeInstruction>(xacc::getService<xacc::Instruction>("C-U"));
    require(block&&block->expand({{"U",base},{"control-idx",controls}}),"lower_failed");return block;
  }
  auto result=gates->createComposite("qpp_lowered");
  for(auto child:composite(input)->getInstructions())result->addInstruction(lower_qpp(child));
  return result;
}
void check_qpp() {
  auto qpp=xacc::getAccelerator("qpp");int cases=0;double all_max=0;
  for(size_t li=0;li<layouts.size();++li)for(size_t oi=0;oi<ops.size();++oi)
  for(const std::string mode:{"inverse","populated","roundtrip","clone","disabled","mapped","fallback","nested"}) {
    auto l=layouts[li],effective=l;auto [name,angle]=ops[oi];
    auto forward=std::make_shared<DirectControlled>(l.n,l.controls,l.target,name,angle);
    auto inverse=composite(structured_inverse(forward,l.n));
    if(mode=="populated")inverse=composite(structured_inverse(populated(l,name,angle),l.n));
    if(mode=="clone"){auto copy=composite(inverse->clone());inverse->disable();inverse=copy;require(inverse->isEnabled(),"clone_alias");}
    if(mode=="disabled"){inverse->disable();inverse=composite(inverse->clone());require(!inverse->isEnabled(),"disabled_clone");}
    if(mode=="mapped") {
      std::vector<size_t> map(l.n);for(int i=0;i<l.n;++i)map[i]=(i+1)%l.n;
      inverse->mapBits(map);for(int& c:effective.controls)c=map[c];effective.target=map[l.target];
      std::set<int> before(l.controls.begin(),l.controls.end()),after(effective.controls.begin(),effective.controls.end());before.insert(l.target);after.insert(effective.target);require(before!=after,"mapping_must_change_active_set");
    }
    if(mode=="fallback")inverse=primitive_inverse(l,name,angle);
    auto circuit=gates->createComposite("test");
    for(int bit=0;bit<l.n;++bit){circuit->addInstruction(gates->createInstruction("H",{size_t(bit)}));circuit->addInstruction(gates->createInstruction("Rz",{size_t(bit)},{.13*(bit+1)}));}
    Vec expected=preparation(l.n);
    if(mode=="nested") {
      auto nested=gates->createComposite("nested");nested->addInstruction(forward);
      nested->addInstruction(std::make_shared<DirectControlled>(l.n,l.controls,l.target,"Ry",.23));
      circuit->addInstruction(structured_inverse(nested,l.n));
      expected=apply(apply(expected,l,"Ry",-.23),l,name,-angle);
    } else {
      if(mode=="roundtrip")circuit->addInstruction(forward);
      circuit->addInstruction(inverse);
      if(mode!="roundtrip"&&mode!="disabled")expected=apply(expected,effective,name,-angle);
    }
    circuit=composite(lower_qpp(circuit));
    double error=0;
    for(int repeat=0;repeat<2;++repeat) {
      qpp->execute(xacc::qalloc(l.n),circuit);
      auto wave=qpp->getExecutionInfo<xacc::ExecutionInfo::WaveFuncPtrType>(xacc::ExecutionInfo::WaveFuncKey);
      require(wave&&wave->size()==expected.size(),"state_shape");
      for(size_t i=0;i<wave->size();++i){require(std::isfinite(wave->at(i).real())&&std::isfinite(wave->at(i).imag()),"state_nonfinite");error=std::max(error,std::abs(wave->at(i)-expected[i]));}
      if(error>=1e-10)std::cerr<<"CASE layout="<<li<<" operation="<<oi<<" mode="<<mode<<" error="<<error<<std::endl;
      require(error<1e-10,"complex_inverse_mismatch");
      if(repeat==1) {
        std::cout<<"INVERSE_CASE {\"layout\":"<<li<<",\"operation\":"<<oi<<",\"mode\":\""<<mode<<"\",\"error\":"<<error;
        if(mode=="inverse"||mode=="fallback"){
          std::cout<<",\"amplitudes\":[";for(size_t i=0;i<wave->size();++i){if(i)std::cout<<',';std::cout<<'['<<wave->at(i).real()<<','<<wave->at(i).imag()<<']';}std::cout<<']';
        }
        std::cout<<"}\n";
      }
    }
    all_max=std::max(all_max,error);++cases;
  }
  require(cases==160,"case_inventory");std::cout<<"PASS: 160 controlled inverse complex-state cases max_error="<<all_max<<std::endl;
}
void check_sparse() {
  auto sparse=xacc::getAccelerator("sparse-sim",{{"shots",64}});int cases=0;
  for(auto l:layouts)for(auto [name,angle]:ops) {
    auto circuit=gates->createComposite("roundtrip");
    for(int bit=0;bit<l.n;++bit)circuit->addInstruction(gates->createInstruction("H",{size_t(bit)}));
    auto forward=std::make_shared<DirectControlled>(l.n,l.controls,l.target,name,angle);
    circuit->addInstruction(forward);circuit->addInstruction(structured_inverse(forward,l.n));
    for(int bit=0;bit<l.n;++bit)circuit->addInstruction(gates->createInstruction("H",{size_t(bit)}));
    for(int bit=0;bit<l.n;++bit)circuit->addInstruction(gates->createInstruction("Measure",{size_t(bit)}));
    for(int repeat=0;repeat<2;++repeat){auto buffer=xacc::qalloc(l.n);sparse->execute(buffer,circuit);auto counts=buffer->getMeasurementCounts();require(counts.size()==1&&counts[std::string(l.n,'0')]==64,"sparse_roundtrip");}
    ++cases;
  }
  std::cout<<"PASS: "<<cases<<" sparse controlled inverse roundtrips, each repeated twice"<<std::endl;
  auto interference=xacc::getAccelerator("sparse-sim",{{"shots",16384}});
  int phase_cases=0;
  for(size_t li=0;li<layouts.size();++li)for(size_t oi=0;oi<ops.size();++oi) {
    auto l=layouts[li];auto [name,angle]=ops[oi];auto circuit=gates->createComposite("sparse_inverse_phase");
    for(int bit=0;bit<l.n;++bit){circuit->addInstruction(gates->createInstruction("H",{size_t(bit)}));circuit->addInstruction(gates->createInstruction("Rz",{size_t(bit)},{.13*(bit+1)}));}
    auto forward=std::make_shared<DirectControlled>(l.n,l.controls,l.target,name,angle);
    circuit->addInstruction(structured_inverse(forward,l.n));
    circuit->addInstruction(gates->createInstruction("H",{size_t(l.target)}));
    for(int bit=0;bit<l.n;++bit)circuit->addInstruction(gates->createInstruction("Measure",{size_t(bit)}));
    auto expected=apply(apply(preparation(l.n),l,name,-angle),Layout{l.n,{},l.target},"H",0);
    auto buffer=xacc::qalloc(l.n);interference->execute(buffer,circuit);auto counts=buffer->getMeasurementCounts();
    double maximum=0;int total=0;
    std::cout<<"INVERSE_SPARSE {\"layout\":"<<li<<",\"operation\":"<<oi<<",\"counts\":[";
    for(int x=0;x<(1<<l.n);++x) {
      std::string bits;for(int bit=0;bit<l.n;++bit)bits+=((x>>bit)&1)?'1':'0';
      int count=counts[bits];total+=count;maximum=std::max(maximum,std::abs(count/16384.-std::norm(expected[x])));
      if(x)std::cout<<',';std::cout<<count;
    }
    std::cout<<"]}"<<std::endl;require(total==16384&&maximum<.025,"sparse_inverse_interference");++phase_cases;
  }
  std::cout<<"PASS: "<<phase_cases<<" sparse inverse interference cases"<<std::endl;

}
void check_negative() {
  int count=0;auto rejects=[&](auto fn){bool caught=false;try{fn();}catch(const std::invalid_argument&){caught=true;}require(caught,"expected_rejection");++count;};
  rejects([]{DirectControlled c(3,{0},1,"U");});
  rejects([]{DirectControlled c(3,{0},1,"Rx",std::numeric_limits<double>::quiet_NaN());});
  rejects([]{DirectControlled c(3,{0},1,"X",.2);});
  rejects([]{DirectControlled c(3,{0,0},1,"X");});
  rejects([]{DirectControlled c(3,{1},1,"X");});
  rejects([]{DirectControlled c(3,{},1,"X");});
  rejects([]{DirectControlled c(3,{0},1,"X");c.mapBits({1,1,0});});
  rejects([]{DirectControlled c(3,{0},1,"X");c.mapBits({1,0});});
  rejects([]{structured_inverse(nullptr,3);});
  rejects([]{structured_inverse(gates->createInstruction("Measure",{0}),3);});
  rejects([]{structured_inverse(gates->createComposite("C-U"),3);});
  rejects([]{structured_inverse(gates->createComposite("opaque"),3);});
  std::cout<<"PASS: "<<count<<" inverse rejected inputs"<<std::endl;
}
int main(int argc,char** argv) {
  std::cout<<std::setprecision(17);xacc::Initialize(argc,argv);
  try {
    gates=xacc::getIRProvider("quantum");
#ifdef __linux__
    dl_iterate_phdr([](dl_phdr_info* info,size_t,void*){if(std::string(info->dlpi_name).starts_with("/work/"))std::cout<<"LOADED_RUNTIME_LIBRARY: "<<info->dlpi_name<<std::endl;return 0;},nullptr);
#endif
    require(argc==2,"mode_required");std::string mode=argv[1];
    if(mode=="negative")check_negative();else if(mode=="qpp")check_qpp();else if(mode=="sparse")check_sparse();else throw std::runtime_error("unknown_mode");
    xacc::Finalize();return 0;
  }catch(const std::exception& e){std::cerr<<"FAIL: "<<e.what()<<std::endl;return 1;}
}
