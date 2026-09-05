function initMetaPixel() {
  !function(f,b,e,v,n,t,s)
  {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)};
  if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version="2.0";
  n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];
  s.parentNode.insertBefore(t,s)}(window, document,"script",
  "https://connect.facebook.net/en_US/fbevents.js");
  fbq("init", "2083020305980459");
  fbq("track", "PageView");
}
// Prerendered pages must not fire analytics until they are actually shown.
// Loading is deferred to idle time after window load so the pixel never
// competes with rendering the page (LCP/TBT).
var metaPixelStarted = false;
function startMetaPixel() {
  if (metaPixelStarted || document.prerendering) return;
  metaPixelStarted = true;
  initMetaPixel();
}
function scheduleMetaPixel() {
  if ("requestIdleCallback" in window) {
    requestIdleCallback(startMetaPixel, { timeout: 3000 });
  } else {
    setTimeout(startMetaPixel, 1500);
  }
}
if (document.prerendering) {
  document.addEventListener("prerenderingchange", scheduleMetaPixel, { once: true });
} else if (document.readyState === "complete") {
  scheduleMetaPixel();
} else {
  window.addEventListener("load", scheduleMetaPixel, { once: true });
}
document.addEventListener("click", function(event) {
  var ticketLink = event.target.closest("a[href*=\"lasalsadelbaile.com/MSC2026\"]");
  if (ticketLink) {
    startMetaPixel();
    if (window.fbq) fbq("track", "InitiateCheckout");
  }
});
