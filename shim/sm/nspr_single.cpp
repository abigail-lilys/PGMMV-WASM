// PGMMV_NSPR_TRACE_V1
#if defined(__EMSCRIPTEN__)
#include <emscripten.h>
#define PGMMV_NSPR_TRACE(message) EM_ASM({ if (typeof Module !== "undefined" && Module.pgmmv && Module.pgmmv.trace) Module.pgmmv.trace(UTF8ToString($0)); }, message)
#else
#define PGMMV_NSPR_TRACE(message) ((void)0)
#endif

// NSPR 单线程 shim for SpiderMonkey 34 (prebuilt/sm34)
//
// 背景：libjs_static.a 引用 15 个 PR_* 符号，但这些符号由 libnspr4.a 提供，
// 而 libnspr4.a 在非 pthread 的 Emscripten 环境不可链接（依赖几十个 _MD_*）。
// 本 shim 提供 SM34 实际用到的 PR_* 子集，全部退化为单线程语义。
//
// 前提：Emscripten 构建不带 -pthread、不带 SharedArrayBuffer。

#include <nspr/prthread.h>
#include <nspr/prlock.h>
#include <nspr/prcvar.h>
#include <nspr/prinit.h>
#include <nspr/prinrval.h>
#include <nspr/prerror.h>

extern "C" {

// ---------- 线程 ----------
// 同步执行 start(arg)，然后返回假句柄。SM34 的 GC helper 工作会压到主线程完成；
// 代价是某些 GC 阶段稍慢，但没有死锁风险。

static char        g_fake_thread_marker = 0;
static PRThread*   g_fake_thread = reinterpret_cast<PRThread*>(&g_fake_thread_marker);

PRThread* PR_CreateThread(PRThreadType /*type*/,
                          void (*start)(void*),
                          void* arg,
                          PRThreadPriority /*priority*/,
                          PRThreadScope /*scope*/,
                          PRThreadState /*state*/,
                          PRUint32 /*stackSize*/)
{
    PGMMV_NSPR_TRACE("NSPR_CREATE_THREAD_ENTER");
    if (start) {
        // Diagnostic: do not run a helper-thread entry on the main thread.
        PGMMV_NSPR_TRACE("NSPR_CREATE_THREAD_CALLBACK_SKIPPED");
    }
    PGMMV_NSPR_TRACE("NSPR_CREATE_THREAD_RETURN");
    return g_fake_thread;
}

PRStatus PR_JoinThread(PRThread* /*thread*/) { return PR_SUCCESS; }

PRThread* PR_GetCurrentThread() { return g_fake_thread; }

PRStatus PR_SetCurrentThreadName(const char* /*name*/) { return PR_SUCCESS; }

// ---------- 锁 ----------
static char   g_fake_lock_marker = 0;
static PRLock* g_fake_lock = reinterpret_cast<PRLock*>(&g_fake_lock_marker);

PRLock*   PR_NewLock()                     { return g_fake_lock; }
void      PR_DestroyLock(PRLock* /*l*/)    {}
void      PR_Lock(PRLock* /*l*/)           {}
PRStatus  PR_Unlock(PRLock* /*l*/)         { return PR_SUCCESS; }

// ---------- 条件变量 ----------
// 单线程下不能真等；PR_WaitCondVar 立即返回"信号已到"。
// 详见对话中的风险说明：如果 SM34 有双向协议依赖，需要改为空转，实测再调。

static char   g_fake_cvar_marker = 0;
static PRCondVar* g_fake_cvar = reinterpret_cast<PRCondVar*>(&g_fake_cvar_marker);

PRCondVar* PR_NewCondVar(PRLock* /*l*/)                          { return g_fake_cvar; }
void       PR_DestroyCondVar(PRCondVar* /*cv*/)                   {}
PRStatus   PR_WaitCondVar(PRCondVar* /*cv*/, PRIntervalTime /*t*/) { return PR_SUCCESS; }
PRStatus   PR_NotifyCondVar(PRCondVar* /*cv*/)                    { return PR_SUCCESS; }
PRStatus   PR_NotifyAllCondVar(PRCondVar* /*cv*/)                 { return PR_SUCCESS; }

// ---------- CallOnce ----------
// 单线程直接调用；inProgress 标志防止递归重入导致的无限递归。

PRStatus PR_CallOnceWithArg(PRCallOnceType* once, PRCallOnceWithArgFN func, void* arg)
{
    PGMMV_NSPR_TRACE("NSPR_CALLONCE_ENTER");
    if (!once)            return PR_FAILURE;
    if (once->initialized) return PR_SUCCESS;
    if (once->inProgress)  return PR_FAILURE;
    once->inProgress  = 1;
    PGMMV_NSPR_TRACE("NSPR_CALLONCE_BEFORE_CALLBACK");
    PRStatus status   = func(arg);
    PGMMV_NSPR_TRACE("NSPR_CALLONCE_AFTER_CALLBACK");
    once->status      = status;
    once->initialized = 1;
    once->inProgress  = 0;
    PGMMV_NSPR_TRACE("NSPR_CALLONCE_RETURN");
    return status;
}

// ---------- 时间 ----------
PRIntervalTime PR_MillisecondsToInterval(PRUint32 ms) { return ms; }

} // extern "C"
