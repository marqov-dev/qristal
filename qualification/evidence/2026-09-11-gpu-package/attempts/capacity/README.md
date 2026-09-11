# Capacity rejection

After the permission fix, AWS rejected a g5.xlarge launch in us-east-1b with `InsufficientInstanceCapacity`. No instance was returned. The temporary security group was deleted and verified; `instance_terminated: false` means no instance was launched, not an uncleared live host. The next attempt selected a default subnet in us-east-1c with the same AMI, instance class, script and limits. No automatic larger-instance fallback was used.
