(function () {
  'use strict';

  const root = document.documentElement;
  const body = document.body;

  function setTheme(theme) {
    const nextTheme = theme === 'dark' ? 'dark' : 'light';
    root.dataset.theme = nextTheme;
    localStorage.setItem('bimfm-theme', nextTheme);
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.setAttribute('aria-pressed', String(nextTheme === 'dark'));
    });
  }

  document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      setTheme(root.dataset.theme === 'dark' ? 'light' : 'dark');
    });
  });
  setTheme(root.dataset.theme || 'light');

  const openNavigation = () => body.classList.add('nav-open');
  const closeNavigation = () => body.classList.remove('nav-open');

  document.querySelectorAll('[data-nav-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      body.classList.contains('nav-open') ? closeNavigation() : openNavigation();
    });
  });
  document.querySelectorAll('[data-nav-close]').forEach((element) => {
    element.addEventListener('click', closeNavigation);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeNavigation();
  });

  function normalizePath(href) {
    try {
      return new URL(href, window.location.origin).pathname;
    } catch (_error) {
      return href;
    }
  }

  const currentUrl = new URL(window.location.href);
  const currentPath = currentUrl.pathname;
  const navLinks = Array.from(document.querySelectorAll('.side-nav nav a'));
  let bestMatch = null;
  let bestLength = -1;

  navLinks.forEach((link) => {
    const linkPath = link.dataset.navPath || normalizePath(link.getAttribute('href') || '');
    const exact = link.dataset.navExact !== 'false';
    const requiredQuery = link.dataset.navQuery || '';
    const pathMatches = exact
      ? currentPath === linkPath
      : (currentPath === linkPath || currentPath.startsWith(`${linkPath}/`));
    const queryMatches = !requiredQuery || currentUrl.searchParams.toString() === requiredQuery;
    const matches = pathMatches && queryMatches;

    if (matches && linkPath.length > bestLength) {
      bestMatch = link;
      bestLength = linkPath.length;
    }

    link.addEventListener('click', () => {
      if (window.innerWidth <= 1050) closeNavigation();
    });
  });

  if (!document.querySelector('.side-nav nav a.active') && bestMatch) {
    bestMatch.classList.add('active');
    bestMatch.setAttribute('aria-current', 'page');
  }

  const liveDate = document.querySelector('[data-live-date]');
  if (liveDate) {
    const locale = root.lang === 'zh-Hant-TW' ? 'zh-TW' : 'en-PH';
    liveDate.textContent = new Intl.DateTimeFormat(locale, {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    }).format(new Date());
  }

  function prepareTableFilter(toolbar) {
    const targetSelector = toolbar.dataset.tableTarget;
    if (!targetSelector) return;

    const table = document.querySelector(targetSelector);
    if (!table) return;

    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const search = toolbar.querySelector('[data-table-search]');
    const unmappedOnly = toolbar.querySelector('[data-unmapped-only]');
    const filters = Array.from(toolbar.querySelectorAll('[data-table-filter]'));
    const reset = toolbar.querySelector('[data-table-filter-reset]');
    const resultCount = toolbar.querySelector('[data-result-count]');

    function searchableRowText(row) {
      return Array.from(row.querySelectorAll('td')).map((cell) => {
        const control = cell.querySelector('input, select, textarea');
        if (!control) return cell.textContent;
        if (control.tagName === 'SELECT') {
          const option = control.options[control.selectedIndex];
          return option ? option.textContent : '';
        }
        return control.value || '';
      }).join(' ').toLocaleLowerCase();
    }

    function applyFilter() {
      const query = (search && search.value || '').trim().toLocaleLowerCase();
      const onlyUnmapped = Boolean(unmappedOnly && unmappedOnly.checked);
      let visible = 0;

      rows.forEach((row) => {
        const text = searchableRowText(row);
        const matchesQuery = !query || text.includes(query);
        const matchesMapping = !onlyUnmapped || row.dataset.mappingStatus === 'unmapped';
        const matchesFilters = filters.every((control) => {
          const selected = (control.value || '').trim().toLocaleLowerCase();
          if (!selected) return true;
          const key = control.dataset.filterKey || '';
          const rowValue = (row.getAttribute(`data-filter-${key}`) || '').toLocaleLowerCase();
          if (control.dataset.filterMode === 'token') {
            return rowValue.includes(`|${selected}|`);
          }
          return rowValue === selected;
        });
        const show = matchesQuery && matchesMapping && matchesFilters;
        row.hidden = !show;
        if (show) visible += 1;
      });

      if (resultCount) {
        const label = visible === 1
          ? (toolbar.dataset.recordSingular || 'record')
          : (toolbar.dataset.recordPlural || 'records');
        resultCount.textContent = `${visible} ${label}`;
      }
    }

    if (search) search.addEventListener('input', applyFilter);
    if (unmappedOnly) unmappedOnly.addEventListener('change', applyFilter);
    filters.forEach((control) => control.addEventListener('change', applyFilter));
    if (reset) {
      reset.addEventListener('click', () => {
        if (search) search.value = '';
        if (unmappedOnly) unmappedOnly.checked = false;
        filters.forEach((control) => { control.value = ''; });
        applyFilter();
      });
    }
    applyFilter();
  }

  document.querySelectorAll('[data-table-toolbar]').forEach(prepareTableFilter);

  function prepareResponsiveTable(table) {
    const headings = Array.from(table.querySelectorAll('thead th')).map((cell) => cell.textContent.trim());
    table.querySelectorAll('tbody tr').forEach((row) => {
      Array.from(row.children).forEach((cell, index) => {
        if (!cell.dataset.label && headings[index]) cell.dataset.label = headings[index];
      });
    });
  }

  document.querySelectorAll('table[data-card-table]').forEach(prepareResponsiveTable);

  document.querySelectorAll('form[data-submit-lock]').forEach((form) => {
    form.addEventListener('submit', () => {
      const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
      if (!submitButton) return;
      submitButton.disabled = true;
      submitButton.setAttribute('aria-busy', 'true');
    });
  });
}());
