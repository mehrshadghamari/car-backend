const API = '/api/v1';
const UI_VERSION = '20250616';
const LISTINGS_PER_PAGE = 20;

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

function buildListingsPaginationState(pagination, listings, page) {
  const perPage = LISTINGS_PER_PAGE;
  const currentPage = page || detailState.listingsPage || 1;
  if (pagination && pagination.total != null) {
    const totalPages = pagination.total_pages != null
      ? pagination.total_pages
      : Math.max(1, Math.ceil(pagination.total / (pagination.per_page || perPage)));
    const hasMore = pagination.has_more != null
      ? pagination.has_more
      : currentPage < totalPages;
    return {
      page: pagination.page || currentPage,
      per_page: pagination.per_page || perPage,
      total: pagination.total,
      total_pages: totalPages,
      has_more: hasMore,
      crawl_run_id: pagination.crawl_run_id || detailState.crawlRunId || null,
    };
  }
  const fullPage = listings.length >= perPage;
  return {
    page: currentPage,
    per_page: perPage,
    total: listings.length,
    total_pages: fullPage ? currentPage + 1 : Math.max(1, currentPage),
    has_more: fullPage,
    crawl_run_id: detailState.crawlRunId || null,
  };
}

function canGoToNextListingsPage(pag, listings) {
  if (pag.has_more) return true;
  if (pag.total_pages != null && pag.page < pag.total_pages) return true;
  if (pag.total != null && pag.page * pag.per_page < pag.total) return true;
  return listings.length >= LISTINGS_PER_PAGE;
}

function createListingsPaginationBar(pag, listings, meta) {
  const frag = cloneTemplate('tplListingsPagination');
  if (!frag) return null;
  const nav = frag.querySelector('.listings-pagination');
  const page = pag.page;
  const from = pag.total ? (page - 1) * pag.per_page + 1 : 0;
  const to = (page - 1) * pag.per_page + listings.length;
  const totalLabel = fmtNum(pag.total);
  const runNote = pag.crawl_run_id ? ' · filtered by crawl run' : '';
  const poolNote = meta && meta.pool_priced_total != null && meta.matching_total != null
    ? ` · ${fmtNum(meta.matching_total)} match purchase (of ${fmtNum(meta.pool_priced_total)} priced in pool)`
    : '';
  const metaEl = nav.querySelector('[data-role="meta"]');
  if (metaEl) {
    metaEl.textContent =
      `Showing ${fmtNum(from)}–${fmtNum(to)} of ${totalLabel} · page ${page} / ${pag.total_pages}${runNote}${poolNote}`;
  }
  const prevBtn = nav.querySelector('[data-page-action="prev"]');
  const nextBtn = nav.querySelector('[data-page-action="next"]');
  if (prevBtn) prevBtn.disabled = page <= 1;
  if (nextBtn) nextBtn.disabled = !canGoToNextListingsPage(pag, listings);
  const clearBtn = nav.querySelector('.listings-clear-run-btn');
  if (clearBtn) {
    if (pag.crawl_run_id) clearBtn.classList.remove('hidden');
    else clearBtn.classList.add('hidden');
  }
  return nav;
}

function fillListingsRow(row, listing) {
  const mp = listing.latest_market_price;
  const links = [];
  if (listing.divar_url) {
    links.push(`<a href="${escapeHtml(listing.divar_url)}" target="_blank" rel="noopener">Divar</a>`);
  }
  if (mp && mp.reference_url) {
    links.push(`<a href="${escapeHtml(mp.reference_url)}" target="_blank" rel="noopener">${escapeHtml(pricingLinkLabel(mp.pricing_provider))}</a>`);
  }
  const set = (role, value) => {
    const el = row.querySelector(`[data-role="${role}"]`);
    if (el) el.innerHTML = value;
  };
  set('title', escapeHtml((listing.title || '—').slice(0, 70)));
  const subtitle = [listing.district || '', listing.color ? ` · ${listing.color}` : ''].join('');
  set('subtitle', escapeHtml(subtitle));
  set('year', listing.production_year ?? '—');
  set('km', fmtNum(listing.kilometer));
  set('price', fmtNum(listing.price));
  set('floor', mp ? fmtNum(mp.price_down) : '—');
  set('mid', mp ? fmtNum(mp.price_mid) : '—');
  set('max', mp ? fmtNum(mp.price_up) : '—');
  set('priced-at', mp ? fmtDate(mp.fetched_at) : '—');
  set('opp', listing.opportunity_still_valid && listing.opportunity_deal_tag
    ? dealTagBadge(listing.opportunity_deal_tag)
    : '—');
  set('links', links.length ? links.join(' · ') : '—');
}

