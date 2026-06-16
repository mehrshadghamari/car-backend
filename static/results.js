const API = '/api/v1';

function trimMappingHref() {
  return (window.APP_PATHS && window.APP_PATHS.trimMapping) || '/';
}

function escapeHtml(value) {
  if (value == null) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatApiError(data) {
  if (!data) return 'Request failed';
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((e) => e.msg || JSON.stringify(e)).join('; ');
  }
  return JSON.stringify(data);
}

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!res.ok) throw new Error(formatApiError(data));
  return data;
}

function fmtDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('en-GB', {
      dateStyle: 'short',
      timeStyle: 'short',
    });
  } catch {
    return iso;
  }
}

const DEAL_TAG_META = {
  best: { label: 'Best', className: 'tag-best' },
  good: { label: 'Good', className: 'tag-good' },
  normal: { label: 'Normal', className: 'tag-fair' },
  fair: { label: 'Fair', className: 'tag-fair' },
};

function dealTagBadge(tag) {
  const meta = DEAL_TAG_META[tag] || { label: tag || '—', className: 'tag-fair' };
  return `<span class="deal-tag ${meta.className}">${meta.label}</span>`;
}

function fmtNum(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString('en-US');
}

function statusBadge(monitoringStatus) {
  const map = {
    active: { label: 'active', className: 'badge-green' },
    pending: { label: 'pending', className: 'badge-gray' },
    queued: { label: 'queued', className: 'badge-yellow' },
    monitoring: { label: 'monitoring', className: 'badge-blue' },
    failed: { label: 'failed', className: 'badge-red' },
    inactive: { label: 'inactive', className: 'badge-gray' },
  };
  const meta = map[monitoringStatus] || map.queued;
  return `<span class="badge ${meta.className}">${meta.label}</span>`;
}

function renderTable(rows) {
  const tbody = document.getElementById('resultsBody');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="12" class="empty">No purchase requests yet</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>
        <div class="cell-main">${escapeHtml(r.user_phone || '—')}</div>
        <div class="cell-sub">${escapeHtml(r.user_name || '')}</div>
      </td>
      <td>
        <div class="cell-main">${escapeHtml(r.car_brand_name || '')} ${escapeHtml(r.car_model_name || '—')}</div>
        <div class="cell-sub">${escapeHtml([r.car_year_title, r.car_trim_name].filter(Boolean).join(' · ') || '')} · year ${escapeHtml(r.production_year_min || '—')} · max ${fmtNum(r.usage_max)} km</div>
      </td>
      <td>${escapeHtml(r.city)}</td>
      <td>${escapeHtml(r.pricing_platform || '—')}</td>
      <td>${statusBadge(r.monitoring_status)}${r.is_active ? '' : ' <span class="cell-sub">(cancelled)</span>'}</td>
      <td>${fmtDate(r.latest_crawl_at)}</td>
      <td>${r.latest_posts_found}</td>
      <td>${r.total_opportunities}</td>
      <td>${r.sms_sent_count}</td>
      <td>${fmtDate(r.created_at)}</td>
      <td>${fmtDate(r.expires_at)}</td>
      <td class="link-cell">
        <button class="link-btn" data-id="${r.purchase_request_id}">Detail</button>
        ${r.is_active ? `<button class="link-btn cancel-btn" data-id="${r.purchase_request_id}">Cancel</button>` : ''}
      </td>
    </tr>
  `).join('');

  tbody.querySelectorAll('.link-btn:not(.cancel-btn)').forEach(btn => {
    btn.addEventListener('click', () => openDetail(btn.dataset.id, { reset: true }));
  });
  tbody.querySelectorAll('.cancel-btn').forEach(btn => {
    btn.addEventListener('click', () => cancelPurchase(btn.dataset.id));
  });
}

async function cancelPurchase(purchaseId) {
  if (!confirm('Cancel this purchase request and stop crawling?')) return;
  try {
    await api(`/purchase-requests/${purchaseId}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: false }),
    });
    loadResults();
  } catch (e) {
    alert(e.message || 'Cancel failed');
  }
}

let detailState = { purchaseId: null, listingsPage: 1, crawlRunId: null };

function section(title, html) {
  return `<section class="detail-section"><h3>${title}</h3>${html}</section>`;
}

function diagLink(label, url) {
  if (!url) return '';
  return `<a class="diag-link" href="${escapeHtml(url)}" target="_blank" rel="noopener">${label}</a>`;
}

