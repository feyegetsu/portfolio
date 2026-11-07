/* Общие помощники для демо-сайтов: то, что раньше каждая страница писала заново.
 * Подключение: <script src="../shared/kit.js" defer></script> (после api.js).
 *
 *   PF.$("id")                       элемент по id
 *   PF.rub(1490)                     «1 490 ₽»
 *   PF.plural(n, "день", "дня", "дней")
 *   PF.toast("Готово")               уведомление внизу экрана (стиль .kit-toast в kit.css)
 *   PF.lead(form, { kind, ... })     отправляет форму заявки в API и показывает результат
 */
(() => {
  const $ = (id) => document.getElementById(id);
  const rub = (n) => `${Number(n).toLocaleString("ru-RU")} ₽`;
  const plural = (n, one, few, many) => {
    const a = Math.abs(n) % 10, b = Math.abs(n) % 100;
    return a === 1 && b !== 11 ? one : a >= 2 && a <= 4 && (b < 10 || b > 20) ? few : many;
  };

  let toastEl, toastTimer;
  const toast = (text, ms = 2800) => {
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.className = "kit-toast";
      toastEl.setAttribute("role", "status");
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = text;
    void toastEl.offsetWidth;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("show"), ms);
  };

  // Заявка из обычной формы: поля name, phone, email, message и всё остальное — в data.
  // Поле website — ловушка для ботов, человек его не видит.
  const lead = (form, { site, kind = "consult", done = "Заявка отправлена, скоро свяжемся" } = {}) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const api = window.PortfolioAPI;
      const fd = Object.fromEntries(new FormData(form));
      const { name = "", phone = "", email = "", message = "", website = "", ...data } = fd;
      try {
        await api.submit(form, () => api.createLead(site || form.dataset.site, { kind, name, phone, email, message, website, data }));
        form.reset();
        toast(done);
      } catch {}
    });
  };

  window.PF = { $, rub, plural, toast, lead };
})();
