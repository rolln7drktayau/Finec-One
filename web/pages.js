const root = document.getElementById('app');
root.innerHTML = `<div class="loading"><div><h1>FINEC ONE</h1><p>Préparation de votre espace de démonstration…</p><p>Le premier chargement peut prendre une minute.</p><p>Données fictives • Aucune installation requise</p></div></div>`;
const worker = new Worker(new URL('./pages-worker.js', import.meta.url));
const pending = new Map();
let sequence = 0;
const ready = new Promise((resolve, reject) => {
  worker.onerror = () => reject(new Error('Le moteur de démonstration ne peut pas démarrer.'));
  worker.onmessage = ({data}) => {
    if (data.ready) return resolve();
    if (data.fatal) return reject(new Error(data.fatal));
    const task = pending.get(data.id);
    if (!task) return;
    pending.delete(data.id);
    if (data.error) task.reject(new Error(data.error));
    else task.resolve(new Response(data.result.body, {status: data.result.status, headers: data.result.headers}));
  };
});
try {
  await ready;
  const nativeFetch = window.fetch.bind(window);
  window.fetch = (input, options = {}) => {
    if (typeof input !== 'string' || !input.startsWith('/api/')) return nativeFetch(input, options);
    return new Promise((resolve, reject) => {
      const id = ++sequence;
      pending.set(id, {resolve, reject});
      worker.postMessage({id, request: {path: input, method: options.method || 'GET', headers: options.headers || {}, body: options.body}});
    });
  };
  // Each tab starts a new synthetic database, so old login tokens cannot apply.
  sessionStorage.removeItem('finec_token');
  const notice = document.createElement('div');
  notice.className = 'browser-demo-notice';
  notice.textContent = 'Démo indépendante · Données fictives dans cet onglet uniquement · Recharger remet la démo à zéro. / Reload to reset.';
  document.body.prepend(notice);
  await import('./app.js');
} catch (error) {
  root.innerHTML = `<div class="loading"><div><h1>Chargement interrompu</h1><p>Vérifiez votre connexion Internet puis réessayez.</p><button class="btn primary" id="retry">Réessayer</button><details><summary>Détails</summary><pre></pre></details></div></div>`;
  root.querySelector('pre').textContent = error.message;
  document.getElementById('retry').onclick = () => location.reload();
}
