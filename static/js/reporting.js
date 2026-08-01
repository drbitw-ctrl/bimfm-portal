(function () {
  'use strict';

  const source = document.getElementById('reportChartData');
  if (!source) return;

  let rows = [];
  try {
    rows = JSON.parse(source.textContent || '[]');
  } catch (_error) {
    rows = [];
  }

  const chartDefinitions = {
    delivered: { key: 'delivered', suffix: '', empty: 0, type: 'bar' },
    quality: { key: 'quality', suffix: '%', empty: null, type: 'line', min: 0, max: 100 },
    on_time: { key: 'on_time', suffix: '%', empty: null, type: 'line', min: 0, max: 100 },
    hours: { key: 'hours', suffix: 'h', empty: 0, type: 'bar' }
  };

  function number(value) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function textSvg(tag, attributes, text) {
    const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attributes || {}).forEach(([key, value]) => element.setAttribute(key, String(value)));
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function valueLabel(value, suffix) {
    if (value === null) return 'No data';
    const rounded = Math.abs(value - Math.round(value)) < 0.01 ? String(Math.round(value)) : value.toFixed(1);
    return `${rounded}${suffix}`;
  }

  function drawChart(container, definition) {
    const width = 820;
    const height = 255;
    const margins = { left: 48, right: 18, top: 20, bottom: 48 };
    const innerWidth = width - margins.left - margins.right;
    const innerHeight = height - margins.top - margins.bottom;
    const values = rows.map((row) => number(row[definition.key]));
    const valid = values.filter((value) => value !== null);

    container.innerHTML = '';
    if (!rows.length || !valid.length) {
      const empty = document.createElement('div');
      empty.className = 'report-chart-empty';
      empty.textContent = 'No measurable data for this period.';
      container.appendChild(empty);
      return;
    }

    const dataMaximum = Math.max(...valid, 0);
    const dataMinimum = Math.min(...valid, 0);
    const maximum = definition.max !== undefined ? definition.max : Math.max(1, dataMaximum * 1.12);
    const minimum = definition.min !== undefined ? definition.min : Math.min(0, dataMinimum);
    const span = Math.max(1, maximum - minimum);
    const xStep = rows.length > 1 ? innerWidth / (rows.length - 1) : innerWidth;
    const xFor = (index) => margins.left + (rows.length > 1 ? index * xStep : innerWidth / 2);
    const yFor = (value) => margins.top + innerHeight - ((value - minimum) / span) * innerHeight;

    const svg = textSvg('svg', {
      viewBox: `0 0 ${width} ${height}`,
      role: 'img',
      'aria-label': container.getAttribute('aria-label') || 'Report chart',
      preserveAspectRatio: 'xMidYMid meet'
    });
    svg.classList.add('report-chart-svg');

    for (let index = 0; index <= 4; index += 1) {
      const ratio = index / 4;
      const y = margins.top + innerHeight * ratio;
      const grid = textSvg('line', { x1: margins.left, y1: y, x2: width - margins.right, y2: y, class: 'chart-grid-line' });
      svg.appendChild(grid);
      const tickValue = maximum - span * ratio;
      svg.appendChild(textSvg('text', { x: margins.left - 8, y: y + 4, class: 'chart-axis-label', 'text-anchor': 'end' }, valueLabel(tickValue, definition.suffix)));
    }

    const labelInterval = Math.max(1, Math.ceil(rows.length / 8));
    rows.forEach((row, index) => {
      if (index % labelInterval !== 0 && index !== rows.length - 1) return;
      svg.appendChild(textSvg('text', { x: xFor(index), y: height - 15, class: 'chart-axis-label', 'text-anchor': 'middle' }, String(row.label || '')));
    });

    if (definition.type === 'bar') {
      const barSlot = innerWidth / Math.max(1, rows.length);
      const barWidth = Math.max(4, Math.min(28, barSlot * 0.62));
      rows.forEach((row, index) => {
        const value = values[index] === null ? 0 : values[index];
        const y = yFor(value);
        const baseline = yFor(Math.max(0, minimum));
        const rect = textSvg('rect', {
          x: xFor(index) - barWidth / 2,
          y: Math.min(y, baseline),
          width: barWidth,
          height: Math.max(1, Math.abs(baseline - y)),
          rx: 4,
          class: 'chart-bar'
        });
        const title = textSvg('title', {}, `${row.label}: ${valueLabel(value, definition.suffix)}`);
        rect.appendChild(title);
        svg.appendChild(rect);
      });
    } else {
      const segments = [];
      let current = [];
      values.forEach((value, index) => {
        if (value === null) {
          if (current.length) segments.push(current);
          current = [];
          return;
        }
        current.push([xFor(index), yFor(value), index, value]);
      });
      if (current.length) segments.push(current);

      segments.forEach((segment) => {
        const pathData = segment.map((point, index) => `${index ? 'L' : 'M'} ${point[0].toFixed(2)} ${point[1].toFixed(2)}`).join(' ');
        svg.appendChild(textSvg('path', { d: pathData, class: 'chart-line', fill: 'none' }));
      });
      segments.flat().forEach(([x, y, index, value]) => {
        const circle = textSvg('circle', { cx: x, cy: y, r: 4, class: 'chart-point' });
        circle.appendChild(textSvg('title', {}, `${rows[index].label}: ${valueLabel(value, definition.suffix)}`));
        svg.appendChild(circle);
      });
    }

    container.appendChild(svg);
  }

  document.querySelectorAll('[data-report-chart]').forEach((container) => {
    const definition = chartDefinitions[container.dataset.reportChart];
    if (definition) drawChart(container, definition);
  });

  const periodForm = document.querySelector('[data-report-period-form]');
  const monthInput = periodForm?.querySelector('input[type="month"]');
  if (periodForm && monthInput) {
    monthInput.addEventListener('change', () => {
      const activeButton = periodForm.querySelector('.report-period-buttons button.active');
      const period = activeButton?.value || 'month';
      const url = new URL(periodForm.action, window.location.origin);
      url.searchParams.set('period', period);
      url.searchParams.set('month', monthInput.value);
      window.location.assign(url.toString());
    });
  }
}());
