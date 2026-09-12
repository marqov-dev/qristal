// Qualification-only provider for unchanged public upstream XACC QFT sources.
// This is not a replacement for the full XACC generators distribution bundle.
#include "QFT.hpp"
#include "InverseQFT.hpp"
#include <cppmicroservices/BundleActivator.h>
#include <cppmicroservices/BundleContext.h>

class US_ABI_LOCAL QftQualificationActivator : public cppmicroservices::BundleActivator {
public:
  void Start(cppmicroservices::BundleContext context) override {
    context.RegisterService<xacc::Instruction>(std::make_shared<xacc::circuits::QFT>());
    context.RegisterService<xacc::Instruction>(std::make_shared<xacc::circuits::InverseQFT>());
  }
  void Stop(cppmicroservices::BundleContext) override {}
};
CPPMICROSERVICES_EXPORT_BUNDLE_ACTIVATOR(QftQualificationActivator)
