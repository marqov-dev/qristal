# First MCZ prototype attempt: enabled-state failure

Native source af426fd. The consumer compiled but the negative gate failed with
clone_lost_disabled before QPP or sparse-sim cases ran. The source of this problem
is our prototype's inheritance: Circuit::disable only visits children, and the
base Instruction::isEnabled returns true. Empty metadata blocks therefore need
an explicit enabled flag. This is not a demonstrated upstream simulator defect.

The failed report, console checksum and exact VM/disk/group/transfer cleanup are
retained. All resources cleaned automatically. No phase or sparse result is
claimed for this attempt. A separate source revision adds explicit isEnabled,
enable and disable overrides, then reruns the original fixtures with the same
bounds on a new, independently identified VM. No original deadline was extended.