function mountListingsSection(mountEl, listings, pagination, meta) {
  if (!mountEl) return;
  mountEl.innerHTML = '';
  const pag = buildListingsPaginationState(pagination, listings, detailState.listingsPage);

  if (!listings.length && pag.page <= 1) {
    const emptyMsg = pag.crawl_run_id
      ? 'No listings recorded for this crawl run'
      : 'No listings crawled yet — run a crawl to fetch Divar posts and market prices';
    mountEl.innerHTML = `<p class="empty-inline">${emptyMsg}</p>`;
    return;
  }

  const topNav = createListingsPaginationBar(pag, listings, meta);
  if (topNav) mountEl.appendChild(topNav);

  const tableWrap = document.createElement('div');
  tableWrap.className = 'table-wrap listings-table-wrap';
  const table = document.createElement('table');
  table.className = 'inner-table listings-table';
  table.innerHTML = `
    <thead>
      <tr>
        <th>Listing</th><th>Year</th><th>Km</th><th>Divar price</th>
        <th>Floor</th><th>Mid</th><th>Max</th><th>Priced at</th><th>Opp</th><th>Links</th>
      </tr>
    </thead>
    <tbody data-role="listings-tbody"></tbody>
  `;
  const tbody = table.querySelector('[data-role="listings-tbody"]');
  listings.forEach((listing) => {
    const rowFrag = cloneTemplate('tplListingsRow');
    if (!rowFrag) return;
    const row = rowFrag.querySelector('tr');
    fillListingsRow(row, listing);
    tbody.appendChild(row);
  });
  tableWrap.appendChild(table);
  mountEl.appendChild(tableWrap);

  const bottomNav = createListingsPaginationBar(pag, listings, meta);
  if (bottomNav) mountEl.appendChild(bottomNav);
}

function bindListingsInteractions(mountEl, purchaseId) {
  if (!mountEl) return;
  mountEl.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-page-action]');
    if (!btn || !mountEl.contains(btn)) return;
    const action = btn.dataset.pageAction;
    const pg = detailState.listingsPage;
    if (action === 'prev' && pg > 1) {
      openDetail(purchaseId, { listingsPage: pg - 1 });
    } else if (action === 'next') {
      openDetail(purchaseId, { listingsPage: pg + 1 });
    } else if (action === 'clear-run') {
      openDetail(purchaseId, { crawlRunId: null, listingsPage: 1 });
    }
  });
}

const OPP_STATUS_META = {
  new: { label: 'Initial', className: 'badge-yellow' },
  approved: { label: 'Valid', className: 'badge-green' },
  notified: { label: 'SMS sent', className: 'badge-blue' },
};

function opportunityStatusBadge(status) {
  const meta = OPP_STATUS_META[status] || { label: status || '—', className: 'badge-gray' };
  return `<span class="badge ${meta.className}">${meta.label}</span>`;
}

function opportunityLinks(o) {
  const links = [];
  if (o.divar_url) {
    links.push(`<a href="${escapeHtml(o.divar_url)}" target="_blank" rel="noopener">Divar</a>`);
  }
  if (o.reference_url) {
    links.push(
      `<a href="${escapeHtml(o.reference_url)}" target="_blank" rel="noopener">${escapeHtml(pricingLinkLabel(o.pricing_provider))}</a>`
    );
  }
  return links.length ? links.join(' · ') : '—';
}

function cloneTemplate(id) {
  const tpl = document.getElementById(id);
  return tpl ? tpl.content.cloneNode(true) : null;
}

function fillOpportunityRow(row, opportunity, mode) {
  const check = row.querySelector('input[type="checkbox"]');
  if (check) check.value = opportunity.id;
  const set = (role, html) => {
    const el = row.querySelector(`[data-role="${role}"]`);
    if (el) el.innerHTML = html;
  };
  set('tag', dealTagBadge(opportunity.deal_tag));
  set('title', escapeHtml(opportunity.listing_title || '—'));
  set('price', fmtNum(opportunity.listing_price));
  set('max-ref', fmtNum(opportunity.reference_price || opportunity.market_price_up || opportunity.market_price_mid));
  set('discount', `${fmtNum(opportunity.discount_pct)}%`);
  set('status', opportunityStatusBadge(opportunity.status));
  set('links', opportunityLinks(opportunity));
  if (mode === 'initial') {
    row.querySelectorAll('[data-action="approve-one"], [data-action="reject-one"]').forEach((btn) => {
      btn.dataset.oppId = opportunity.id;
    });
  }
}

