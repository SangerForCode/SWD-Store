"use strict";

// Cache name - change the version when you update your assets
const CACHE_NAME = 'pwa-cache-v14';

// List of assets to cache during installation
const urlsToCache = [
    '/',
    '/offline/',
    // Local CSS
    // External resources
    'https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&display=swap',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    // Cache icon files and manifest
    // '/static/images/icons/icon-72x72.png',
    // '/static/images/icons/icon-96x96.png',
    // '/static/images/icons/icon-128x128.png',
    // '/static/images/icons/icon-144x144.png',
    // '/static/images/icons/icon-152x152.png',
    // '/static/images/icons/icon-192x192.png',
    // '/static/images/icons/icon-384x384.png',
    // '/static/images/icons/icon-512x512.png',
    '/manifest.json'
];

// Install event handler - caches assets
self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache:', CACHE_NAME);
                // Use a more robust caching approach that doesn't fail completely
                // if one resource fails
                return Promise.allSettled(
                    urlsToCache.map(url => {
                        return cache.add(url)
                            .catch(error => {
                                console.error(`Failed to cache ${url}:`, error);
                            });
                    })
                );
            })
    );
});

// Activate event handler - clean old caches and claim clients
self.addEventListener('activate', event => {
    event.waitUntil(
        Promise.all([
            // Clean up old cache versions
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames
                        .filter(cacheName => cacheName.startsWith('pwa-cache-'))
                        .filter(cacheName => cacheName !== CACHE_NAME)
                        .map(cacheName => {
                            console.log('Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            }),
            // Claim all clients so the service worker is in control immediately
            self.clients.claim()
        ])
    );
});

// Fetch event handler - serve cached content when possible
self.addEventListener('fetch', event => {
    // Skip cross-origin requests like Google Analytics
    if (!event.request.url.startsWith(self.location.origin) && 
        !event.request.url.includes('googleapis.com') && 
        !event.request.url.includes('cdnjs.cloudflare.com')) {
        return;
    }

    // For HTML page navigation
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    // When network is unavailable for navigation, serve offline page
                    return caches.match('/offline/');
                })
        );
        return;
    }

    // For other requests like images, scripts, styles
    event.respondWith(
        caches.match(event.request)
            .then(cachedResponse => {
                // Return cached response if available
                if (cachedResponse) {
                    return cachedResponse;
                }

                // Otherwise try to fetch from network
                return fetch(event.request)
                    .then(response => {
                        // Don't cache non-successful responses
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }

                        // Cache the fetched response for future use
                        // We need to clone the response since it's a stream and can only be consumed once
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });

                        return response;
                    })
                    .catch(error => {
                        console.error('Fetch failed:', error);
                        
                        // For image requests that fail, we could return a default image
                        if (event.request.url.match(/\.(jpg|jpeg|png|gif|svg)$/)) {
                            return caches.match('/static/images/placeholder.png');
                        }
                        
                        // Return undefined for other resources which will result in a network error
                        // This is preferable to returning a corrupted response
                    });
            })
    );
});
