// PufferLib 4.0 staged env source for critical_ranger_ffm.
// The real environment lives in ffm_unmanaged.c; the C1 Ocean seam lives in
// ffm_c1_ocean_binding.c. This aggregation unit keeps Puffer's build script
// pointed at the real binding, not the old provisional shim.

#include "ffm_unmanaged.c"
#include "ffm_c1_ocean_binding.c"
#include "critical_ranger_ffm.h"
