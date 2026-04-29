// JAMES PWA Service Worker — minimal offline shell caching
const CACHE_NAME = 'james-v1';
const SHELL_FILES = ['/', '/static/style.css', '/static/app.js'];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL_FILES))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (e) => {
    // network-first for API, cache-first for static assets
    if (e.request.url.includes('/api/') || e.request.url.includes('/ws')) {
        return; // let network handle API calls
    }
    e.respondWith(
        fetch(e.request).catch(() => caches.match(e.request))
    );
});
