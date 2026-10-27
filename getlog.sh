OUT=${1:-$HOME/pgmmv-wasm/page_log_latest.txt}
grep -a -o 'log?m=[^& ]*' $HOME/pgmmv-wasm/serve.log | sed 's/^log?m=//' | python3 -c "import sys,urllib.parse as u; L=[u.unquote(l.strip()) for l in sys.stdin]; i=max([k for k,x in enumerate(L) if x.endswith('page-start')]+[0]); print('\n'.join(L[i:]))" > "$OUT"
wc -l "$OUT"
