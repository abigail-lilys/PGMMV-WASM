import re, shutil, sys, os
p = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/pgmmv-wasm/web/index.html')
s = open(p, encoding='utf-8').read()
if 'PGMMV_GROW_PROBE_V1' in s:
    print('already patched'); sys.exit(0)
js = r"""<script>
// PGMMV_GROW_PROBE_V1: log who grows / fails to grow the wasm heap
(function(){
  try {
    Error.stackTraceLimit = 60;
    var P = WebAssembly.Memory.prototype, og = P.grow, ok = 0, bad = 0;
    function mb(x){ return (x/1048576).toFixed(1) + 'MB'; }
    function env(){
      var m = performance.memory || {};
      return 'jsUsed=' + (m.usedJSHeapSize ? mb(m.usedJSHeapSize) : '?') +
             ' jsTotal=' + (m.totalJSHeapSize ? mb(m.totalJSHeapSize) : '?') +
             ' jsLimit=' + (m.jsHeapSizeLimit ? mb(m.jsHeapSizeLimit) : '?') +
             ' deviceMemory=' + (navigator.deviceMemory || '?') + 'GB';
    }
    function st(){ return String(new Error().stack).split('\n').slice(2, 28).join('\n'); }
    P.grow = function(d){
      var before = this.buffer.byteLength, r;
      try {
        r = og.call(this, d);
        if (++ok <= 40) console.warn('[GROWPROBE] ok #' + ok + ' ' + mb(before) + ' -> ' + mb(before + d*65536) + ' ' + env() + '\n' + st());
        return r;
      } catch (e) {
        bad++;
        if (bad <= 3 || bad % 30 === 0)
          console.error('[GROWPROBE] FAIL #' + bad + ' heap=' + before + ' (' + mb(before) + ') delta=' + (d*65536) + ' (' + mb(d*65536) + ') ' + env() + '\n' + st());
        throw e;
      }
    };
  } catch (e) { console.error('[GROWPROBE] install failed: ' + e); }
})();
</script>
"""
shutil.copy(p, p + '.bak_growprobe')
m = re.search(r'<head[^>]*>', s, re.I)
if m:
    s = s[:m.end()] + '\n' + js + s[m.end():]
else:
    i = s.lower().find('<script')
    s = (s[:i] + js + s[i:]) if i >= 0 else (js + s)
open(p, 'w', encoding='utf-8').write(s)
print('patched', p)
