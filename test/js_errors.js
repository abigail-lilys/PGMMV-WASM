// Debug aid: show uncaught JS errors / console.error inside the page's output box (no devtools on the phone).
(function () {
  if (typeof window === 'undefined') return;       // pthread workers have no window
  var pr = function (s) {
    if (typeof Module !== 'undefined' && Module['print']) Module['print'](s); else console.log(s);
  };
  window.addEventListener('error', function (e) {
    pr('[jserr] ' + e.message + ' @' + String(e.filename).split('/').pop() + ':' + e.lineno + ':' + e.colno +
       (e.error && e.error.stack ? ' | ' + String(e.error.stack).replace(/\s+/g, ' ').slice(0, 500) : ''));
  });
  window.addEventListener('unhandledrejection', function (e) {
    pr('[jserr] unhandledrejection: ' + String(e.reason && (e.reason.stack || e.reason)).replace(/\s+/g, ' ').slice(0, 500));
  });
  var oe = console.error;
  var depth = 0;
  console.error = function () {
    if (!depth) {
      depth++;
      try { pr('[console.error] ' + Array.prototype.slice.call(arguments).join(' ').replace(/\s+/g, ' ').slice(0, 400)); } catch (x) {}
      depth--;
    }
    return oe.apply(console, arguments);
  };
  pr('[jserr] handlers installed');
})();
