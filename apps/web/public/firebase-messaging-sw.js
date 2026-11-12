/**
 * Firebase Cloud Messaging service worker (web).
 *
 * Handles background push messages when the site tab is closed or not
 * focused. The foreground handler lives in src/lib/fcm.ts.
 *
 * Why the compat CDN build: a plain (non-module) service worker cannot resolve
 * bare npm specifiers such as "firebase/app". importScripts with the official
 * compat bundle is the supported way to run FCM in a classic service worker.
 */

/* global firebase, importScripts, self, clients */

importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js");

const firebaseConfig = {
  apiKey: "AIzaSyB9C3JpTrdpzSBuVSX56yhY4FeP4F3scCw",
  authDomain: "restaurant-94f9b.firebaseapp.com",
  projectId: "restaurant-94f9b",
  storageBucket: "restaurant-94f9b.firebasestorage.app",
  messagingSenderId: "987351547926",
  appId: "1:987351547926:web:0bd64696d752ac2508b537",
};

firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const notification = payload.notification || {};
  const data = payload.data || {};
  const title = notification.title || data.title || "New notification";
  const body = notification.body || data.body || "";

  self.registration.showNotification(title, {
    body,
    icon: notification.icon || "/favicon.ico",
    badge: "/favicon.ico",
    tag: data.tag || "restaurant-push",
    renotify: true,
    requireInteraction: false,
    data: { ...data, url: data.route || data.url || "/staff" },
  });
});

// Focus an existing tab (or open one) when the user taps the notification.
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/staff";

  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((windowClients) => {
        for (const client of windowClients) {
          if (client.url.includes(self.location.origin) && "focus" in client) {
            client.navigate(target);
            return client.focus();
          }
        }
        return clients.openWindow(target);
      })
  );
});
