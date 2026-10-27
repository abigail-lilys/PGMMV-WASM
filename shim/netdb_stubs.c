/* [wasm-port] Emscripten's musl has no reentrant protoent lookups; NSPR's prnetdb.o references them.
   Browsers never need protocol-by-name/number lookups, so return "not found".
   Signature matches NSPR's 4-argument form (as reported by wasm-ld). */
#include <stddef.h>

struct protoent;

int getprotobyname_r(const char *name, struct protoent *result, char *buf, size_t buflen)
{
    (void)name; (void)result; (void)buf; (void)buflen;
    return -1;
}

int getprotobynumber_r(int number, struct protoent *result, char *buf, size_t buflen)
{
    (void)number; (void)result; (void)buf; (void)buflen;
    return -1;
}
