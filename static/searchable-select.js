(function (global) {
  'use strict';

  function escapeHtml(value) {
    if (value == null) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  const instances = new WeakMap();

  class SearchableSelect {
    constructor(select, opts = {}) {
      if (!select || select.dataset.searchableEnhanced === 'true') {
        return;
      }
      this.select = select;
      this.placeholder =
        opts.placeholder ||
        select.getAttribute('data-search-placeholder') ||
        'Search…';
      this.noResultsText = opts.noResultsText || 'No results';
      this.fetchOptions = opts.fetchOptions || null;
      this.minSearchChars = opts.minSearchChars ?? 2;
      this.searchDebounceMs = opts.searchDebounceMs ?? 250;
      this.loadingText = opts.loadingText || 'Searching…';
      this.typeToSearchText =
        opts.typeToSearchText || `Type at least ${this.minSearchChars} characters…`;
      this._fetchTimer = null;
      this._fetchSeq = 0;
      this._isLoading = false;
      this._hasSelection = false;
      this.activeIndex = -1;
      select.dataset.searchableEnhanced = 'true';
      select.classList.add('searchable-select-native');
      select.tabIndex = -1;
      this._build();
      this._observer = new MutationObserver(() => this._onOptionsChanged());
      this._observer.observe(select, { childList: true, subtree: true, attributes: true });
      select.addEventListener('change', () => this._syncInputFromSelect());
      this._onOptionsChanged();
      instances.set(select, this);
    }

    _build() {
      const wrap = document.createElement('div');
      wrap.className = 'searchable-select';
      this.select.parentNode.insertBefore(wrap, this.select);
      wrap.appendChild(this.select);

      this.input = document.createElement('input');
      this.input.type = 'search';
      this.input.className = 'searchable-select-input';
      this.input.placeholder = this.placeholder;
      this.input.autocomplete = 'off';
      this.input.setAttribute('role', 'combobox');
      this.input.setAttribute('aria-autocomplete', 'list');
      wrap.insertBefore(this.input, this.select);

      this.list = document.createElement('ul');
      this.list.className = 'searchable-select-list';
      this.list.hidden = true;
      this.list.setAttribute('role', 'listbox');
      wrap.appendChild(this.list);

      this.wrap = wrap;

      this.input.addEventListener('focus', () => this.open());
      this.input.addEventListener('input', () => {
        this.activeIndex = -1;
        if (this.fetchOptions) {
          this._hasSelection = false;
          if (this.select.value) {
            this.select.value = '';
          }
          this._scheduleFetch();
          return;
        }
        this.open();
        this.render();
      });
      this.input.addEventListener('keydown', (e) => this._onKeydown(e));
      this.list.addEventListener('mousedown', (e) => e.preventDefault());
      wrap.addEventListener('focusout', (e) => {
        if (!wrap.contains(e.relatedTarget)) this.close();
      });
    }

    _onKeydown(e) {
      const items = this._visibleItems();
      if (e.key === 'Escape') {
        this.close();
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (this.list.hidden) this.open();
        this.activeIndex = Math.min(this.activeIndex + 1, items.length - 1);
        this._highlightActive(items);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.activeIndex = Math.max(this.activeIndex - 1, 0);
        this._highlightActive(items);
        return;
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        if (this.list.hidden) {
          this.open();
          return;
        }
        const pick = items[this.activeIndex] || items[0];
        if (pick) this.pick(pick.dataset.value);
      }
    }

    _visibleItems() {
      return Array.from(this.list.querySelectorAll('.searchable-select-option'));
    }

    _highlightActive(items) {
      items.forEach((li, idx) => li.classList.toggle('is-active', idx === this.activeIndex));
      const active = items[this.activeIndex];
      if (active) active.scrollIntoView({ block: 'nearest' });
    }

    getOptions() {
      return Array.from(this.select.options).filter((o) => o.value);
    }

    setOptions(items, { keepValue = false } = {}) {
      this._observer.disconnect();
      try {
        const current = keepValue ? this.select.value : '';
        this.select.innerHTML = `<option value="">${escapeHtml(
          this.select.getAttribute('data-empty-label') || 'Select…'
        )}</option>`;
        items.forEach((item) => {
          const o = document.createElement('option');
          o.value = item.value;
          o.textContent = item.label;
          if (item.slug) o.dataset.slug = item.slug;
          this.select.appendChild(o);
        });
        if (keepValue && current) {
          this.select.value = current;
        }
      } finally {
        this._observer.observe(this.select, { childList: true, subtree: true, attributes: true });
      }
      this._onOptionsChanged({ preserveInput: true });
    }

    _scheduleFetch() {
      clearTimeout(this._fetchTimer);
      this._fetchTimer = setTimeout(() => this._runFetch(), this.searchDebounceMs);
      this.open();
      this.render();
    }

    async _runFetch() {
      const q = this.input.value.trim();
      if (q.length < this.minSearchChars) {
        this.setOptions([]);
        this.render();
        return;
      }
      const seq = ++this._fetchSeq;
      this._isLoading = true;
      this.render();
      try {
        const items = await this.fetchOptions(q);
        if (seq !== this._fetchSeq) return;
        this.setOptions(items, { keepValue: true });
      } catch (err) {
        if (seq !== this._fetchSeq) return;
        this.setOptions([]);
        this.list.innerHTML = `<li class="searchable-select-empty">${escapeHtml(
          err.message || 'Search failed'
        )}</li>`;
        return;
      } finally {
        if (seq === this._fetchSeq) {
          this._isLoading = false;
          this.render();
        }
      }
    }

    render() {
      if (this.fetchOptions) {
        const q = this.input.value.trim();
        if (q.length < this.minSearchChars) {
          this.list.innerHTML = `<li class="searchable-select-empty">${escapeHtml(
            this.typeToSearchText
          )}</li>`;
          return;
        }
        if (this._isLoading) {
          this.list.innerHTML = `<li class="searchable-select-empty">${escapeHtml(
            this.loadingText
          )}</li>`;
          return;
        }
      }
      const q = this.input.value.trim().toLowerCase();
      const options = this.getOptions().filter(
        (o) => !this.fetchOptions || !q || o.textContent.toLowerCase().includes(q)
      );
      if (!options.length) {
        this.list.innerHTML = `<li class="searchable-select-empty">${escapeHtml(this.noResultsText)}</li>`;
        return;
      }
      this.list.innerHTML = options
        .map(
          (o, idx) =>
            `<li class="searchable-select-option${o.selected ? ' is-selected' : ''}${
              idx === this.activeIndex ? ' is-active' : ''
            }" data-value="${escapeHtml(o.value)}" role="option">${escapeHtml(o.textContent)}</li>`
        )
        .join('');
      this.list.querySelectorAll('.searchable-select-option').forEach((li) => {
        li.addEventListener('click', () => this.pick(li.dataset.value));
      });
    }

    pick(value) {
      this.select.value = value;
      this._hasSelection = true;
      this.select.dispatchEvent(new Event('change', { bubbles: true }));
      this._syncInputFromSelect();
      this.close();
    }

    open() {
      if (this.input.disabled) return;
      this.list.hidden = false;
      this.render();
    }

    close() {
      this.list.hidden = true;
      this.activeIndex = -1;
      if (this.fetchOptions) {
        if (this._hasSelection) {
          this._syncInputFromSelect();
        }
        return;
      }
      this._syncInputFromSelect();
    }

    clearInput() {
      this.input.value = '';
      this.activeIndex = -1;
    }

    _syncInputFromSelect() {
      const sel = this.select.selectedOptions[0];
      if (sel && sel.value) {
        this.input.value = sel.textContent;
        this._hasSelection = true;
        return;
      }
      if (!this.fetchOptions) {
        this.input.value = '';
      }
    }

    _onOptionsChanged({ preserveInput = false } = {}) {
      const hasChoices = this.getOptions().length > 0;
      this.input.disabled = this.select.disabled || (!this.fetchOptions && !hasChoices);
      if (!this.list.hidden) this.render();
      if (this.fetchOptions && (preserveInput || (!this._hasSelection && this.input.value))) {
        return;
      }
      if (!this.fetchOptions || this._hasSelection) {
        this._syncInputFromSelect();
      }
    }
  }

  function enhance(select, opts) {
    const el = typeof select === 'string' ? document.getElementById(select) : select;
    if (!el) return null;
    if (instances.has(el)) return instances.get(el);
    const instance = new SearchableSelect(el, opts);
    return instances.get(el) || instance;
  }

  function enhanceCatalog(idsOrOpts) {
    const defaultIds = ['brandSelect', 'modelSelect', 'yearSelect', 'trimSelect'];
    if (Array.isArray(idsOrOpts)) {
      return idsOrOpts.map((id) => enhance(id));
    }
    if (idsOrOpts && typeof idsOrOpts === 'object') {
      const ids = Object.keys(idsOrOpts).length ? Object.keys(idsOrOpts) : defaultIds;
      return ids.map((id) => enhance(id, idsOrOpts[id] || {}));
    }
    return defaultIds.map((id) => enhance(id));
  }

  global.SearchableSelect = { enhance, enhanceCatalog, SearchableSelect };
})(window);
