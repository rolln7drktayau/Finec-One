/* Python and SQLite run in this visitor's worker, never on a public server. */
importScripts('https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.js');
let python;
async function initialize() {
  python = await loadPyodide({indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.29.3/full/'});
  await python.loadPackage(['fastapi', 'sqlite3', 'hashlib']);
  python.FS.mkdirTree('/finec/app');
  python.FS.mkdirTree('/finec/web');
  const base = new URL('../', self.location.href);
  const manifest = await fetch(new URL('python-files.json', base)).then(r => r.json());
  await Promise.all(manifest.map(async path => {
    const response = await fetch(new URL(path, base));
    if (!response.ok) throw new Error('Chargement impossible : ' + path);
    python.FS.writeFile('/finec/' + path, await response.text());
  }));
  await python.runPythonAsync("import sys, hashlib, importlib\nimportlib.reload(hashlib)\nsys.path.insert(0, '/finec')\nfrom app.browser import browser_request");
  self.postMessage({ready: true});
}
let queue = initialize().catch(error => { self.postMessage({fatal: String(error)}); throw error; });
self.onmessage = ({data}) => {
  queue = queue.then(async () => {
    try {
      python.globals.set('request_json', JSON.stringify(data.request));
      const result = await python.runPythonAsync('await browser_request(request_json)');
      self.postMessage({id: data.id, result: JSON.parse(result)});
    } catch (error) { self.postMessage({id: data.id, error: String(error)}); }
  });
};



