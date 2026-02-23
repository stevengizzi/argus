/**
 * ARGUS Command Center Service Worker
 *
 * Caching strategy:
 * - App shell (HTML, CSS, JS): Cache-first for offline capability
 * - API calls (/api/, /ws/): Network-only, NEVER cached (trading data must be live)
 *
 * Version-keyed cache ensures clean updates when the app changes.
 */

const CACHE_VERSION = 'v3';
const CACHE_NAME = `argus-shell-${CACHE_VERSION}`;

// Files to precache for offline shell
const SHELL_ASSETS = [
  '/',
  '/index.html',
];

// Install: Precache shell assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(SHELL_ASSETS);
    })
  );
  // Activate immediately without waiting for other tabs to close
  self.skipWaiting();
});

// Activate: Clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key.startsWith('argus-') && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      );
    })
  );
  // Take control of all clients immediately
  self.clients.claim();
});

// Fetch: Route requests appropriately
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // CRITICAL: Never cache API or WebSocket requests
  // Trading data must always be live
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) {
    // Let the browser handle these normally (network-only)
    return;
  }

  // For navigation requests (HTML pages), try network first, fall back to cache
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache the latest HTML for offline use
          if (response.ok) {
            const clonedResponse = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, clonedResponse);
            });
          }
          return response;
        })
        .catch(() => {
          // Offline: serve from cache
          return caches.match(event.request).then((cached) => {
            return cached || caches.match('/index.html');
          });
        })
    );
    return;
  }

  // For static assets (JS, CSS, images), cache-first strategy
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        // Return cached version and update cache in background
        fetch(event.request)
          .then((response) => {
            if (response.ok) {
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(event.request, response);
              });
            }
          })
          .catch(() => {
            // Network failed, cached version already returned
          });
        return cached;
      }

      // Not in cache, fetch from network
      return fetch(event.request).then((response) => {
        // Cache successful responses for next time
        if (response.ok) {
          const clonedResponse = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, clonedResponse);
          });
        }
        return response;
      });
    })
  );
});
