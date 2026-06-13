const API = '/api/v1';

function escapeHtml(value) {
  if (value == null) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data));
  return data;
}

function renderMappings(rows) {
  const tbody = document.getElementById('mappingsBody');
  const sel = document.getElementById('targetMappingSelect');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty">No mappings yet</td></tr>';
    sel.innerHTML = '<option value="">No mappings</option>';
    return;
  }
  tbody.innerHTML = rows.map((m) => `
    <tr>
      <td>${escapeHtml(m.listing_platform_slug)}</td>
      <td>${escapeHtml(m.divar_car_model_display)}</td>
      <td><code>${escapeHtml(m.divar_car_model_slug)}</code></td>
      <td><code>${escapeHtml(m.path)}</code></td>
      <td>${m.trim_count} — ${escapeHtml((m.trims || []).map((t) => t.name).slice(0, 4).join(', '))}${m.trim_count > 4 ? '…' : ''}</td>
      <td>${m.is_active ? 'yes' : 'no'}</td>
    </tr>
  `).join('');
  sel.innerHTML = rows.map((m) =>
    `<option value="${m.id}">${escapeHtml(m.divar_car_model_display)} — ${escapeHtml(m.path)} (${m.trim_count} trims)</option>`
  ).join('');
}

async function loadMappings() {
  const status = document.getElementById('mappingStatus');
  status.textContent = 'Loading...';
  try {
    const rows = await api('/listing-mappings');
    renderMappings(rows);
    status.textContent = `${rows.length} mapping(s)`;
  } catch (e) {
    document.getElementById('mappingsBody').innerHTML =
      `<tr><td colspan="6" class="empty error">${escapeHtml(e.message)}</td></tr>`;
    status.textContent = 'Error';
  }
}

function initDivarModelSearch() {
  const sel = document.getElementById('divarModelSelect');
  sel.setAttribute('data-empty-label', 'Select Divar car model');
  sel.innerHTML = '<option value="">Select Divar car model</option>';
  SearchableSelect.enhance(sel, {
    placeholder: 'Search Divar model (e.g. Peugeot 207)…',
    noResultsText: 'No Divar models found',
    typeToSearchText: 'Type at least 2 characters to search all 2100+ models',
    fetchOptions: async (q) => {
      const models = await api(`/divar/car-models?q=${encodeURIComponent(q)}&limit=50`);
      return models.map((m) => ({
        value: m.id,
        label: `${m.display} — ${m.slug}`,
        slug: m.slug,
      }));
    },
  });
}

async function loadBrands() {
  const brands = await api('/car-brands');
  const sel = document.getElementById('brandSelect');
  sel.innerHTML = '<option value="">Select brand</option>';
  brands.forEach((b) => {
    const o = document.createElement('option');
    o.value = b.id;
    o.textContent = b.name;
    sel.appendChild(o);
  });
}

document.getElementById('brandSelect').addEventListener('change', async (e) => {
  const q = e.target.value ? `?brand_id=${e.target.value}` : '';
  const models = await api('/car-models' + q);
  const sel = document.getElementById('modelSelect');
  sel.innerHTML = '<option value="">Select model</option>';
  document.getElementById('yearSelect').innerHTML = '<option value="">All years</option>';
  document.getElementById('trimChecks').innerHTML = 'Select a model to load trims';
  models.forEach((m) => {
    const o = document.createElement('option');
    o.value = m.id;
    o.textContent = `${m.brand_name || ''} ${m.name}`.trim();
    sel.appendChild(o);
  });
});

document.getElementById('modelSelect').addEventListener('change', async (e) => {
  const modelId = e.target.value;
  if (!modelId) return;
  const years = await api(`/car-years?model_id=${modelId}`);
  const yearSel = document.getElementById('yearSelect');
  yearSel.innerHTML = '<option value="">All years</option>';
  years.forEach((y) => {
    const o = document.createElement('option');
    o.value = y.id;
    o.textContent = y.title;
    yearSel.appendChild(o);
  });
  await loadTrimChecks(modelId, null);
});

document.getElementById('yearSelect').addEventListener('change', async (e) => {
  const modelId = document.getElementById('modelSelect').value;
  if (!modelId) return;
  await loadTrimChecks(modelId, e.target.value || null);
});

async function loadTrimChecks(modelId, yearId) {
  const box = document.getElementById('trimChecks');
  const trimSearch = document.getElementById('trimSearch');
  if (trimSearch) trimSearch.value = '';
  box.textContent = 'Loading trims...';
  let q = `?model_id=${modelId}`;
  if (yearId) q += `&year_id=${yearId}`;
  const trims = await api('/car-trims' + q);
  if (!trims.length) {
    box.innerHTML = '<p class="empty-inline">No trims for this filter</p>';
    return;
  }
  box.innerHTML = trims.map((t) => `
    <label class="trim-check-row">
      <input type="checkbox" class="trim-check" value="${t.id}">
      ${escapeHtml(t.year_title || '')} — ${escapeHtml(t.name)}
    </label>
  `).join('');
}

document.getElementById('createMappingBtn').addEventListener('click', async () => {
  const msg = document.getElementById('createMappingMsg');
  msg.textContent = '';
  const path = document.getElementById('mappingPath').value.trim();
  const divarCarModelId = document.getElementById('divarModelSelect').value;
  if (!path || !divarCarModelId) {
    msg.textContent = 'Select a Divar car model from search results and enter path';
    return;
  }
  try {
    const created = await api('/listing-mappings', {
      method: 'POST',
      body: JSON.stringify({
        listing_platform_slug: 'divar',
        divar_car_model_id: divarCarModelId,
        path,
        trim_ids: [],
      }),
    });
    msg.textContent = `Created mapping ${created.id}`;
    await loadMappings();
    document.getElementById('targetMappingSelect').value = created.id;
  } catch (e) {
    msg.textContent = e.message;
  }
});

document.getElementById('linkTrimsBtn').addEventListener('click', async () => {
  const msg = document.getElementById('linkTrimsMsg');
  msg.textContent = '';
  const mappingId = document.getElementById('targetMappingSelect').value;
  const trimIds = Array.from(document.querySelectorAll('.trim-check:checked')).map((c) => c.value);
  if (!mappingId) {
    msg.textContent = 'Select a mapping';
    return;
  }
  if (!trimIds.length) {
    msg.textContent = 'Select at least one trim';
    return;
  }
  try {
    await api(`/listing-mappings/${mappingId}/trims`, {
      method: 'POST',
      body: JSON.stringify({ trim_ids: trimIds }),
    });
    msg.textContent = `Linked ${trimIds.length} trim(s)`;
    await loadMappings();
  } catch (e) {
    msg.textContent = e.message;
  }
});

document.getElementById('refreshMappingsBtn').addEventListener('click', loadMappings);

document.getElementById('trimSearch')?.addEventListener('input', (e) => {
  const q = e.target.value.trim().toLowerCase();
  document.querySelectorAll('.trim-check-row').forEach((row) => {
    const text = row.textContent.toLowerCase();
    row.hidden = q && !text.includes(q);
  });
});

initDivarModelSearch();

SearchableSelect.enhanceCatalog({
  brandSelect: { placeholder: 'Search brand…', noResultsText: 'No brands found' },
  modelSelect: { placeholder: 'Search model…', noResultsText: 'No models found' },
  yearSelect: { placeholder: 'Search year…', noResultsText: 'No years found' },
});

Promise.all([loadBrands(), loadMappings()]).catch((e) => {
  document.getElementById('mappingStatus').textContent = e.message;
});
