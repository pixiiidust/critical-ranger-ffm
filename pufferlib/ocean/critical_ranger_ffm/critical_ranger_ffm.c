// PufferLib 4.0 staged env source for critical_ranger_ffm.
// This file is intentionally a thin local-build aggregation unit: the real
// environment lives in src/critical_ranger_ffm/ffm_unmanaged.c and the C1
// Ocean seam lives in src/critical_ranger_ffm/ocean/ffm_c1_ocean_binding.c.
// Copy/sync this directory into Jamie's PufferLib checkout before local WSL
// native-extension builds; do not run those builds on the VPS.

#include "../../../src/critical_ranger_ffm/ffm_unmanaged.c"
#include "../../../src/critical_ranger_ffm/ocean/ffm_c1_ocean_binding.c"