function diagItem(e) {
  const cls = `diag-${e.level === 'opportunity' ? 'opportunity' : (e.level || 'info')}`;
  const extra = [];
  if (e.title) extra.push(escapeHtml(e.title));
  if (e.year != null) extra.push(`year ${e.year}`);
  if (e.km != null) extra.push(`${fmtNum(e.km)} km`);
  if (e.listing_price != null) extra.push(`listing ${fmtNum(e.listing_price)}`);
  if (e.price_down != null) extra.push(`floor ${fmtNum(e.price_down)}`);
  if (e.price_mid != null) extra.push(`mid ${fmtNum(e.price_mid)}`);
  if (e.price_up != null) extra.push(`max ${fmtNum(e.price_up)}`);
  if (e.deal_tag) extra.push(e.deal_tag);
  if (e.discount_pct != null) extra.push(`${fmtNum(e.discount_pct)}% off`);

  const links = [];
  if (e.divar_url) links.push(diagLink('Divar', e.divar_url));
  if (e.reference_url) links.push(diagLink('Khodro45', e.reference_url));
  if (links.length) extra.push(links.join(' · '));

  const suffix = extra.length ? `<div class="diag-meta">${extra.join(' · ')}</div>` : '';
  return `<li class="${cls}"><div>${escapeHtml(e.message || '')}</div>${suffix}</li>`;
}

function renderDiagnostics(runs) {
  const events = runs.flatMap(r => (r.diagnostics || []).map(e => ({ ...e, run_status: r.status })));
  if (!events.length) {
    return '<p class="empty-inline">No diagnostics yet — click <strong>Run crawl now</strong> to start a tracked crawl</p>';
  }
  return `<ul class="diag-list">${events.slice(0, 120).map(diagItem).join('')}</ul>`;
}

function pricingLinkLabel(provider) {
  if (provider === 'khodro45') return 'Khodro45';
  if (provider === 'hamrah_mechanic') return 'Hamrah';
  return provider || 'Price';
}

function shouldShowListingsPagination(pagination, listings) {
  const perPage = (pagination && pagination.per_page) || 20;
  const page = (pagination && pagination.page) || 1;
  if (pagination && pagination.total != null) {
    const totalPages = pagination.total_pages != null
      ? pagination.total_pages
      : Math.max(1, Math.ceil(pagination.total / perPage));
    return pagination.total > perPage || totalPages > 1 || page > 1;
  }
  return listings.length >= perPage || page > 1;
}

function normalizeListingsPagination(pagination, listings, page) {
  const perPage = 20;
  if (pagination && pagination.total != null) {
    const totalPages = pagination.total_pages != null
      ? pagination.total_pages
      : Math.max(1, Math.ceil(pagination.total / (pagination.per_page || perPage)));
    return { ...pagination, per_page: pagination.per_page || perPage, total_pages: totalPages };
  }
  return {
    page: page || 1,
    per_page: perPage,
    total: listings.length,
    total_pages: 1,
    crawl_run_id: detailState.crawlRunId,
  };
}

function renderListingsPagination(purchaseId, pagination, listings) {
  const pag = normalizeListingsPagination(pagination, listings, detailState.listingsPage);
  if (!shouldShowListingsPagination(pag, listings)) return '';
  const page = pag.page;
  const totalPages = pag.total_pages;
  const perPage = pag.per_page;
  const total = pag.total;
  const from = total ? (page - 1) * perPage + 1 : 0;
  const to = Math.min(page * perPage, total);
  const runNote = pag.crawl_run_id ? ' · filtered by crawl run' : '';
  return `
    <div class="pagination-bar listings-pagination">
      <button type="button" class="btn-secondary" data-page-action="prev" ${page <= 1 ? 'disabled' : ''}>← Previous</button>
      <span class="pagination-meta">Showing ${fmtNum(from)}–${fmtNum(to)} of ${fmtNum(total)} · page ${page} / ${totalPages}${runNote}</span>
      <button type="button" class="btn-secondary" data-page-action="next" ${page >= totalPages ? 'disabled' : ''}>Next →</button>
      ${pag.crawl_run_id ? `<button type="button" class="btn-secondary" data-page-action="clear-run">All listings</button>` : ''}
    </div>
  `;
}

