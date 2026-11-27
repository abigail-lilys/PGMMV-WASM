// pthread 单线程 shim for SpiderMonkey 34
//
// libjs_static.a 直接引用 8 个 pthread 符号：TLS 相关 4 个 + attr/stack 相关 4 个。
// 没有 pthread_create / pthread_join（线程创建走 PR_CreateThread）。
//
// 全部标 __attribute__((weak))：如果 Emscripten libc 的 pthread stub 已经提供，
// 用 libc 的；只有缺失时用这里（比如 pthread_getattr_np 是 glibc 扩展，
// Emscripten 不一定有）。

#include <pthread.h>
#include <cerrno>
#include <cstdint>
#include <cstring>

extern "C" {

// ---------- TLS ----------
static constexpr int PGMMV_TLS_MAX = 32;
static void* g_tls_values[PGMMV_TLS_MAX] = {0};

__attribute__((weak))
int pthread_key_create(pthread_key_t* key, void (*/*destructor*/)(void*)) {
    static uint32_t next = 1;
    if (!key)                return EINVAL;
    if (next >= PGMMV_TLS_MAX) return EAGAIN;
    *key = next++;
    return 0;
}

__attribute__((weak))
void* pthread_getspecific(pthread_key_t key) {
    if (key >= PGMMV_TLS_MAX) return nullptr;
    return g_tls_values[key];
}

__attribute__((weak))
int pthread_setspecific(pthread_key_t key, const void* value) {
    if (key >= PGMMV_TLS_MAX) return EINVAL;
    g_tls_values[key] = const_cast<void*>(value);
    return 0;
}

__attribute__((weak))
pthread_t pthread_self() { return (pthread_t)0x1; }

// ---------- attr / stack ----------
// SM34 通过 pthread_getattr_np + pthread_attr_getstack 获取当前线程的栈范围，
// 用于 JS 栈溢出检测。给一个保守的 8MB 假范围（与 SM 默认 stack quota 一致）。

__attribute__((weak))
int pthread_attr_init(pthread_attr_t* attr) {
    if (!attr) return EINVAL;
    std::memset(attr, 0, sizeof(*attr));
    return 0;
}

__attribute__((weak))
int pthread_attr_destroy(pthread_attr_t* /*attr*/) { return 0; }

struct PgmmvStackInfo { void* addr; size_t size; };

__attribute__((weak))
int pthread_getattr_np(pthread_t /*thread*/, pthread_attr_t* attr) {
    if (!attr) return EINVAL;
    void* sp = __builtin_frame_address(0);
    PgmmvStackInfo info;
    info.addr = (char*)sp - (8u * 1024u * 1024u);
    info.size = 8u * 1024u * 1024u;
    static_assert(sizeof(PgmmvStackInfo) <= sizeof(pthread_attr_t),
                  "pthread_attr_t too small for stack info");
    std::memcpy(attr, &info, sizeof(info));
    return 0;
}

__attribute__((weak))
int pthread_attr_getstack(const pthread_attr_t* attr, void** stackaddr, size_t* stacksize) {
    if (!attr) return EINVAL;
    PgmmvStackInfo info;
    std::memcpy(&info, attr, sizeof(info));
    if (stackaddr) *stackaddr = info.addr;
    if (stacksize) *stacksize = info.size;
    return 0;
}

} // extern "C"

// =========================================================
// 强制覆盖 libc 的 pthread_create，同步执行线程体
// 防止 libc++ 抛出 std::system_error: thread constructor failed
// =========================================================
extern "C" {
#undef pthread_create
struct PgmmvFakeThread { int dummy; };
static PgmmvFakeThread g_fake_thread = {0};

// 注意：因为这是个强符号，Emscripten 链接时会优先使用我们提供的实现
int pthread_create(pthread_t* thread, const pthread_attr_t* /*attr*/,
                   void* (*start_routine)(void*), void* arg) {
    if (start_routine) {
        start_routine(arg); // 强行在当前单线程内同步执行，不让它抛异常
    }
    if (thread) {
        *thread = (pthread_t)&g_fake_thread;
    }
    return 0; // 永远返回成功
}
} // extern "C"
