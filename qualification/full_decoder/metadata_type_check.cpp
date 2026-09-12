#include "AcceleratorBuffer.hpp"
#include <iostream>
#include <stdexcept>

// Header-only probe: the Linux XACC library cannot link into this macOS test.
// Any XACC error path must fail the check, never be silently ignored.
namespace xacc {
void emit_error(const std::string&& message) { throw std::runtime_error(message); }
}

int main() {
  // Exercise the actual installed ExtraInfo variant without simulator services.
  for (bool found : {false, true}) {
    xacc::ExtraInfo metadata = found;
    if (metadata.as<int>() != (found ? 1 : 0))
      throw std::runtime_error("Unexpected XACC bool-to-int metadata representation");
  }
  std::cout << "PASS: both candidate flags use the integer ExtraInfo variant\n";
}
