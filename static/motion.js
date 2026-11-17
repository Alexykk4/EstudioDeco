// Animaciones que necesitan saber cuándo cambia un dato. No toca la lógica de app.js: solo observa el DOM.
(() => {
  const total = document.getElementById('orderTotal');
  if (!total) return;
  let previo = total.textContent;
  new MutationObserver(() => {
    if (total.textContent === previo) return;
    previo = total.textContent;
    total.classList.remove('bump');
    void total.offsetWidth; // reinicia la animación aunque se repita seguido
    total.classList.add('bump');
  }).observe(total, { childList: true, characterData: true, subtree: true });
})();