function mountOpportunityRows(tbody, opportunities, mode) {
  const rowTplId = mode === 'initial' ? 'tplOppRowInitial' : 'tplOppRowValid';
  opportunities.forEach((opp) => {
    const rowFrag = cloneTemplate(rowTplId);
    if (!rowFrag) return;
    const row = rowFrag.querySelector('tr');
    fillOpportunityRow(row, opp, mode);
    tbody.appendChild(row);
  });
}

function mountOpportunitiesWorkflow(mountEl, opportunities, purchaseId) {
  if (!mountEl) return;

  const initialOpps = (opportunities || []).filter((o) => o.status === 'new');
  const validOpps = (opportunities || []).filter((o) => o.status === 'approved' || o.status === 'notified');

  mountEl.innerHTML = '';
  mountEl.dataset.purchaseId = purchaseId;

  if (!initialOpps.length && !validOpps.length) {
    mountEl.innerHTML = '<p class="empty-inline">No opportunities found</p>';
    return;
  }

  const workflowFrag = cloneTemplate('tplOppWorkflow');
  if (!workflowFrag) {
    mountEl.innerHTML = renderOpportunitiesSectionsFallback(opportunities, purchaseId);
    return;
  }

  const workflow = workflowFrag.querySelector('.opp-workflow');
  const initialMount = workflow.querySelector('[data-role="initial-mount"]');
  const validMount = workflow.querySelector('[data-role="valid-mount"]');

  if (initialOpps.length) {
    const initialFrag = cloneTemplate('tplOppInitial');
    const initialPanel = initialFrag.querySelector('.opp-panel');
    initialPanel.querySelector('[data-role="title-count"]').textContent =
      `Initial opportunities (${initialOpps.length})`;
    mountOpportunityRows(initialPanel.querySelector('[data-role="tbody"]'), initialOpps, 'initial');
    initialMount.appendChild(initialPanel);
  }

  if (validOpps.length) {
    const validFrag = cloneTemplate('tplOppValid');
    const validPanel = validFrag.querySelector('.opp-panel');
    validPanel.querySelector('[data-role="title-count"]').textContent =
      `Validated opportunities (${validOpps.length}) — SMS enabled`;
    mountOpportunityRows(validPanel.querySelector('[data-role="tbody"]'), validOpps, 'valid');
    validMount.appendChild(validPanel);
  } else {
    const emptyFrag = cloneTemplate('tplOppValidEmpty');
    if (emptyFrag) validMount.appendChild(emptyFrag.querySelector('.opp-panel'));
  }

  mountEl.appendChild(workflow);
}

function renderOpportunitiesSectionsFallback(opportunities, purchaseId) {
  return renderOpportunitiesSections(opportunities, purchaseId);
}

function bindOpportunitiesInteractions(container, purchaseId) {
  if (!container) return;

  container.addEventListener('change', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;
    if (target.matches('[data-role="select-all"]')) {
      const panel = target.closest('.opp-panel');
      if (!panel) return;
      const isInitial = panel.classList.contains('opp-panel-initial');
      const selector = isInitial ? '.opp-check-review' : '.opp-check-sms';
      panel.querySelectorAll(selector).forEach((cb) => {
        cb.checked = target.checked;
      });
    }
  });

  container.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-action]');
    if (!btn || !container.contains(btn)) return;

    const action = btn.dataset.action;
    const panel = btn.closest('.opp-panel');
    const reviewMsg = container.querySelector('[data-role="review-msg"]');
    const smsMsg = container.querySelector('[data-role="sms-msg"]');

    if (action === 'approve-selected') {
      const ids = Array.from(container.querySelectorAll('.opp-check-review:checked')).map((c) => c.value);
      reviewOpportunities(purchaseId, 'approve', ids, reviewMsg);
      return;
    }
    if (action === 'reject-selected') {
      const ids = Array.from(container.querySelectorAll('.opp-check-review:checked')).map((c) => c.value);
      reviewOpportunities(purchaseId, 'reject', ids, reviewMsg);
      return;
    }
    if (action === 'approve-one' && btn.dataset.oppId) {
      reviewOpportunities(purchaseId, 'approve', [btn.dataset.oppId], reviewMsg);
      return;
    }
    if (action === 'reject-one' && btn.dataset.oppId) {
      reviewOpportunities(purchaseId, 'reject', [btn.dataset.oppId], reviewMsg);
      return;
    }
    if (action === 'sms-gateway') {
      const ids = Array.from(container.querySelectorAll('.opp-check-sms:checked')).map((c) => c.value);
      sendOpportunitySms(purchaseId, 'gateway', ids, smsMsg);
      return;
    }
    if (action === 'sms-portal') {
      const ids = Array.from(container.querySelectorAll('.opp-check-sms:checked')).map((c) => c.value);
      sendOpportunitySms(purchaseId, 'portal', ids, smsMsg);
    }
  });
}

