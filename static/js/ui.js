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

  const currentPath = window.location.pathname;
  const navLinks = Array.from(document.querySelectorAll('.side-nav nav a'));
  let bestMatch = null;
  let bestLength = -1;

  navLinks.forEach((link) => {
    const linkPath = normalizePath(link.getAttribute('href') || '');
    const exactHome = linkPath === '/admin' || linkPath === '/attendance';
    const matches = exactHome ? currentPath === linkPath : currentPath.startsWith(linkPath);
    if (matches && linkPath.length > bestLength) {
      bestMatch = link;
      bestLength = linkPath.length;
    }
    link.addEventListener('click', () => {
      if (window.innerWidth <= 1000) closeNavigation();
    });
  });
  if (bestMatch) bestMatch.classList.add('active');

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
    const resultCount = toolbar.querySelector('[data-result-count]');

    function applyFilter() {
      const query = (search && search.value || '').trim().toLocaleLowerCase();
      const onlyUnmapped = Boolean(unmappedOnly && unmappedOnly.checked);
      let visible = 0;

      rows.forEach((row) => {
        const text = row.textContent.toLocaleLowerCase();
        const matchesQuery = !query || text.includes(query);
        const matchesMapping = !onlyUnmapped || row.dataset.mappingStatus === 'unmapped';
        const show = matchesQuery && matchesMapping;
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
    applyFilter();
  }

  document.querySelectorAll('[data-table-toolbar]').forEach(prepareTableFilter);

  document.querySelectorAll('form[data-submit-lock]').forEach((form) => {
    form.addEventListener('submit', () => {
      const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
      if (!submitButton) return;
      submitButton.disabled = true;
      submitButton.setAttribute('aria-busy', 'true');
    });
  });
}());
