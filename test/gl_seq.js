// Debug aid: log the sequence of GL state calls of ONE frame (the 3rd after the first draw), with the enabled
// vertex-attribute mask before every draw. Enabled by adding ?seq to the page address.
(function () {
  if (typeof WebGLRenderingContext === 'undefined' || typeof location === 'undefined') return;
  if (location.search.indexOf('seq') < 0) return;
  var pr = function (s) {
    if (typeof Module !== 'undefined' && Module['print']) Module['print'](s); else console.log(s);
  };
  var proto = WebGLRenderingContext.prototype;
  var draws = 0, armed = false, logging = false, lines = 0, LIMIT = 80;
  var names = { useProgram: 1, bindVertexArrayOES: 1, bindBuffer: 1, enableVertexAttribArray: 1,
                disableVertexAttribArray: 1, vertexAttribPointer: 1, drawArrays: 1, drawElements: 1, bindFramebuffer: 1 };
  var mask = function (gl) {
    var m = '', n = gl.getParameter(gl.MAX_VERTEX_ATTRIBS);
    for (var i = 0; i < Math.min(n, 8); i++) m += gl.getVertexAttrib(i, gl.VERTEX_ATTRIB_ARRAY_ENABLED) ? '1' : '0';
    return m;
  };
  var arg = function (x) {
    if (x === null) return 'null';
    if (x === undefined) return 'undef';
    if (typeof x === 'object') return x.constructor && x.constructor.name ? x.constructor.name : 'obj';
    return String(x);
  };
  Object.getOwnPropertyNames(proto).forEach(function (k) {
    var d = Object.getOwnPropertyDescriptor(proto, k);
    if (!d || typeof d.value !== 'function' || !names[k]) return;
    var f = d.value;
    proto[k] = function () {
      if (logging && lines < LIMIT) {
        lines++;
        var isDraw = (k === 'drawArrays' || k === 'drawElements');
        var vao = '';
        try { vao = this.getParameter(0x85B5) ? ' vao=set' : ' vao=none'; } catch (e) {}
        pr('[seq] ' + k + '(' + Array.prototype.slice.call(arguments).map(arg).join(',') + ')' +
           (isDraw ? '  enabledAttribs=' + mask(this) + vao : ''));
        if (lines === LIMIT) pr('[seq] (limit reached)');
      }
      var r = f.apply(this, arguments);
      if (k === 'drawArrays' || k === 'drawElements') draws++;
      return r;
    };
  });
  // frame boundary: requestAnimationFrame callbacks; log exactly one frame, the 4th one
  var raf = window.requestAnimationFrame.bind(window), frame = 0;
  window.requestAnimationFrame = function (cb) {
    return raf(function (t) {
      frame++;
      logging = (frame === 4) && !armed;
      if (logging) { armed = true; pr('[seq] ---- frame 4 begins ----'); }
      var r = cb(t);
      if (logging) { pr('[seq] ---- frame 4 ends (draw calls so far: ' + draws + ') ----'); logging = false; }
      return r;
    });
  };
  pr('[seq] installed');
})();
