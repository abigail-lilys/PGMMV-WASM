/* [wasm-port] NSPR's ptsynch.o references SysV semaphores; Emscripten's musl has none.
   NSPR uses them only as a fallback synchronization primitive; fail cleanly with ENOSYS. */
#include <errno.h>
#include <stddef.h>
#include <sys/types.h>
struct sembuf;
int semget(key_t key, int nsems, int semflg) { (void)key; (void)nsems; (void)semflg; errno = ENOSYS; return -1; }
int semop(int semid, struct sembuf *sops, size_t nsops) { (void)semid; (void)sops; (void)nsops; errno = ENOSYS; return -1; }
int semctl(int semid, int semnum, int cmd, ...) { (void)semid; (void)semnum; (void)cmd; errno = ENOSYS; return -1; }
key_t ftok(const char *pathname, int proj_id) { (void)pathname; (void)proj_id; errno = ENOSYS; return (key_t)-1; }
