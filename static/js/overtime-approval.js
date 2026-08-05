(() => {
  const minutesBetween = (start, end) => {
    if (!start || !end) return null;
    const [sh, sm] = start.split(':').map(Number);
    const [eh, em] = end.split(':').map(Number);
    let value = (eh * 60 + em) - (sh * 60 + sm);
    if (value <= 0) value += 24 * 60;
    return value;
  };
  document.querySelectorAll('[data-ot-final-form]').forEach((form) => {
    const start = form.dataset.plannedStart;
    const end = form.querySelector('[data-approved-end]');
    const minutes = form.querySelector('[data-approved-minutes]');
    const summary = form.querySelector('[data-approved-summary]');
    const dayNote = form.querySelector('[data-day-note]');
    const update = () => {
      const computed = minutesBetween(start, end?.value);
      if (computed !== null && minutes) minutes.value = computed;
      const value = Number(minutes?.value || 0);
      if (summary) summary.textContent = `${value} minutes`;
      if (dayNote) dayNote.textContent = end?.value && start && end.value <= start ? 'End time is treated as the following day.' : '';
    };
    end?.addEventListener('change', update);
    minutes?.addEventListener('input', () => { if (summary) summary.textContent = `${Number(minutes.value || 0)} minutes`; });
    update();
  });
})();