function renderListings(listings, pagination, purchaseId) {
  const paginationHtml = renderListingsPagination(purchaseId, pagination, listings);
  if (!listings.length) {
    const emptyMsg = pagination && pagination.crawl_run_id
      ? 'No listings recorded for this crawl run'
      : 'No listings crawled yet — run a crawl to fetch Divar posts and market prices';
    return `<p class="empty-inline">${emptyMsg}</p>${paginationHtml}`;
  }
  return `
    ${paginationHtml}
    <table class="inner-table listings-table">
      <thead>
        <tr>
          <th>Listing</th>
          <th>Year</th>
          <th>Km</th>
          <th>Divar price</th>
          <th>Floor</th>
          <th>Mid</th>
          <th>Max</th>
          <th>Priced at</th>
          <th>Opp</th>
          <th>Links</th>
        </tr>
      </thead>
      <tbody>
        ${listings.map((l) => {
          const mp = l.latest_market_price;
          const links = [];
          if (l.divar_url) links.push(`<a href="${escapeHtml(l.divar_url)}" target="_blank" rel="noopener">Divar</a>`);
          if (mp && mp.reference_url) {
            links.push(`<a href="${escapeHtml(mp.reference_url)}" target="_blank" rel="noopener">${escapeHtml(pricingLinkLabel(mp.pricing_provider))}</a>`);
          }
          return `
            <tr>
              <td>
                <div class="cell-main">${escapeHtml((l.title || '—').slice(0, 70))}</div>
                <div class="cell-sub">${escapeHtml(l.district || '')}${l.color ? ` · ${escapeHtml(l.color)}` : ''}</div>
              </td>
              <td>${l.production_year ?? '—'}</td>
              <td>${fmtNum(l.kilometer)}</td>
              <td>${fmtNum(l.price)}</td>
              <td>${mp ? fmtNum(mp.price_down) : '—'}</td>
              <td>${mp ? fmtNum(mp.price_mid) : '—'}</td>
              <td>${mp ? fmtNum(mp.price_up) : '—'}</td>
              <td>${mp ? fmtDate(mp.fetched_at) : '—'}</td>
              <td>${l.opportunity_still_valid && l.opportunity_deal_tag ? dealTagBadge(l.opportunity_deal_tag) : '—'}</td>
              <td class="link-cell">${links.length ? links.join(' · ') : '—'}</td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
    ${paginationHtml}
  `;
}

function renderDetail(d, purchaseId) {
  const pr = d.purchase_request;
  const user = d.user;
  const car = d.car_model;

  let html = `<div style="margin-bottom:1rem">
    <button class="btn-secondary" id="runCrawlBtn" data-id="${purchaseId}">Run crawl now</button>
    <span id="runCrawlMsg" class="cell-sub"></span>
  </div>`;

  html += section('User', `
    <dl class="detail-dl">
      <dt>Phone</dt><dd>${escapeHtml(user.phone || '—')}</dd>
      <dt>Name</dt><dd>${escapeHtml([user.first_name, user.last_name].filter(Boolean).join(' ') || '—')}</dd>
      <dt>Channel</dt><dd>${escapeHtml(user.source_channel || '—')}</dd>
    </dl>
  `);

  html += section('Purchase request', `
    <dl class="detail-dl">
      <dt>Car</dt><dd>${escapeHtml(car.brand_name || '')} ${escapeHtml(car.name || '—')}</dd>
      <dt>City</dt><dd>${escapeHtml(pr.city)}</dd>
      <dt>Color</dt><dd>${escapeHtml(pr.color || '—')}</dd>
      <dt>Year range</dt><dd>${pr.production_year_min || '—'} – ${pr.production_year_max || '—'}</dd>
      <dt>Usage max</dt><dd>${fmtNum(pr.usage_max)} km</dd>
      <dt>Pricing</dt><dd>${escapeHtml(d.pricing_platform || '—')}</dd>
      <dt>Listing mapping</dt><dd>${pr.listing_mapping_configured ? 'configured' : `not configured — add at ${escapeHtml(trimMappingHref())}`}</dd>
      <dt>Active</dt><dd>${pr.is_active ? 'yes (valid 2 days from create)' : 'no — cancelled or expired'}</dd>
      <dt>Expires</dt><dd>${fmtDate(pr.expires_at)}</dd>
      <dt>Divar URL</dt><dd>${pr.generated_divar_url ? `<a href="${escapeHtml(pr.generated_divar_url)}" target="_blank">${escapeHtml(pr.generated_divar_url)}</a>` : '— (no listing mapping for this trim)'}</dd>
    </dl>
  `);

  if (!d.crawl_targets.length) {
    html += section('Crawl targets', `<p class="empty-inline">No Divar listing mapping for this trim — configure at <a href="${escapeHtml(trimMappingHref())}">${escapeHtml(trimMappingHref())}</a></p>`);
  } else if (d.crawl_targets.length) {
    html += section('Crawl targets', `
      <ul class="detail-list">
        ${d.crawl_targets.map(t => `
          <li>
            <strong>${escapeHtml(t.source)}</strong> · poll ${t.poll_interval_sec}s · ${t.is_active ? 'active' : 'inactive'}<br>
            <a href="${escapeHtml(t.listing_url)}" target="_blank">${escapeHtml(t.listing_url)}</a>
          </li>
        `).join('')}
      </ul>
    `);
  }

  if (d.crawl_runs.length) {
    const selectedRun = detailState.crawlRunId;
    html += section('Crawl runs (all)', `
      <p class="cell-sub">Click a run to show its listings below (20 per page).</p>
      <table class="inner-table">
        <thead><tr><th>Started</th><th>Status</th><th>Posts</th><th>Opps</th><th>Listings</th><th>Error</th><th></th></tr></thead>
        <tbody>
          ${d.crawl_runs.map(r => `
            <tr class="${selectedRun === r.id ? 'row-selected' : ''}">
              <td>${fmtDate(r.started_at)}</td>
              <td>${escapeHtml(r.status)}</td>
              <td>${r.posts_found}</td>
              <td>${r.opportunities_found}</td>
              <td>${fmtNum(r.listings_count ?? 0)}</td>
              <td>${escapeHtml(r.error_message || '—')}</td>
              <td><button type="button" class="link-btn crawl-run-filter-btn" data-run-id="${r.id}">Show listings</button></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `);
  } else {
    html += section('Crawl runs', '<p class="empty-inline">No crawl runs yet</p>');
  }

  html += section('Crawl diagnostics (why no opportunity?)', renderDiagnostics(d.crawl_runs || []));

  const listingsTitle = detailState.crawlRunId
    ? 'Found listings for selected crawl run (Divar + market price)'
    : 'Found listings (Divar + market price)';
  const pag = d.listings_pagination || {};
  const listingsCountNote = pag.total != null ? ` <span class="cell-sub">(${fmtNum(pag.total)} total · 20 per page)</span>` : '';
  html += section(`${listingsTitle}${listingsCountNote}`, renderListings(d.listings || [], d.listings_pagination, purchaseId));

  if (d.opportunities.length) {
    html += section('Opportunities', `
      <div class="sms-toolbar">
        <label><input type="checkbox" id="selectAllOpps"> Select all</label>
        <button class="btn-secondary" id="approveOppsBtn" data-id="${purchaseId}">Approve</button>
        <button class="btn-secondary" id="rejectOppsBtn" data-id="${purchaseId}">Reject</button>
        <button class="btn-secondary" id="sendGatewaySmsBtn" data-id="${purchaseId}">Send gateway links SMS</button>
        <button class="btn-secondary" id="sendPortalSmsBtn" data-id="${purchaseId}">Send portal share SMS</button>
        <span id="smsMsg" class="cell-sub"></span>
      </div>
      <table class="inner-table">
        <thead><tr><th></th><th>Tag</th><th>Listing</th><th>Price</th><th>Reference</th><th>Discount %</th><th>Status</th><th>Link</th></tr></thead>
        <tbody>
          ${d.opportunities.map(o => `
            <tr>
              <td><input type="checkbox" class="opp-check" value="${o.id}"></td>
              <td>${dealTagBadge(o.deal_tag)}</td>
              <td>${escapeHtml(o.listing_title || '—')}</td>
              <td>${fmtNum(o.listing_price)}</td>
              <td>${fmtNum(o.reference_price || o.market_price_mid || o.market_price_up)}</td>
              <td>${fmtNum(o.discount_pct)}%</td>
              <td>${escapeHtml(o.status)}</td>
              <td>${o.divar_url ? `<a href="${escapeHtml(o.divar_url)}" target="_blank">Divar</a>` : '—'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `);
  } else {
    html += section('Opportunities', '<p class="empty-inline">No opportunities found</p>');
  }

  if (d.deliveries.length) {
    html += section('SMS deliveries', `
      <table class="inner-table">
        <thead><tr><th>Listing</th><th>SMS</th><th>Sent at</th><th>Gateway</th></tr></thead>
        <tbody>
          ${d.deliveries.map(dv => `
            <tr>
              <td>${escapeHtml(dv.listing_title || '—')}</td>
              <td>${escapeHtml(dv.sms_status)}</td>
              <td>${fmtDate(dv.sms_sent_at)}</td>
              <td><a href="/g/${dv.gateway_token}" target="_blank">/g/${dv.gateway_token}</a></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `);
  } else {
    html += section('SMS deliveries', '<p class="empty-inline">No SMS sent yet</p>');
  }

  return html;
}

async function reviewOpportunities(purchaseId, action) {
  const checks = document.querySelectorAll('.opp-check:checked');
  const ids = Array.from(checks).map((c) => c.value);
  const msg = document.getElementById('smsMsg');
  if (!ids.length) {
    if (msg) msg.textContent = 'Select at least one opportunity';
    return;
  }
  if (msg) msg.textContent = action === 'approve' ? 'Approving...' : 'Rejecting...';
  try {
    const r = await api(`/crawl-results/${purchaseId}/review-opportunities`, {
      method: 'POST',
      body: JSON.stringify({ opportunity_ids: ids, action }),
    });
    if (msg) msg.textContent = `${action === 'approve' ? 'Approved' : 'Rejected'} ${r.updated} opportunity(s)`;
    setTimeout(() => openDetail(purchaseId), 800);
  } catch (e) {
    if (msg) msg.textContent = e.message;
  }
}

async function sendOpportunitySms(purchaseId, mode) {
  const checks = document.querySelectorAll('.opp-check:checked');
  const ids = Array.from(checks).map((c) => c.value);
  const msg = document.getElementById('smsMsg');
  if (!ids.length) {
    if (msg) msg.textContent = 'Select at least one opportunity';
    return;
  }
  if (msg) msg.textContent = 'Sending...';
  try {
    const r = await api(`/crawl-results/${purchaseId}/send-sms`, {
      method: 'POST',
      body: JSON.stringify({ opportunity_ids: ids, mode }),
    });
    if (msg) {
      msg.textContent = `Sent ${r.sms_sent} SMS · ${r.deliveries_created} deliveries` +
        (r.share_url ? ` · ${r.share_url}` : '');
    }
    setTimeout(() => openDetail(purchaseId), 2000);
  } catch (e) {
    if (msg) msg.textContent = e.message;
  }
}

async function runCrawlForPurchase(id) {
  const msg = document.getElementById('runCrawlMsg');
  if (msg) msg.textContent = 'Starting...';
  try {
    const r = await api(`/crawl-tasks/purchase/${id}/run-now`, { method: 'POST' });
    const count = (r.crawl_target_ids || []).length;
    if (!count) {
      if (msg) msg.textContent = 'No crawl targets — configure Trim Mapping for this trim first';
      return;
    }
    if (msg) {
      msg.textContent = `${r.message || 'Crawl started'} (${count} target${count === 1 ? '' : 's'})`;
    }
    pollDetailAfterCrawl(id, msg);
  } catch (e) {
    if (msg) msg.textContent = e.message;
  }
}

function pollDetailAfterCrawl(id, msgEl) {
  let attempts = 0;
  const maxAttempts = 12;
  const timer = setInterval(async () => {
    attempts += 1;
    try {
      const d = await api(`/crawl-results/${id}`);
      const runs = d.crawl_runs || [];
      const latest = runs[0];
      if (latest && latest.status !== 'running') {
        clearInterval(timer);
        if (msgEl) {
          msgEl.textContent = `Crawl ${latest.status} — ${latest.posts_found ?? 0} posts, ${latest.opportunities_found ?? 0} opportunities`;
        }
        await openDetail(id);
        return;
      }
      if (attempts >= maxAttempts) {
        clearInterval(timer);
        if (msgEl) msgEl.textContent += ' — still running, click Refresh';
        await openDetail(id);
      }
    } catch {
      if (attempts >= maxAttempts) clearInterval(timer);
    }
  }, 5000);
}

async function openDetail(id, options = {}) {
  if (options.reset) {
    detailState = { purchaseId: id, listingsPage: 1, crawlRunId: null };
  } else if (detailState.purchaseId !== id) {
    detailState = { purchaseId: id, listingsPage: 1, crawlRunId: null };
  }
  if (options.listingsPage != null) detailState.listingsPage = options.listingsPage;
  if (options.crawlRunId !== undefined) detailState.crawlRunId = options.crawlRunId;

  const modal = document.getElementById('detailModal');
  const content = document.getElementById('detailContent');
  modal.classList.remove('hidden');
  content.textContent = 'Loading...';
  const params = new URLSearchParams({
    listings_page: String(detailState.listingsPage),
    listings_per_page: '20',
  });
  if (detailState.crawlRunId) params.set('crawl_run_id', detailState.crawlRunId);
  try {
    const detail = await api(`/crawl-results/${id}?${params.toString()}`);
    content.innerHTML = renderDetail(detail, id);
    const btn = document.getElementById('runCrawlBtn');
    if (btn) btn.addEventListener('click', () => runCrawlForPurchase(id));
    const selectAll = document.getElementById('selectAllOpps');
    if (selectAll) {
      selectAll.addEventListener('change', () => {
        document.querySelectorAll('.opp-check').forEach((c) => {
          c.checked = selectAll.checked;
        });
      });
    }
    const gwBtn = document.getElementById('sendGatewaySmsBtn');
    if (gwBtn) gwBtn.addEventListener('click', () => sendOpportunitySms(id, 'gateway'));
    const portalBtn = document.getElementById('sendPortalSmsBtn');
    if (portalBtn) portalBtn.addEventListener('click', () => sendOpportunitySms(id, 'portal'));
    const approveBtn = document.getElementById('approveOppsBtn');
    if (approveBtn) approveBtn.addEventListener('click', () => reviewOpportunities(id, 'approve'));
    const rejectBtn = document.getElementById('rejectOppsBtn');
    if (rejectBtn) rejectBtn.addEventListener('click', () => reviewOpportunities(id, 'reject'));
    document.querySelectorAll('.crawl-run-filter-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        openDetail(id, { crawlRunId: btn.dataset.runId, listingsPage: 1 });
      });
    });
    document.querySelectorAll('[data-page-action]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.pageAction;
        const pg = detailState.listingsPage;
        const pag = normalizeListingsPagination(detail.listings_pagination, detail.listings || [], pg);
        if (action === 'prev' && pg > 1) {
          openDetail(id, { listingsPage: pg - 1 });
        } else if (action === 'next' && pg < pag.total_pages) {
          openDetail(id, { listingsPage: pg + 1 });
        } else if (action === 'clear-run') {
          openDetail(id, { crawlRunId: null, listingsPage: 1 });
        }
      });
    });
  } catch (e) {
    content.innerHTML = `<p class="error">${escapeHtml(e.message)}</p>`;
  }
}

