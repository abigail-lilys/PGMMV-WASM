#include <sys/resource.h>
#include <string.h>

int getrusage(int who, struct rusage *usage) {
    (void)who;
    if (usage) {
        memset(usage, 0, sizeof(struct rusage));
    }
    return 0;
}
