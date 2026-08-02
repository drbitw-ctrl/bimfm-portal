(() => {
  'use strict';

  const cfg = window.BIMFM_I18N || {};
  if (cfg.locale !== 'zh_TW' || !cfg.catalog) return;

  const catalog = cfg.catalog;
  const translate = (key) => catalog[key] || key;
  const aliases = {
    IN_PROGRESS: 'In Progress',
    ON_HOLD: 'On Hold',
    COMPLETED: 'Completed',
    CANCELLED: 'Cancelled',
    NOT_STARTED: 'Not Started',
    PENDING: 'Pending',
    PENDING_PLAN: 'PENDING_PLAN',
    PLAN_APPROVED: 'PLAN_APPROVED',
    PENDING_FINAL: 'PENDING_FINAL',
    PENDING_FINAL_MISSING: 'PENDING_FINAL_MISSING',
    APPROVED: 'Approved',
    REJECTED: 'Rejected',
    REVIEWED: 'Reviewed',
    UNREVIEWED: 'Unreviewed',
    FINALIZED: 'Finalized',
    DRAFT: 'Draft',
    READY: 'Ready',
    LOCKED: 'Locked',
    OPEN: 'Open',
    COMPLETE: 'Complete',
    PRESENT: 'Present',
    ABSENT: 'Absent',
    MISSING_TIME_OUT: 'Missing Time Out',
    INVALID_RECORD: 'Invalid Record',
    ACCOUNT_DISABLED: 'Account Disabled',
    CURRENTLY_WORKING: 'Currently Working',
    NO_RECORD: 'No Record'
  };

  const countLabel = (amount, singular, plural) => {
    const numeric = Number(amount);
    const key = numeric === 1 ? singular : plural;
    return `${amount} ${translate(key)}`.trim();
  };

  const formatDynamic = (value) => {
    let match;

    match = value.match(/^(\d+)\s+entries?$/i);
    if (match) return countLabel(match[1], 'entry', 'entries');

    match = value.match(/^(\d+)\s+members?$/i);
    if (match) return countLabel(match[1], 'member', 'members');

    match = value.match(/^(\d+)\s+projects?$/i);
    if (match) return countLabel(match[1], 'project', 'projects');

    match = value.match(/^(\d+)\s+tasks?$/i);
    if (match) return countLabel(match[1], 'task', 'tasks');

    match = value.match(/^(\d+)\s+active tasks?$/i);
    if (match) return countLabel(match[1], 'active task', 'active tasks');

    match = value.match(/^(\d+)\s+completed tasks?$/i);
    if (match) return countLabel(match[1], 'completed task', 'completed tasks');

    match = value.match(/^(\d+)\s+affected members?$/i);
    if (match) return countLabel(match[1], 'affected member', 'affected members');

    match = value.match(/^(\d+)\s+correction\(s\)$/i);
    if (match) return `${match[1]} ${translate('correction(s)')}`;

    match = value.match(/^(\d+)\s+overdue$/i);
    if (match) return `${match[1]} ${translate('overdue')}`;

    match = value.match(/^(\d+)\s+without assignee$/i);
    if (match) return `${match[1]} ${translate('without assignee')}`;

    match = value.match(/^(\d+)\s+rated tasks?$/i);
    if (match) return countLabel(match[1], 'rated task', 'rated tasks');

    match = value.match(/^(\d+)\s+rated deliveries$/i);
    if (match) return countLabel(match[1], 'rated delivery', 'rated deliveries');

    match = value.match(/^(\d+)\s+measurable deliveries$/i);
    if (match) return countLabel(match[1], 'measurable delivery', 'measurable deliveries');

    match = value.match(/^(\d+)\s+early\/on-time$/i);
    if (match) return `${match[1]} ${translate('early/on-time')}`;

    match = value.match(/^(\d+)\s+day\(s\)$/i);
    if (match) return `${match[1]} ${translate('day(s)')}`;

    match = value.match(/^(\d+)\s+whole day\(s\)$/i);
    if (match) return `${match[1]} ${translate('whole day(s)')}`;

    match = value.match(/^(\d+)\s+days$/i);
    if (match) return `${match[1]} ${translate('days')}`;

    match = value.match(/^(\d+(?:\.\d+)?)\s+hours$/i);
    if (match) return `${match[1]} ${translate('hours')}`;

    match = value.match(/^(\d+)h\s+(\d{1,2})m$/i);
    if (match) return `${match[1]} ${translate('hours')} ${match[2]} ${translate('minutes')}`;

    match = value.match(/^(\d+)\s+min$/i);
    if (match) return `${match[1]} ${translate('minutes')}`;

    match = value.match(/^(\d+)\s+min\s+Previous claim$/i);
    if (match) return `${translate('Previous claim')}：${match[1]} ${translate('minutes')}`;

    match = value.match(/^Potential:\s*(\d+)\s+min$/i);
    if (match) return `${translate('Potential:')} ${match[1]} ${translate('minutes')}`;

    match = value.match(/^Approved\s+(\d+)\s+min$/i);
    if (match) return `${translate('Approved')}：${match[1]} ${translate('minutes')}`;

    match = value.match(/^Credited\s+(\d+)\s+min$/i);
    if (match) return `${translate('Credited')}：${match[1]} ${translate('minutes')}`;

    match = value.match(/^Comp credit\s+(\d+)\s+min$/i);
    if (match) return `${translate('Compensatory credit')}：${match[1]} ${translate('minutes')}`;

    match = value.match(/^([+-]?\d+(?:\.\d+)?)\s+days?\s+(early|late)$/i);
    if (match) return `${match[1]} ${translate('days')} ${translate(match[2].toLowerCase() === 'early' ? 'early' : 'late')}`;

    match = value.match(/^#(\d+)\s+(Quality|Output|Delivery)$/i);
    if (match) return `#${match[1]} ${translate(match[2])}`;

    match = value.match(/^Available compensatory credit:\s*(\d+)\s+whole day\(s\) available\s*·\s*(\d+)h\s+(\d{1,2})m accumulating$/i);
    if (match) return `${translate('Available compensatory credit:')} ${match[1]} ${translate('whole day(s)')} · ${match[2]} ${translate('hours')} ${match[3]} ${translate('minutes')} ${translate('accumulating')}`;

    match = value.match(/^(\d+)\s+entries?\s*·\s*(\d+)h\s+(\d{1,2})m\s*·\s*Review:\s*(.+)$/i);
    if (match) return `${match[1]} ${translate('entries')} · ${match[2]} ${translate('hours')} ${match[3]} ${translate('minutes')} · ${translate('Review:')} ${translate(aliases[match[4]] || match[4])}`;

    match = value.match(/^Total\s+(\d+)h\s+(\d{1,2})m$/i);
    if (match) return `${translate('Total')} ${match[1]} ${translate('hours')} ${match[2]} ${translate('minutes')}`;

    match = value.match(/^(\d+)\s+active members?\s*·\s*updated from the PostgreSQL task register$/i);
    if (match) return `${match[1]} ${translate('active member')} · ${translate('updated from the PostgreSQL task register')}`;

    match = value.match(/^Time in\s+(.+)$/i);
    if (match) return `${translate('Time in')} ${match[1]}`;

    match = value.match(/^Time out:\s*(.+)$/i);
    if (match) return `${translate('Time out')}：${match[1]}`;

    match = value.match(/^Deadline\s+(.+)$/i);
    if (match) return `${translate('Deadline')} ${match[1]}`;

    match = value.match(/^Review:\s*(.+)$/i);
    if (match) return `${translate('Review:')} ${translate(aliases[match[1]] || match[1])}`;

    match = value.match(/^\+(\d+)\s+more active tasks?$/i);
    if (match) return `＋${match[1]} ${translate('active tasks')}`;

    match = value.match(/^(\d+)\s+projects?\s*·\s*(\d+)\s+completed tasks?$/i);
    if (match) {
      return `${countLabel(match[1], 'project', 'projects')} · ${countLabel(match[2], 'completed task', 'completed tasks')}`;
    }

    match = value.match(/^([\d.]+)\s+calendar days\s*−\s*([\d.]+)\s+deduction day\(s\)$/i);
    if (match) return `${match[1]} ${translate('calendar days')} − ${match[2]} ${translate('day(s)')}`;

    return value;
  };

  const exact = (raw) => {
    const value = raw.trim();
    if (!value) return raw;

    const dynamic = formatDynamic(value);
    if (dynamic !== value) {
      const start = raw.match(/^\s*/)?.[0] || '';
      const end = raw.match(/\s*$/)?.[0] || '';
      return `${start}${dynamic}${end}`;
    }

    const alias = aliases[value] || value;
    const translated = catalog[value] || catalog[alias];
    if (!translated || translated === value) return raw;

    const start = raw.match(/^\s*/)?.[0] || '';
    const end = raw.match(/\s*$/)?.[0] || '';
    return `${start}${translated}${end}`;
  };

  // Only multi-word phrases are used for substring replacement. Single words
  // are translated only when they are the complete UI label, which protects
  // member names, project names, and task descriptions from accidental edits.
  const fragments = Object.entries(catalog)
    .filter(([key, value]) => (
      key !== value
      && key.length >= 4
      && key.length <= 90
      && /[\s:()\/&·—–-]/.test(key)
    ))
    .sort((a, b) => b[0].length - a[0].length);

  const mixed = (raw) => {
    const direct = exact(raw);
    if (direct !== raw) return direct;

    let out = raw;
    for (const [key, value] of fragments) {
      if (out.includes(key)) out = out.split(key).join(value);
    }
    for (const [code, label] of Object.entries(aliases)) {
      const replacement = catalog[code] || catalog[label];
      if (!replacement) continue;
      out = out.replace(new RegExp(`\\b${code}\\b`, 'g'), replacement);
    }

    const normalized = out.trim();
    const formatted = formatDynamic(normalized);
    if (formatted !== normalized) {
      const start = out.match(/^\s*/)?.[0] || '';
      const end = out.match(/\s*$/)?.[0] || '';
      return `${start}${formatted}${end}`;
    }
    return out;
  };

  const ignoredTags = new Set(['SCRIPT', 'STYLE', 'CODE', 'PRE', 'TEXTAREA']);
  const shouldSkip = (node) => {
    const parent = node.parentElement;
    return !parent
      || ignoredTags.has(parent.tagName)
      || Boolean(parent.closest('[data-i18n-skip], [translate="no"]'));
  };

  const translateElement = (root) => {
    if (root.nodeType === Node.ELEMENT_NODE && root.matches?.('[data-i18n-skip], [translate="no"]')) return;

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);

    for (const node of nodes) {
      if (shouldSkip(node)) continue;
      node.nodeValue = mixed(node.nodeValue || '');
    }

    const attrs = [
      'placeholder',
      'title',
      'aria-label',
      'data-empty-label',
      'data-record-singular',
      'data-record-plural'
    ];
    root.querySelectorAll?.('*:not([data-i18n-skip]):not([translate="no"])').forEach((el) => {
      if (el.closest('[data-i18n-skip], [translate="no"]')) return;
      for (const attr of attrs) {
        if (el.hasAttribute(attr)) el.setAttribute(attr, mixed(el.getAttribute(attr) || ''));
      }
    });
  };

  translateElement(document.documentElement);
  document.title = mixed(document.title);

  const observer = new MutationObserver((records) => {
    for (const record of records) {
      record.addedNodes.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE) {
          if (!shouldSkip(node)) node.nodeValue = mixed(node.nodeValue || '');
        } else if (node.nodeType === Node.ELEMENT_NODE) {
          translateElement(node);
        }
      });
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
