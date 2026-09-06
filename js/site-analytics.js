(() => {
  'use strict';
  const measurementId = 'G-YR3PM2QG8J';
  const pixelId = '2083020305980459';
  const production = ['milanosensualcongress.com', 'www.milanosensualcongress.com'].includes(location.hostname);
  const debug = new URL(location.href).searchParams.get('analytics_debug') === '1';
  const localDebug = debug && ['localhost', '127.0.0.1'].includes(location.hostname);
  let googleStarted = false;
  let metaStarted = false;

  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { window.dataLayer.push(arguments); };

  function loadScript(src) {
    const script = document.createElement('script');
    script.async = true;
    script.src = src;
    script.referrerPolicy = 'strict-origin-when-cross-origin';
    document.head.appendChild(script);
  }

  // Preserve campaign attribution without forwarding form fields or arbitrary URL parameters.
  function reportingUrl(value, campaigns = false) {
    try {
      const url = new URL(value);
      if (!['https:', 'http:'].includes(url.protocol)) return '';
      const result = new URL(url.origin + url.pathname);
      if (campaigns) {
        for (const key of ['utm_source', 'utm_medium', 'utm_campaign', 'utm_id', 'utm_term', 'utm_content']) {
          const value = url.searchParams.get(key);
          if (value && !value.includes('@')) result.searchParams.set(key, value);
        }
      }
      return result.href;
    } catch (_) { return ''; }
  }

  function startGoogleAnalytics() {
    if (document.prerendering || (!production && !localDebug)) return false;
    if (!googleStarted) {
      googleStarted = true;
      window.gtag('js', new Date());
      window.gtag('config', measurementId, {
        page_location: reportingUrl(location.href, true),
        page_referrer: reportingUrl(document.referrer),
        content_group: document.documentElement.lang.startsWith('it') ? 'Italian' : 'English',
        allow_google_signals: false,
        allow_ad_personalization_signals: false,
        cookie_expires: 180 * 24 * 60 * 60,
        ...(debug ? { debug_mode: true } : {})
      });
      loadScript('https://www.googletagmanager.com/gtag/js?id=' + measurementId);
    }
    return true;
  }

  function startMetaPixel() {
    if (document.prerendering || !production) return false;
    if (!metaStarted) {
      metaStarted = true;
      if (!window.fbq) {
        const fbq = window.fbq = function () {
          if (fbq.callMethod) fbq.callMethod.apply(fbq, arguments);
          else fbq.queue.push(arguments);
        };
        window._fbq = fbq;
        fbq.push = fbq;
        fbq.loaded = true;
        fbq.version = '2.0';
        fbq.queue = [];
      }
      window.fbq('init', pixelId);
      window.fbq('track', 'PageView');
      loadScript('https://connect.facebook.net/en_US/fbevents.js');
    }
    return true;
  }

  function startAnalytics() {
    startGoogleAnalytics();
    startMetaPixel();
  }

  function scheduleAnalytics() {
    const idle = () => {
      if ('requestIdleCallback' in window) window.requestIdleCallback(startAnalytics, { timeout: 3000 });
      else window.setTimeout(startAnalytics, 1500);
    };
    if (document.readyState === 'complete') idle();
    else window.addEventListener('load', idle, { once: true });
  }

  function trackGoogleEvent(name, parameters) {
    if (startGoogleAnalytics()) window.gtag('event', name, parameters);
  }

  window.startMetaPixel = startMetaPixel;
  window.mscAnalytics = {
    // Called only after Apps Script has confirmed that the reminder was saved.
    trackReminder(source) {
      if (!['Home - EN', 'Home - IT', 'Tickets - EN', 'Tickets - IT'].includes(source)) return;
      trackGoogleEvent('generate_lead', { lead_type: 'price_reminder', form_id: 'reminder-form', source });
      if (startMetaPixel()) window.fbq('track', 'Lead', {
        content_name: 'Price increase reminder', content_category: 'Email reminder', source
      });
    }
  };

  document.addEventListener('click', event => {
    const link = event.target.closest && event.target.closest('a[href]');
    if (!link) return;
    let target;
    try { target = new URL(link.href); } catch (_) { return; }
    if (target.hostname !== 'lasalsadelbaile.com' || !/^\/MSC2026\/?$/.test(target.pathname)) return;
    // A ticket click is an outbound referral, not a confirmed purchase.
    trackGoogleEvent('ticket_click', { link_domain: target.hostname, link_url: target.origin + target.pathname });
    if (startMetaPixel()) window.fbq('track', 'InitiateCheckout');
  });

  // Automatically load analytics after rendering; prerenders must never count as visits.
  if (document.prerendering) document.addEventListener('prerenderingchange', scheduleAnalytics, { once: true });
  else scheduleAnalytics();
})();
