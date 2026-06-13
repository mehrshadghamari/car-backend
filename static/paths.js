/** Resolve staff nav links from /portal/{uuid1}/{uuid2}/… pages. */
(() => {
  const uuidRe =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const segments = window.location.pathname.split('/').filter(Boolean);
  let secretBase = '';
  if (
    segments[0] === 'portal' &&
    segments.length >= 3 &&
    uuidRe.test(segments[1]) &&
    uuidRe.test(segments[2])
  ) {
    secretBase = `/${segments.slice(0, 3).join('/')}`;
  }

  window.APP_PATHS = {
    portal: '/portal/',
    results: secretBase ? `${secretBase}/results` : '/portal/',
    admin: secretBase ? `${secretBase}/admin/` : '/portal/',
    docs: secretBase ? `${secretBase}/docs` : '/portal/',
    trimMapping: secretBase ? `${secretBase}/trim-mapping` : '/portal/',
  };

  document.querySelectorAll('[data-nav]').forEach((el) => {
    const key = el.getAttribute('data-nav');
    if (window.APP_PATHS[key]) {
      el.href = window.APP_PATHS[key];
    }
  });
})();
