const API = '/api/v1';

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

function log(obj) {
  document.getElementById('output').textContent = JSON.stringify(obj, null, 2);
}

let brands = [];
let models = [];
let years = [];
let trims = [];

function yearCatalogValue(y) {
  if (y.jalali_year != null) return String(y.jalali_year);
  return y.title;
}

function parseYearValue(value) {
  if (!value) return null;
  const n = parseInt(String(value).replace(/[^\d]/g, ''), 10);
  return Number.isFinite(n) ? n : null;
}

function fillYearRangeSelects(catalogYears, selectedValue) {
  ['yearMinSelect', 'yearMaxSelect'].forEach((id) => {
    const sel = document.getElementById(id);
    sel.innerHTML = '<option value="">Select year</option>';
    catalogYears.forEach((y) => {
      const o = document.createElement('option');
      o.value = yearCatalogValue(y);
      o.textContent = y.title;
      sel.appendChild(o);
    });
    if (selectedValue) sel.value = selectedValue;
  });
}

async function loadBrands() {
  brands = await api('/car-brands');
  const sel = document.getElementById('brandSelect');
  sel.innerHTML = '<option value="">Select brand</option>';
  brands.forEach(b => {
    const o = document.createElement('option');
    o.value = b.id;
    o.textContent = b.name;
    sel.appendChild(o);
  });
}

async function loadModels(brandId) {
  const q = brandId ? `?brand_id=${brandId}` : '';
  models = await api('/car-models' + q);
  const sel = document.getElementById('modelSelect');
  sel.innerHTML = '<option value="">Select model</option>';
  document.getElementById('yearSelect').innerHTML = '<option value="">Select year</option>';
  document.getElementById('trimSelect').innerHTML = '<option value="">Select trim</option>';
  fillYearRangeSelects([]);
  models.forEach(m => {
    const o = document.createElement('option');
    o.value = m.id;
    o.textContent = `${m.brand_name || ''} ${m.name}`.trim();
    sel.appendChild(o);
  });
}

async function loadYears(modelId) {
  if (!modelId) return;
  years = await api(`/car-years?model_id=${modelId}`);
  const sel = document.getElementById('yearSelect');
  sel.innerHTML = '<option value="">Select year</option>';
  document.getElementById('trimSelect').innerHTML = '<option value="">Select trim</option>';
  years.forEach(y => {
    const o = document.createElement('option');
    o.value = y.id;
    o.textContent = y.title;
    sel.appendChild(o);
  });
  fillYearRangeSelects(years);
}

async function loadTrims(modelId, yearId) {
  if (!modelId) return;
  let q = `?model_id=${modelId}`;
  if (yearId) q += `&year_id=${yearId}`;
  trims = await api('/car-trims' + q);
  const sel = document.getElementById('trimSelect');
  sel.innerHTML = '<option value="">Select trim</option>';
  trims.forEach(t => {
    const o = document.createElement('option');
    o.value = t.id;
    o.dataset.yearValue = t.year_title || '';
    o.textContent = `${t.year_title || ''} — ${t.name}`.trim();
    sel.appendChild(o);
  });
}

function getFilters() {
  const yearMin = parseYearValue(document.getElementById('yearMinSelect').value);
  const yearMax = parseYearValue(document.getElementById('yearMaxSelect').value);
  if (yearMin != null && yearMax != null && yearMin > yearMax) {
    throw new Error('Min year cannot be greater than max year');
  }
  const usageMax = document.getElementById('usageMax').value;
  return {
    car_trim_id: document.getElementById('trimSelect').value,
    pricing_platform_slug: document.getElementById('pricingPlatform').value,
    city: document.getElementById('citySelect').value || 'tehran',
    color: document.getElementById('color').value || null,
    production_year_min: yearMin,
    production_year_max: yearMax ?? yearMin,
    usage_max: usageMax ? parseInt(usageMax) : null,
    sample_production_year: yearMin || 1403,
    sample_kilometer: usageMax ? parseInt(usageMax) : 30000,
  };
}

document.getElementById('brandSelect').addEventListener('change', e => {
  loadModels(e.target.value);
});

document.getElementById('modelSelect').addEventListener('change', e => {
  loadYears(e.target.value);
});

document.getElementById('yearSelect').addEventListener('change', e => {
  loadTrims(document.getElementById('modelSelect').value, e.target.value);
});

document.getElementById('trimSelect').addEventListener('change', e => {
  const opt = e.target.selectedOptions[0];
  const yearValue = opt?.dataset?.yearValue;
  if (yearValue) fillYearRangeSelects(years, yearValue);
});

document.getElementById('previewBtn').addEventListener('click', async () => {
  try {
    const f = getFilters();
    if (!f.car_trim_id) return alert('Please select brand, model, year, and trim');
    const result = await api('/preview-urls', { method: 'POST', body: JSON.stringify(f) });
    document.getElementById('divarUrl').href = result.divar_url;
    document.getElementById('divarUrl').textContent = result.divar_url;
    const pricingUrl = result.pricing_url || result.khodro45_url;
    document.getElementById('pricingUrl').href = pricingUrl;
    document.getElementById('pricingUrl').textContent = pricingUrl;
    document.getElementById('urlMeta').textContent =
      `Platform: ${result.pricing_platform_slug}\nTrim: ${result.trim_name || '—'}\nYear: ${result.year_title || '—'}\nDivar path: ${result.divar_path}\nKhodro45 slug: ${result.khodro45_slug || '—'}`;
    log(result);
  } catch (e) { log({ error: e.message }); }
});

document.getElementById('runScenarioBtn').addEventListener('click', async () => {
  try {
    const f = getFilters();
    if (!f.car_trim_id) return alert('Please select brand, model, year, and trim');
    const body = {
      car_trim_id: f.car_trim_id,
      pricing_platform_slug: f.pricing_platform_slug,
      phone: document.getElementById('phone').value,
      first_name: document.getElementById('firstName').value,
      source_channel: document.getElementById('channel').value,
      city: f.city,
      color: f.color,
      production_year_min: f.production_year_min,
      production_year_max: f.production_year_max,
      usage_max: f.usage_max,
      run_crawl: document.getElementById('runCrawl').checked,
    };
    const result = await api('/flow/scenario', { method: 'POST', body: JSON.stringify(body) });
    document.getElementById('divarUrl').href = result.divar_url;
    document.getElementById('divarUrl').textContent = result.divar_url;
    const pricingUrl = result.pricing_preview_url;
    document.getElementById('pricingUrl').href = pricingUrl;
    document.getElementById('pricingUrl').textContent = pricingUrl;
    log(result);
  } catch (e) { log({ error: e.message }); }
});

async function loadCities() {
  const cities = await api('/divar/cities?limit=2000');
  const sel = document.getElementById('citySelect');
  sel.innerHTML = '';
  cities.forEach((c) => {
    const o = document.createElement('option');
    o.value = c.slug;
    o.textContent = c.display;
    if (c.slug === 'tehran') o.selected = true;
    sel.appendChild(o);
  });
}

loadCities().catch(e => log({ error: e.message }));
loadBrands().catch(e => log({ error: e.message }));

SearchableSelect.enhanceCatalog({
  citySelect: { placeholder: 'Search city…', noResultsText: 'No cities found' },
  brandSelect: { placeholder: 'Search brand…', noResultsText: 'No brands found' },
  modelSelect: { placeholder: 'Search model…', noResultsText: 'No models found' },
  yearSelect: { placeholder: 'Search year…', noResultsText: 'No years found' },
  trimSelect: { placeholder: 'Search trim…', noResultsText: 'No trims found' },
});
