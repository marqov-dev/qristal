#include <qristal/core/backends/sims/microsoft/sparse-sim/SparseSimulator.h>
#include <stdexcept>
#include <map>
using namespace Microsoft::Quantum::SPARSESIMULATOR;
using Wave=std::map<std::string,std::complex<double>>;
void require(bool value,const char* why){if(!value)throw std::runtime_error(why);}
int main(){try{
  double maximum=0;size_t checked=0,queued=0;
  for(int repeat=0;repeat<2;++repeat)for(int mode=0;mode<6;++mode){
    SparseSimulator control(3),observed(3);
    for(int step=0;step<18;++step){
      auto gate=[&](SparseSimulator& s){int q=step%3;
        switch((step+mode)%9){
        case 0:s.H(q);break;case 1:s.X(q);break;
        case 2:s.R(Gates::Basis::PauliX,.37,q);break;
        case 3:s.R(Gates::Basis::PauliY,-.29,q);break;
        case 4:s.R(Gates::Basis::PauliZ,.41,q);break;
        case 5:s.MCX({static_cast<logical_qubit_id>((q+1)%3)},q);break;
        case 6:s.H(q);break;case 7:s.Z(q);break;case 8:s.Y(q);break;}};
      gate(control);gate(observed);
      auto a=observed.qb_stats();for(int i=0;i<100;++i)require(a==observed.qb_stats(),"observation_changed_queues");
      queued+=(a.operations+a.h+a.rx+a.ry)>0;
    }
    Wave a,b;
    // Both routes flush normally only when obtaining their final state.
    control.dump_all([&](const char* label,double r,double i){a[label]={r,i};return true;});
    observed.dump_all([&](const char* label,double r,double i){b[label]={r,i};return true;});
    require(a.size()==b.size(),"state_size_changed");double norm=0;
    for(auto [key,z]:a){require(b.count(key),"state_support_changed");maximum=std::max(maximum,std::abs(z-b.at(key)));norm+=std::norm(z);}
    require(std::abs(norm-1)<1e-10,"state_norm");require(maximum<1e-12,"state_changed");++checked;
  }
  require(queued>0,"no_pending_operations_exercised");
  std::cout<<"STATE_NEUTRALITY {\"cases\":"<<checked<<",\"queued_checkpoints\":"<<queued<<",\"max_complex_difference\":"<<maximum<<"}"<<std::endl;
  return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}}
