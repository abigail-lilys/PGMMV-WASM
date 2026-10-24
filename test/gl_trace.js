// Debug aid: report GL calls that raise an error, shader compile/link failures, first useProgram calls.
(function () {
  if (typeof WebGLRenderingContext === 'undefined') return;     // worker threads: no GL
  if (typeof location === 'undefined' || location.search.indexOf('gltrace') < 0) return;   // opt-in via ?gltrace (getError after EVERY GL call is very slow)
  var pr = function (s) {
    if (typeof Module !== 'undefined' && Module['print']) Module['print'](s); else console.log(s);
  };
  var proto = WebGLRenderingContext.prototype;
  var reported = 0, LIMIT = 40, sh = 0, SHLIMIT = 12, up = 0, UPLIMIT = 12;
  var errName = function (e) {
    return e === 0x500 ? 'INVALID_ENUM' : e === 0x501 ? 'INVALID_VALUE' : e === 0x502 ? 'INVALID_OPERATION' :
           e === 0x505 ? 'OUT_OF_MEMORY' : e === 0x506 ? 'INVALID_FRAMEBUFFER_OPERATION' : e === 0x9242 ? 'CONTEXT_LOST_WEBGL' : '0x' + e.toString(16);
  };
  Object.getOwnPropertyNames(proto).forEach(function (k) {
    var d = Object.getOwnPropertyDescriptor(proto, k);
    if (!d || typeof d.value !== 'function' || k === 'constructor' || k === 'getError') return;
    var f = d.value;
    proto[k] = function () {
      var r = f.apply(this, arguments);
      if (k === 'compileShader' && sh < SHLIMIT) {
        var s = arguments[0];
        if (!this.getShaderParameter(s, this.COMPILE_STATUS)) {
          sh++;
          pr('[glwrap] COMPILE FAILED: ' + this.getShaderInfoLog(s));
          pr('[glwrap]   source: ' + String(this.getShaderSource(s)).replace(/\s+/g, ' ').slice(0, 500));
        }
      } else if (k === 'linkProgram' && sh < SHLIMIT) {
        var p0 = arguments[0];
        if (!this.getProgramParameter(p0, this.LINK_STATUS)) {
          sh++;
          pr('[glwrap] LINK FAILED: ' + this.getProgramInfoLog(p0));
        }
      } else if (k === 'useProgram' && up < UPLIMIT) {
        up++;
        pr('[glwrap] useProgram(' + (arguments[0] ? 'program' : 'null') + ')');
      }
      if (reported < LIMIT) {
        var e = this.getError();
        if (e) {
          reported++;
          var a = Array.prototype.slice.call(arguments).map(function (x) {
            return (x && x.constructor && x.constructor.name && typeof x === 'object') ? x.constructor.name : String(x);
          }).join(',');
          pr('[glwrap] ' + k + '(' + a.slice(0, 120) + ') -> ' + errName(e));
          if (k === 'drawElements' || k === 'drawArrays') {
            var p = this.getParameter(this.CURRENT_PROGRAM);
            pr('[glwrap]   program=' + (p ? 'set' : 'NONE') +
               (p ? ' link=' + this.getProgramParameter(p, this.LINK_STATUS) + ' log=' + this.getProgramInfoLog(p) : ''));
            pr('[glwrap]   ARRAY_BUFFER bound=' + !!this.getParameter(this.ARRAY_BUFFER_BINDING) +
               ' ELEMENT_ARRAY_BUFFER bound=' + !!this.getParameter(this.ELEMENT_ARRAY_BUFFER_BINDING));
          }
          if (reported === LIMIT) pr('[glwrap] (limit reached, further errors not reported)');
        }
      }
      return r;
    };
  });
  pr('[glwrap] installed v2');
})();
