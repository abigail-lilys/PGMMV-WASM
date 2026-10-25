/* Emscripten has no <sys/sysctl.h>. Chipmunk's cpHastySpace.c includes it unconditionally
   (non-Windows) but only calls sysctlbyname() under __APPLE__; elsewhere threads==0 means 1 thread. */
#ifndef PGMMV_SHIM_SYS_SYSCTL_H
#define PGMMV_SHIM_SYS_SYSCTL_H
#endif
