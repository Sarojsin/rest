const tab = await tools.browser.tabs.open({ url: "http://192.168.1.5:5173/auth/invitations/x3Ub1j303tR0JczULbxceJX7dVBjuJ61IhZ1mG0HJ7M" });
await tools.browser.wait({ tabID: tab.id, condition: "load", timeoutMs: 20000 });
const snap = await tools.browser.snapshot({ tabID: tab.id });
const content = snap.content || "";
return { url: snap.tab?.url, title: snap.tab?.title, contentLength: content.length, contentStart: content.slice(0, 2000) };