async function loadTaskStatus() {
  const panel = document.getElementById('taskStatusPanel');
  try {
    const s = await api('/crawl-tasks/status');
    panel.classList.remove('hidden', 'ok');
    if (s.redis_ok && !s.running_crawls && s.failed_crawls === 0) panel.classList.add('ok');
    panel.innerHTML = `
      <strong>Crawl scheduler</strong>
      Redis: ${s.redis_ok ? 'OK' : 'DOWN'} ·
      Active purchases: ${s.active_purchases} ·
      Running: ${s.running_crawls} · Failed: ${s.failed_crawls} · Completed: ${s.completed_crawls}
      <ul>${(s.hints || []).map(h => `<li>${h}</li>`).join('')}</ul>
    `;
  } catch (e) {
    panel.classList.remove('hidden', 'ok');
    panel.innerHTML = `<strong>Task status unavailable:</strong> ${e.message}`;
  }
}

function closeModal() {
  document.getElementById('detailModal').classList.add('hidden');
}

async function loadResults() {
  const status = document.getElementById('statusText');
  status.textContent = 'Loading...';
  loadTaskStatus();
  try {
    const rows = await api('/crawl-results');
    renderTable(rows);
    status.textContent = `${rows.length} purchase request(s)`;
  } catch (e) {
    document.getElementById('resultsBody').innerHTML =
      `<tr><td colspan="12" class="empty error">${e.message}</td></tr>`;
    status.textContent = 'Error';
  }
}

document.getElementById('refreshBtn').addEventListener('click', loadResults);
document.getElementById('closeModalBtn').addEventListener('click', closeModal);
document.getElementById('modalBackdrop').addEventListener('click', closeModal);

loadResults();