function renderOpportunityTableRows(opportunities, options = {}) {
  const checkboxClass = options.checkboxClass || '';
  const showRowActions = options.showRowActions === true;
  const purchaseId = options.purchaseId || '';

  return opportunities.map((o) => `
    <tr class="${options.rowClass || ''}">
      <td><input type="checkbox" class="${checkboxClass}" value="${o.id}"></td>
      <td>${dealTagBadge(o.deal_tag)}</td>
      <td>${escapeHtml(o.listing_title || '—')}</td>
      <td>${fmtNum(o.listing_price)}</td>
      <td>${fmtNum(o.reference_price || o.market_price_up || o.market_price_mid)}</td>
      <td>${fmtNum(o.discount_pct)}%</td>
      <td>${opportunityStatusBadge(o.status)}</td>
      <td class="link-cell">${opportunityLinks(o)}</td>
      ${showRowActions ? `
        <td class="link-cell">
          <button type="button" class="link-btn opp-validate-one-btn" data-purchase-id="${purchaseId}" data-opp-id="${o.id}">Mark valid</button>
          <button type="button" class="link-btn opp-reject-one-btn" data-purchase-id="${purchaseId}" data-opp-id="${o.id}">Reject</button>
        </td>
      ` : ''}
    </tr>
  `).join('');
}

