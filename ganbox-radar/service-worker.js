importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey:"AIzaSyAeS1SmwQL2QcHAAh5VEKFovZcQm-DwFiY",
  authDomain:"ganbox-radar.firebaseapp.com",
  projectId:"ganbox-radar",
  storageBucket:"ganbox-radar.firebasestorage.app",
  messagingSenderId:"376912482178",
  appId:"1:376912482178:web:a7ccab69524caa64cec99b"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage(payload => {
  const {title,body} = payload.notification || {};
  const data = payload.data || {};
  self.registration.showNotification(title || 'GAN BOX Radar', {
    body:    body || '새 신호 감지',
    icon:    '/icon-192.png',
    badge:   '/icon-192.png',
    tag:     data.ticker || 'ganbox',
    data,
    actions: [
      {action:'chart', title:'차트 열기'},
      {action:'dismiss', title:'닫기'}
    ],
    vibrate: [200,100,200],
    requireInteraction: ['S1','S3','TP_HIT','SL_HIT'].includes(data.type),
  });
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const data   = e.notification.data || {};
  const ticker = data.ticker || '';
  if (e.action==='chart' && ticker) {
    e.waitUntil(clients.openWindow(
      `https://www.tradingview.com/chart/?interval=D&symbol=${ticker}`
    ));
  } else {
    e.waitUntil(
      clients.matchAll({type:'window'}).then(list=>{
        if (list.length) { list[0].focus(); }
        else clients.openWindow('/');
      })
    );
  }
});

const CACHE = 'gbr-v2';
self.addEventListener('install',  e=>{ e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/','index.html','manifest.json']))); self.skipWaiting(); });
self.addEventListener('activate', e=>{ e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k))))); self.clients.claim(); });
self.addEventListener('fetch',    e=>{ if(e.request.method!=='GET')return; e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))); });
