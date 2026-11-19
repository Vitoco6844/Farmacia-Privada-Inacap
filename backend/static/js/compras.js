document.querySelectorAll('[data-purchase-formset]').forEach(container => {
  const total = document.getElementById(`id_${container.dataset.purchaseFormset}-TOTAL_FORMS`);
  const button = container.querySelector('[data-add-row]');
  button.addEventListener('click', () => {
    const index = Number(total.value);
    const status = container.querySelector('[data-row-status]');
    if (index >= Number(container.dataset.max)) {
      status.textContent = 'Alcanzaste el máximo de filas de este formulario.';
      return;
    }
    const fragment = container.querySelector('template').content.cloneNode(true);
    fragment.querySelectorAll('*').forEach(element => {
      ['name', 'id', 'for', 'aria-describedby'].forEach(attribute => {
        if (element.hasAttribute(attribute)) {
          element.setAttribute(attribute, element.getAttribute(attribute).replaceAll('__prefix__', String(index)));
        }
      });
    });
    container.querySelector('[data-rows]').appendChild(fragment);
    total.value = index + 1;
    status.textContent = `Fila ${index + 1} agregada.`;
    container.querySelector('[data-rows]').lastElementChild.querySelector('select, input')?.focus();
  });
});
