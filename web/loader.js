// PGMMV lazy resource loader + IDBFS cache.
// Manifest is loaded before main(); assets are fetched synchronously only when FS accesses them.
(function () {
  if (typeof window === 'undefined') return;

  var Q = new URLSearchParams(location.search);
  var base = new URL(Q.get('game') || 'game/', location.href).href.replace(/\/?$/, '/');
  var hooks = Module.pgmmv || (Module.pgmmv = {});
  var manifest = null;
  var available = new Map();
  var loading = new Set();
  var fs = null;
  var root = '/app/Resources';
  var idbfsMounted = false;
  var persistTimer = null;
  var persistBusy = false;
  var persistAgain = false;
  var loadedCount = 0;
  var loadedBytes = 0;
  var reportedMissing = new Set();

  function logError(message) {
    console.error('[PGMMV-LAZY] ' + message);
    if (hooks.onError) {
      try { hooks.onError('[PGMMV-LAZY] ' + message); } catch (_) {}
    }
  }

  // Keep a leading slash for absolute FS paths, but collapse dot segments.
  function normalize(path) {
    var raw = String(path).replace(/\\/g, '/');
    var absolute = raw.charAt(0) === '/';
    var parts = raw.split('/');
    var out = [];
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i];
      if (!p || p === '.') continue;
      if (p === '..') { if (out.length) out.pop(); }
      else out.push(p);
    }
    return (absolute ? '/' : '') + out.join('/');
  }

  function pathKeys(path) {
    var n = normalize(path).replace(/^\/+/, '');
    var candidates = [n];
    try { candidates.push(n.normalize('NFC'), n.normalize('NFD')); } catch (_) {}
    var keys = new Set();
    for (var i = 0; i < candidates.length; i++) {
      var c = candidates[i];
      var lower = c.toLowerCase();
      keys.add(lower);
      if (lower.indexOf('data/') === 0) keys.add(lower.slice(5));
      var idx = lower.lastIndexOf('/data/');
      if (idx >= 0) keys.add(lower.slice(idx + 6));
    }
    return Array.from(keys);
  }

  // Synchronous XHR cannot set responseType='arraybuffer' on the main thread.
  // x-user-defined maps each response byte to a character whose low byte is original.
  function xhrSync(url, binary) {
    var x = new XMLHttpRequest();
    x.open('GET', url, false);
    if (x.overrideMimeType) {
      x.overrideMimeType(binary ? 'text/plain; charset=x-user-defined' : 'text/plain; charset=utf-8');
    }
    try { x.send(null); }
    catch (e) { throw new Error('XHR failed: ' + url + ' :: ' + String(e)); }
    if (x.status < 200 || x.status >= 300) {
      throw new Error('HTTP ' + x.status + ' ' + url);
    }
    if (!binary) return x.responseText;
    var txt = x.responseText || '';
    var out = new Uint8Array(txt.length);
    for (var i = 0; i < txt.length; i++) out[i] = txt.charCodeAt(i) & 255;
    return out;
  }

  function loadManifestAsync() {
    var url = base + 'manifest.json';

    return fetch(url, {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store'
    }).then(function (response) {
      return response.text().then(function (text) {
        if (!response.ok) {
          throw new Error('HTTP ' + response.status + ' ' + url +
            ' :: body=' + String(text || '').slice(0, 400));
        }
        return text;
      });
    }).then(function (text) {
      var m;
      try {
        m = JSON.parse(text);
      } catch (e) {
        throw new Error('manifest JSON parse failed: ' + url + ' :: ' + String(e));
      }

      if (!m || m.format !== 1 || !Array.isArray(m.files)) {
        throw new Error('unsupported or malformed manifest at ' + url);
      }

      root = normalize(Module.resourceRoot || m.root || '/app/Resources');
      if (!root || root.charAt(0) !== '/') root = '/' + root;

      manifest = {
        version: String(m.version || '0'),
        files: m.files,
        total: Number(m.total || 0)
      };

      for (var i = 0; i < m.files.length; i++) {
        var stored = normalize(m.files[i].p).replace(/^\/+/, '');
        if (!stored || stored.split('/').indexOf('..') >= 0) continue;

        var keys = pathKeys(stored);
        for (var j = 0; j < keys.length; j++) {
          available.set(keys[j], stored);
        }
      }

      console.log('[PGMMV-LAZY] manifest loaded asynchronously; files=' +
        manifest.files.length + '; root=' + root);

      return manifest;
    });
  }

  function ensureParents(path) {
    var parent = normalize(path).slice(0, normalize(path).lastIndexOf('/')) || '/';
    try { fs.mkdirTree(parent); } catch (_) {}
  }

  function schedulePersist() {
    if (!idbfsMounted || !fs || typeof fs.syncfs !== 'function') return;
    if (persistTimer !== null) clearTimeout(persistTimer);
    persistTimer = setTimeout(function () {
      persistTimer = null;
      if (persistBusy) { persistAgain = true; return; }
      persistBusy = true;
      fs.syncfs(false, function (err) {
        persistBusy = false;
        if (err) console.warn('[PGMMV-LAZY] IDBFS writeback failed:', err);
        if (persistAgain) { persistAgain = false; schedulePersist(); }
      });
    }, 700);
  }

  function removeStaleManifestFiles() {
    var marker = root + '/.pgmmv-manifest-version';
    var oldVersion = '';
    try {
      if (fs.analyzePath(marker).exists) oldVersion = String(fs.readFile(marker, { encoding: 'utf8' })).trim();
    } catch (_) {}
    if (oldVersion === manifest.version) return false;

    // Remove only paths listed in the current manifest; leave unrelated user files alone.
    for (var i = 0; i < manifest.files.length; i++) {
      var rel = normalize(manifest.files[i].p).replace(/^\/+/, '');
      if (!rel) continue;
      var target = root + '/' + rel;
      try {
        if (fs.analyzePath(target).exists) fs.unlink(target);
      } catch (_) {}
    }
    fs.writeFile(marker, manifest.version, { encoding: 'utf8' });
    return true;
  }

  function setupIdbfsThen(done) {
    fs = (typeof FS !== 'undefined') ? FS : Module.FS;
    if (!fs) throw new Error('Emscripten FS is unavailable in preRun');
    try { fs.mkdirTree(root); } catch (_) {}

    var idbfsType = (typeof IDBFS !== 'undefined') ? IDBFS : Module.IDBFS;
    if (!idbfsType || typeof idbfsType.mount !== 'function') {
      console.warn('[PGMMV-LAZY] IDBFS is not linked; using MEMFS for this session');
      done();
      return;
    }
    try {
      fs.mount(idbfsType, {}, root);
      idbfsMounted = true;
    } catch (e) {
      // Never block game startup solely because persistent storage cannot be mounted.
      console.warn('[PGMMV-LAZY] IDBFS mount failed; using current FS:', e);
      done();
      return;
    }

    if (typeof fs.syncfs !== 'function') {
      console.warn('[PGMMV-LAZY] FS.syncfs is unavailable; IDBFS cache cannot be hydrated');
      done();
      return;
    }
    fs.syncfs(true, function (err) {
      if (err) console.warn('[PGMMV-LAZY] IDBFS restore failed; continuing with empty/current cache:', err);
      try {
        var changed = removeStaleManifestFiles();
        if (!changed) { done(); return; }
        fs.syncfs(false, function (writeErr) {
          if (writeErr) console.warn('[PGMMV-LAZY] IDBFS version-marker writeback failed:', writeErr);
          done();
        });
      } catch (e) {
        console.warn('[PGMMV-LAZY] cache version check failed; continuing:', e);
        done();
      }
    });
  }


  // PGMMV_ASYNC_PRELOAD_MANIFEST_ASSETS_V1
  // Download manifest assets asynchronously before C++ starts.
  // This preserves synchronous FS.open() for native game code.
  function preloadManifestFilesAsync() {
    if (!manifest || !fs) {
      return Promise.reject(new Error('manifest or FS is unavailable'));
    }

    var files = manifest.files || [];
    var cursor = 0;
    var finished = 0;
    var downloaded = 0;
    var skipped = 0;
    var downloadedBytes = 0;
    var failure = null;
    var rootNorm = normalize(root).replace(/\/+$/, '');
    var concurrency = Math.min(2, files.length);

    console.log('[PGMMV-LAZY] preloading assets; files=' +
      files.length + '; total=' + manifest.total +
      '; concurrency=' + concurrency);

    function reportProgress() {
      finished++;
      if (finished % 10 === 0 || finished === files.length) {
        console.log('[PGMMV-LAZY] preload progress: ' +
          finished + '/' + files.length +
          '; downloaded=' + downloaded +
          '; cached=' + skipped +
          '; bytes=' + downloadedBytes);
      }
    }

    function loadOne(entry) {
      var rel = normalize(entry.p).replace(/^\/+/, '');

      if (!rel || rel.split('/').indexOf('..') >= 0) {
        skipped++;
        reportProgress();
        return Promise.resolve();
      }

      var target = rootNorm + '/' + rel;

      // Reuse files already hydrated from IDBFS.
      try {
        if (fs.analyzePath(target).exists) {
          skipped++;
          reportProgress();
          return Promise.resolve();
        }
      } catch (_) {}

      var url = base + rel.split('/').map(encodeURIComponent).join('/') +
        '?v=' + encodeURIComponent(manifest.version);

      return fetch(url, {
        method: 'GET',
        credentials: 'same-origin',
        cache: 'no-store'
      }).then(function (response) {
        if (!response.ok) {
          return response.text().then(function (body) {
            throw new Error('HTTP ' + response.status +
              ' :: ' + url +
              ' :: body=' + String(body || '').slice(0, 300));
          });
        }
        return response.arrayBuffer();
      }).then(function (buffer) {
        var bytes = new Uint8Array(buffer);

        if (entry.s !== undefined &&
            bytes.length !== Number(entry.s)) {
          throw new Error('size mismatch: ' + rel +
            '; received=' + bytes.length +
            '; expected=' + entry.s);
        }

        ensureParents(target);
        fs.writeFile(target, bytes);

        downloaded++;
        downloadedBytes += bytes.length;
        reportProgress();
      }).catch(function (e) {
        throw new Error('asset preload failed: ' + rel +
          ' :: ' + String(e && e.stack || e));
      });
    }

    function worker() {
      function next() {
        if (failure) return Promise.resolve();

        var index = cursor++;
        if (index >= files.length) return Promise.resolve();

        return loadOne(files[index]).then(next).catch(function (e) {
          if (!failure) failure = e;
        });
      }

      return next();
    }

    var workers = [];
    for (var w = 0; w < concurrency; w++) {
      workers.push(worker());
    }

    return Promise.all(workers).then(function () {
      if (failure) throw failure;

      console.log('[PGMMV-LAZY] asset preload complete; downloaded=' +
        downloaded + '; cached=' + skipped +
        '; bytes=' + downloadedBytes);

      // Persist the completed preload to IDBFS.
      // A writeback failure must not prevent this session from starting.
      if (!idbfsMounted || typeof fs.syncfs !== 'function') {
        return true;
      }

      return new Promise(function (resolve) {
        try {
          fs.syncfs(false, function (err) {
            if (err) {
              console.warn('[PGMMV-LAZY] asset cache writeback failed:', err);
            } else {
              console.log('[PGMMV-LAZY] asset cache writeback complete');
            }
            resolve(true);
          });
        } catch (e) {
          console.warn('[PGMMV-LAZY] asset cache writeback threw:', e);
          resolve(true);
        }
      });
    });
  }

  function loadOnDemand(path) {
    if (!manifest || typeof path !== 'string') return false;
    var requested = normalize(path);
    if (requested === '/dev' || requested.indexOf('/dev/') === 0 ||
        requested === '/tmp' || requested.indexOf('/tmp/') === 0 || requested === '/') return false;

    var rootNorm = normalize(root).replace(/\/+$/, '');
    var rel = requested;
    if (rel === rootNorm) return false;
    if (rel.indexOf(rootNorm + '/') === 0) rel = rel.slice(rootNorm.length + 1);
    else rel = rel.replace(/^\/+/, '');

    var keys = pathKeys(rel), matched = null;
    for (var i = 0; i < keys.length; i++) {
      if (available.has(keys[i])) { matched = available.get(keys[i]); break; }
    }
    if (!matched) {
      var low = rel.toLowerCase();
      if (low.indexOf('data/') >= 0 && !reportedMissing.has(low)) {
        reportedMissing.add(low);
        console.debug('[PGMMV-LAZY] path not in manifest:', requested);
      }
      return false;
    }

    var target = rootNorm + '/' + matched;
    // The wrapper is re-entered by FS.writeFile; avoid recursive fetch/write loops.
    if (loading.has(target)) return false;
    try { if (fs.analyzePath(target).exists) return true; } catch (_) {}

    loading.add(target);
    try {
      var url = base + matched.split('/').map(encodeURIComponent).join('/') +
        '?v=' + encodeURIComponent(manifest.version);
      var bytes = xhrSync(url, true);
      var rec = manifest.files.find(function (f) { return normalize(f.p).replace(/^\/+/, '') === matched; });
      if (rec && rec.s !== undefined && bytes.length !== Number(rec.s)) {
        throw new Error('size mismatch: path=' + matched + ' url=' + url +
          ' received=' + bytes.length + ' expected=' + rec.s +
          ' firstBytes=' + Array.from(bytes.slice(0, 16)).map(function (b) { return b.toString(16).padStart(2, '0'); }).join(' '));
      }
      ensureParents(target);
      fs.writeFile(target, bytes);
      loadedCount++;
      loadedBytes += bytes.length;
      if (hooks.onProgress) hooks.onProgress(loadedCount, manifest.files.length, loadedBytes, manifest.total);
      schedulePersist();
      return true;
    } finally {
      loading.delete(target);
    }
  }

  // PGMMV_LAZY_STAT_METADATA_V1
  // A manifest hit during stat/lstat means "exists"; do not download bytes until open().
  function manifestInfoForPath(path) {
    if (!manifest || typeof path !== 'string') return null;
    var requested = normalize(path);
    var rootNorm = normalize(root).replace(/\/+$/, '');
    if (requested === rootNorm) return null;
    var rel = requested;
    if (rel.indexOf(rootNorm + '/') === 0) rel = rel.slice(rootNorm.length + 1);
    else rel = rel.replace(/^\/+/, '');
    rel = normalize(rel).replace(/^\/+/, '');
    if (!rel) return null;

    var keys = pathKeys(rel), matched = null;
    for (var i = 0; i < keys.length; i++) {
      if (available.has(keys[i])) { matched = available.get(keys[i]); break; }
    }
    if (matched) {
      var entry = null;
      for (var j = 0; j < manifest.files.length; j++) {
        if (normalize(manifest.files[j].p).replace(/^\/+/, '') === matched) {
          entry = manifest.files[j]; break;
        }
      }
      return { path: matched, entry: entry, directory: false, target: rootNorm + '/' + matched };
    }

    // Synthesize directories implied by manifest entries so isFileExist/stat on a folder
    // doesn't trigger a download or incorrectly report ENOENT before its first file opens.
    var prefix = rel.toLowerCase().replace(/\/+$/, '') + '/';
    for (var k = 0; k < manifest.files.length; k++) {
      var candidate = normalize(manifest.files[k].p).replace(/^\/+/, '');
      if (candidate.toLowerCase().indexOf(prefix) === 0) {
        return { path: rel, entry: null, directory: true, target: rootNorm + '/' + rel };
      }
    }
    return null;
  }

  function virtualStat(info) {
    var now = new Date();
    var size = info.entry && info.entry.s !== undefined ? Math.max(0, Number(info.entry.s) || 0) : 0;
    return {
      dev: 1, ino: 0,
      mode: info.directory ? (0x4000 | 0o555) : (0x8000 | 0o444),
      nlink: info.directory ? 2 : 1,
      uid: 0, gid: 0, rdev: 0,
      size: size,
      atime: now, mtime: now, ctime: now,
      blksize: 4096, blocks: Math.ceil(size / 512)
    };
  }

  function manifestAwareStat(path, original, args) {
    var info = manifestInfoForPath(path);
    if (!info) return original.apply(fs, args);
    try {
      if (fs.analyzePath(info.target).exists) {
        // The caller may have supplied a relative path; stat the canonical cached path.
        return original.call(fs, info.target);
      }
    } catch (_) {}
    // Manifest metadata is enough to answer existence/size checks. Do not XHR here.
    return virtualStat(info);
  }

  function installHooks() {

    // [PGMMV-SAVE-IDBFS-V1]
    // PGMMV saves are under /app/Resources/save, inside the existing IDBFS mount.
    function __pgmmvIsSavePath(path) {
      if (typeof path !== "string") return false;
      var p = normalize(path).toLowerCase();
      return /(?:^|\/)save\/(?:play_[0-9]+\.json|config\.json)(?:\.(?:tmp|bak))?$/.test(p);
    }

    // Persist completed save-file writes (including config.json).
    var __pgmmvOriginalClose = fs.close;
    if (typeof __pgmmvOriginalClose === "function") {
      fs.close = function (stream) {
        var savePath = stream && stream.path;
        var flags = stream && stream.flags;
        var isWrite = typeof flags !== "number" || (flags & 3) !== 0;
        var isSaveWrite = isWrite && __pgmmvIsSavePath(savePath);

        var result = __pgmmvOriginalClose.apply(fs, arguments);

        if (isSaveWrite) {
          console.log("[PGMMV-SAVE-IDBFS] file closed:", savePath);
          schedulePersist();
        }
        return result;
      };
    }

    // Persist after PGMMV's .tmp -> final save rename has completed.
    var __pgmmvOriginalRename = fs.rename;
    if (typeof __pgmmvOriginalRename === "function") {
      fs.rename = function (oldPath, newPath) {
        var isSaveRename =
          __pgmmvIsSavePath(oldPath) || __pgmmvIsSavePath(newPath);

        var result = __pgmmvOriginalRename.apply(fs, arguments);

        if (isSaveRename) {
          console.log(
            "[PGMMV-SAVE-IDBFS] rename completed:",
            oldPath, "->", newPath
          );
          schedulePersist();
        }
        return result;
      };
    }

    console.log(
      "[PGMMV-SAVE-IDBFS] hooks installed; IDBFS root=" + root
    );
    // [PGMMV-SAVE-IDBFS-V1-END]

    var originalOpen = fs.open;
    var originalStat = fs.stat;
    var originalLstat = fs.lstat;

    fs.open = function (path, flags) {
      var readOnly = typeof flags === 'string' ? !/[wa+]/.test(flags) :
        (typeof flags === 'number' && (flags & 3) === 0);
      if (readOnly && typeof path === 'string') {
        try { loadOnDemand(path); }
        catch (e) {
          console.error('[PGMMV-LAZY] open fetch failed: ' + path, e);
          throw e;
        }
      }
      return originalOpen.apply(fs, arguments);
    };
    if (typeof originalStat === 'function') {
      fs.stat = function (path) {
        if (typeof path === 'string') return manifestAwareStat(path, originalStat, arguments);
        return originalStat.apply(fs, arguments);
      };
    }
    if (typeof originalLstat === 'function') {
      fs.lstat = function (path) {
        if (typeof path === 'string') return manifestAwareStat(path, originalLstat, arguments);
        return originalLstat.apply(fs, arguments);
      };
    }
  }

  if (typeof Module.preRun === 'function') Module.preRun = [Module.preRun];
  Module.preRun = Module.preRun || [];
  Module.preRun.push(function () {
    var addDep = Module['addRunDependency'];
    var delDep = Module['removeRunDependency'];
    addDep('pgmmv-manifest-and-idbfs');
    try {
      loadManifestAsync().then(function () {
        setupIdbfsThen(function () {
          preloadManifestFilesAsync().then(function () {
            try { installHooks(); }
            catch (e) {
              logError('failed to install lazy loader: ' + String(e && e.stack || e));
              return;
            }

            console.log('[PGMMV-LAZY] ready; all manifest assets available; IDBFS=' +
              idbfsMounted + '; manifest files=' + manifest.files.length +
              '; root=' + root);

            delDep('pgmmv-manifest-and-idbfs');
          }).catch(function (e) {
            logError('manifest asset preload failed: ' +
              String(e && e.stack || e));
            // Keep the run dependency on failure.
          });
        });
      }).catch(function (e) {
        logError('manifest/IDBFS setup failed: ' +
          String(e && e.stack || e));
        // Keep the run dependency on failure.
      });
    } catch (e) {
      logError(String(e && e.stack || e));
      // Keep dependency on fatal manifest/FS setup failure to prevent partially initialized game.
    }
  });
})();
