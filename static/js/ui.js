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

  function prepareSortableTable(table) {
    const body = table.tBodies[0];
    if (!body) return;

    const headers = Array.from(table.querySelectorAll('thead th'));
    const originalOrder = new Map(
      Array.from(body.rows).map((row, index) => [row, index])
    );
    const activeFirst = table.hasAttribute('data-sortable-task-table');
    let activeColumn = -1;
    let direction = 'asc';

    function taskGroup(row) {
      if (!activeFirst) return 0;
      return row.dataset.taskState === 'closed' ? 1 : 0;
    }

    function rawCellValue(row, columnIndex) {
      const cell = row.cells[columnIndex];
      if (!cell) return '';
      if (cell.dataset.sortValue !== undefined) return cell.dataset.sortValue;
      const control = cell.querySelector('select, input, textarea');
      if (control) {
        if (control.tagName === 'SELECT') {
          const selected = control.options[control.selectedIndex];
          return control.value || selected?.textContent || '';
        }
        return control.value || '';
      }
      return cell.textContent.trim();
    }

    function comparable(value, type) {
      const text = String(value ?? '').trim();
      if (type === 'number') {
        const parsed = Number.parseFloat(text.replace(/[^0-9.+-]/g, ''));
        return Number.isFinite(parsed) ? parsed : Number.NEGATIVE_INFINITY;
      }
      if (type === 'date') {
        if (!text || text === '—') return Number.POSITIVE_INFINITY;
        const parsed = Date.parse(text);
        return Number.isFinite(parsed) ? parsed : Number.POSITIVE_INFINITY;
      }
      if (type === 'priority') {
        const rank = { URGENT: 4, CRITICAL: 4, HIGH: 3, NORMAL: 2, MEDIUM: 2, LOW: 1 };
        return rank[text.toUpperCase()] || 0;
      }
      if (type === 'status') {
        const rank = {
          IN_PROGRESS: 1,
          'IN PROGRESS': 1,
          NOT_STARTED: 2,
          'NOT STARTED': 2,
          FOR_REVIEW: 3,
          'COMPLETED — FOR REVIEW': 3,
          ON_HOLD: 4,
          'ON HOLD': 4,
          UNASSIGNED: 5,
          COMPLETED: 6,
          CANCELLED: 7
        };
        return rank[text.toUpperCase()] ?? 50;
      }
      return text.toLocaleLowerCase();
    }

    function compareValues(left, right, type) {
      if (typeof left === 'number' && typeof right === 'number') return left - right;
      return String(left).localeCompare(String(right), undefined, {
        numeric: true,
        sensitivity: 'base'
      });
    }

    function applySort(columnIndex, nextDirection, updateIndicators) {
      const header = headers[columnIndex];
      if (!header) return;
      const type = header.dataset.sortType || 'text';
      const multiplier = nextDirection === 'desc' ? -1 : 1;
      const rows = Array.from(body.rows);

      rows.sort((leftRow, rightRow) => {
        const groupDifference = taskGroup(leftRow) - taskGroup(rightRow);
        if (groupDifference !== 0) return groupDifference;
        const left = comparable(rawCellValue(leftRow, columnIndex), type);
        const right = comparable(rawCellValue(rightRow, columnIndex), type);
        const compared = compareValues(left, right, type);
        if (compared !== 0) return compared * multiplier;
        return (originalOrder.get(leftRow) || 0) - (originalOrder.get(rightRow) || 0);
      });

      rows.forEach((row) => body.appendChild(row));
      activeColumn = columnIndex;
      direction = nextDirection;

      if (updateIndicators) {
        headers.forEach((cell, index) => {
          cell.setAttribute('aria-sort', index === columnIndex
            ? (nextDirection === 'asc' ? 'ascending' : 'descending')
            : 'none');
          const indicator = cell.querySelector('[data-sort-indicator]');
          if (indicator) indicator.textContent = index === columnIndex
            ? (nextDirection === 'asc' ? '▲' : '▼')
            : '↕';
        });
      }
    }

    headers.forEach((header, index) => {
      if (!header.dataset.sortType || header.dataset.sortType === 'none') return;
      const label = header.textContent.trim();
      header.textContent = '';
      header.setAttribute('aria-sort', 'none');
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'table-sort-button';
      button.innerHTML = `<span>${label}</span><em data-sort-indicator aria-hidden="true">↕</em>`;
      button.addEventListener('click', () => {
        const nextDirection = activeColumn === index && direction === 'asc' ? 'desc' : 'asc';
        applySort(index, nextDirection, true);
      });
      header.appendChild(button);
    });

    table.addEventListener('bimfm:row-updated', () => {
      if (activeColumn >= 0) applySort(activeColumn, direction, false);
    });
  }

  document.querySelectorAll('table[data-sortable-table], table[data-sortable-task-table]').forEach(prepareSortableTable);

  function prepareResponsiveTable(table) {
    const headings = Array.from(table.querySelectorAll('thead th')).map((cell) => {
      const sortLabel = cell.querySelector('.table-sort-button span');
      return (sortLabel ? sortLabel.textContent : cell.textContent).trim();
    });
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
