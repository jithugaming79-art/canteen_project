const CACHE_NAME = 'campusbites-v4';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/manifest.json',
    '/offline/',
];

// Install service worker
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .catch(err => console.log('Cache failed:', err))
    );
    self.skipWaiting();
});

// Activate and clean old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.filter(name => name !== CACHE_NAME)
                    .map(name => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

// Fetch strategy: Network first, fallback to cache
self.addEventListener('fetch', event => {
    // Skip non-GET requests and external URLs
    if (event.request.method !== 'GET') return;
    if (!event.request.url.startsWith(self.location.origin)) return;

    // Skip dynamic pages - always use network, never cache
    if (event.request.url.includes('/chat/') ||
        event.request.url.includes('/place-order/') ||
        event.request.url.includes('/cart/') ||
        event.request.url.includes('/api/') ||
        event.request.url.includes('/menu/') && !event.request.url.includes('/static/')) {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then(response => {
                // Cache successful responses
                if (response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseClone);
                    });
                }
                return response;
            })
            .catch(() => {
                // Fallback to cache if offline
                return caches.match(event.request).then(response => {
                    // Return cached response if found, else offline page for navigations
                    return response || caches.match('/offline/');
                });
            })
    );
});
