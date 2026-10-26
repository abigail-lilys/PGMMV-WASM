/* [wasm-port] Emscripten's musl has no reentrant protoent lookups; NSPR's prnetdb.o references them.
   Browsers never need protocol-by-name/number lookups, so return "not found". */
#include <stddef.h>
struct protoent;
int getprotobyname_r(const char *name, struct protoent *result, char *buf, size_t buflen, struct protoent **resultp) {
    (void)name; (void)result; (void)buf; (void)buflen;
    if (resultp) *resultp = 0;
    return -1;
}
int getprotobynumber_r(int number, struct protoent *result, char *buf, size_t buflen, struct protoent **resultp) {
    (void)number; (void)result; (void)buf; (void)buflen;
    if (resultp) *resultp = 0;
    return -1;
}
