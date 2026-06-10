// PufferLib 4.0 binding notes for critical_ranger_ffm.
//
// The train smoke for Issue #16 is a build/buffer/wiring proof around the real
// FFM environment seam. Real raylib rendering is deferred to Issue #20.
// A missing/no-op c_render is not visual eval proof.
//
// This placeholder keeps the expected Ocean file layout explicit in-repo while
// the CPU-safe binding contract is tested through ffm_c1_ocean_binding.c. The
// local PufferLib checkout owns the generated/native Python extension glue.

#include "ffm_c1_ocean_binding.h"

void c_render(void *env) {
    (void)env;
}
