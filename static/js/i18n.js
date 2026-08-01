(() => {
  'use strict';
  const cfg = window.BIMFM_I18N || {};
  if (cfg.locale !== 'zh_TW' || !cfg.catalog) return;
  const catalog = cfg.catalog;
  const exact = (raw) => {
    const value = raw.trim();
    if (!value) return raw;
    const translated = catalog[value];
    if (!translated || translated === value) return raw;
    const start = raw.match(/^\s*/)?.[0] || '';
    const end = raw.match(/\s*$/)?.[0] || '';
    return `${start}${translated}${end}`;
  };
  const fragments = Object.entries(catalog)
    .filter(([key, value]) => key !== value && key.length >= 4 && key.length <= 45)
    .sort((a, b) => b[0].length - a[0].length);
  const mixed = (raw) => {
    const direct = exact(raw);
    if (direct !== raw) return direct;
    let out = raw;
    for (const [key, value] of fragments) {
      if (out.includes(key)) out = out.split(key).join(value);
    }
    return out;
  };
  const ignored = new Set(['SCRIPT', 'STYLE', 'CODE', 'PRE', 'TEXTAREA']);
  const translateElement = (root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      if (!node.parentElement || ignored.has(node.parentElement.tagName)) continue;
      node.nodeValue = mixed(node.nodeValue || '');
    }
    const attrs = ['placeholder', 'title', 'aria-label', 'data-empty-label'];
    root.querySelectorAll?.('*').forEach((el) => {
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
        if (node.nodeType === Node.TEXT_NODE && node.parentElement && !ignored.has(node.parentElement.tagName)) {
          node.nodeValue = mixed(node.nodeValue || '');
        } else if (node.nodeType === Node.ELEMENT_NODE) {
          translateElement(node);
        }
      });
    }
  });
  observer.observe(document.body, {childList: true, subtree: true});
})();