function renderOpportunitiesSections(opportunities, purchaseId) {
  const initialOpps = opportunities.filter((o) => o.status === 'new');
  const validOpps = opportunities.filter((o) => o.status === 'approved' || o.status === 'notified');

  if (!initialOpps.length && !validOpps.length) {
    return section('Opportunities', '<p class="empty-inline">No opportunities found</p>');
  }

  let html = '';

  if (initialOpps.length) {
    html += section(`Initial opportunities (${initialOpps.length})`, `
      <div class="opp-section opp-section-initial">
        <p class="cell-sub">Auto-created by crawl. Open Divar / Hamrah links to review. Use <strong>Mark valid</strong> (single or bulk) — <em>SMS is not available here</em>.</p>
        <div class="sms-toolbar">
          <label><input type="checkbox" id="selectAllInitialOpps"> Select all</label>
          <button type="button" class="btn-secondary" id="approveOppsBtn">Mark selected valid</button>
          <button type="button" class="btn-secondary" id="rejectOppsBtn">Reject selected</button>
          <span id="reviewMsg" class="cell-sub"></span>
        </div>
        <table class="inner-table opp-table-initial">
          <thead><tr>
            <th></th><th>Tag</th><th>Listing</th><th>Price</th><th>Max ref</th><th>Discount vs max</th><th>Status</th><th>Links</th><th>Actions</th>
          </tr></thead>
          <tbody>${renderOpportunityTableRows(initialOpps, {
            checkboxClass: 'opp-check-review',
            showRowActions: true,
            purchaseId,
            rowClass: 'opp-row-initial',
          })}</tbody>
        </table>
      </div>
    `);
  }

  if (validOpps.length) {
    html += section(`Validated opportunities (${validOpps.length}) — SMS enabled`, `
      <div class="opp-section opp-section-valid">
        <p class="cell-sub">Staff-approved. Select one or more rows, then send gateway links or portal share SMS.</p>
        <div class="sms-toolbar">
          <label><input type="checkbox" id="selectAllValidOpps"> Select all</label>
          <button type="button" class="btn-secondary" id="sendGatewaySmsBtn">Send gateway links SMS</button>
          <button type="button" class="btn-secondary" id="sendPortalSmsBtn">Send portal share SMS</button>
          <span id="smsMsg" class="cell-sub"></span>
        </div>
        <table class="inner-table opp-table-valid">
          <thead><tr>
            <th></th><th>Tag</th><th>Listing</th><th>Price</th><th>Max ref</th><th>Discount vs max</th><th>Status</th><th>Links</th>
          </tr></thead>
          <tbody>${renderOpportunityTableRows(validOpps, {
            checkboxClass: 'opp-check-sms',
            rowClass: 'opp-row-valid',
          })}</tbody>
        </table>
      </div>
    `);
  } else {
    html += section('Validated opportunities — SMS enabled', `
      <div class="opp-section opp-section-valid empty">
        <p class="empty-inline">No validated opportunities yet. Mark initial rows as valid above to enable SMS.</p>
      </div>
    `);
  }

  return html;
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
  const pag = buildListingsPaginationState(d.listings_pagination, d.listings || [], detailState.listingsPage);
  const meta = d.listings_meta || {};
  const latestPosts = d.crawl_runs && d.crawl_runs[0] ? d.crawl_runs[0].posts_found : null;
  let listingsCountNote = '';
  if (pag.total != null) {
    listingsCountNote = ` <span class="cell-sub">(${fmtNum(pag.total)} matching · ${pag.per_page} per page`;
    if (latestPosts != null) listingsCountNote += ` · latest crawl fetched ${fmtNum(latestPosts)} posts`;
    listingsCountNote += ')</span>';
  }
  html += section(`${listingsTitle}${listingsCountNote}`, '<div id="listingsMount" class="listings-mount"></div>');

  html += section('Opportunities workflow', '<div id="opportunitiesMount" class="opportunities-mount"></div>');

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

async function reviewOpportunities(purchaseId, action, opportunityIds = null, msgEl = null) {
  const checks = opportunityIds
    ? null
    : document.querySelectorAll('.opp-check-review:checked');
  const ids = opportunityIds || Array.from(checks).map((c) => c.value);
  const msg = msgEl || document.querySelector('[data-role="review-msg"]');
  if (!ids.length) {
    if (msg) msg.textContent = 'Select at least one initial opportunity';
    return;
  }
  if (msg) msg.textContent = action === 'approve' ? 'Validating...' : 'Rejecting...';
  try {
    const r = await api(`/crawl-results/${purchaseId}/review-opportunities`, {
      method: 'POST',
      body: JSON.stringify({ opportunity_ids: ids, action }),
    });
    if (msg) msg.textContent = `${action === 'approve' ? 'Validated' : 'Rejected'} ${r.updated} opportunity(s)`;
    setTimeout(() => openDetail(purchaseId), 800);
  } catch (e) {
    if (msg) msg.textContent = e.message;
  }
}

async function sendOpportunitySms(purchaseId, mode, opportunityIds = null, msgEl = null) {
  const checks = opportunityIds
    ? null
    : document.querySelectorAll('.opp-check-sms:checked');
  const ids = opportunityIds || Array.from(checks).map((c) => c.value);
  const msg = msgEl || document.querySelector('[data-role="sms-msg"]');
  if (!ids.length) {
    if (msg) msg.textContent = 'Select at least one validated opportunity';
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
    listings_per_page: String(LISTINGS_PER_PAGE),
  });
  if (detailState.crawlRunId) params.set('crawl_run_id', detailState.crawlRunId);
  try {
    const detail = await api(`/crawl-results/${id}?${params.toString()}`);
    content.innerHTML = renderDetail(detail, id);

    const listingsMount = document.getElementById('listingsMount');
    mountListingsSection(
      listingsMount,
      detail.listings || [],
      detail.listings_pagination,
      detail.listings_meta,
    );
    bindListingsInteractions(listingsMount, id);

    const oppMount = document.getElementById('opportunitiesMount');
    mountOpportunitiesWorkflow(oppMount, detail.opportunities || [], id);
    bindOpportunitiesInteractions(oppMount, id);

    const btn = document.getElementById('runCrawlBtn');
    if (btn) btn.addEventListener('click', () => runCrawlForPurchase(id));
    document.querySelectorAll('.crawl-run-filter-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        openDetail(id, { crawlRunId: btn.dataset.runId, listingsPage: 1 });
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
