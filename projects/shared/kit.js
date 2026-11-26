/* Общие помощники для демо-сайтов: то, что раньше каждая страница писала заново.
 * Подключение: <script src="../shared/kit.js" defer></script> (после api.js).
 *
 *   PF.$("id")                       элемент по id
 *   PF.rub(1490)                     «1 490 ₽»
 *   PF.plural(n, "день", "дня", "дней")
 *   PF.toast("Готово")               уведомление внизу экрана (стиль .kit-toast в kit.css)
 *   PF.lead(form, { kind, ... })     отправляет форму заявки в API и показывает результат
 *   PF.sheet(el, { label, keep })    окно или шторка как диалог: .open(), .close() — фокус, Tab, возврат фокуса
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

  // Окно или шторка с семантикой диалога (WCAG 2.4.3, 2.1.2). Пока окно открыто, остальная страница inert:
  // Tab не уходит под окно, скринридер не читает фон. Закрытое окно тоже inert — с клавиатуры в него не попасть.
  // Фокус при открытии — на первый элемент окна, при закрытии — обратно на кнопку, которая его открыла.
  // keep — элементы, которые остаются живыми (подложка, по клику на которую окно закрывается).
  const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
  const sheet = (el, { label, keep = [] } = {}) => {
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-modal", "true");
    if (label) el.setAttribute("aria-label", label);
    if (!el.hasAttribute("tabindex")) el.tabIndex = -1;
    let opener = null, isOpen = false, frozen = [];
    const close = () => {
      if (!isOpen) return;
      isOpen = false;
      frozen.forEach((n) => { n.inert = false; });
      frozen = [];
      el.inert = true;
      el.setAttribute("aria-hidden", "true");
      if (el.contains(document.activeElement)) document.activeElement.blur();  // фокус не остаётся в закрытом окне
      if (opener && opener.isConnected) opener.focus({ preventScroll: true });
    };
    const open = (from = document.activeElement) => {
      opener = from;
      el.inert = false;
      el.removeAttribute("aria-hidden");
      if (!isOpen) {
        isOpen = true;
        // Всё вне окна по пути от него до body — inert, кроме keep и уже неактивных элементов
        for (let n = el; n.parentElement && n !== document.body; n = n.parentElement) {
          for (const s of n.parentElement.children) {
            if (s === n || s.inert || keep.includes(s) || s.tagName === "SCRIPT" || s.tagName === "STYLE") continue;
            s.inert = true;
            frozen.push(s);
          }
        }
      }
      requestAnimationFrame(() => (el.querySelector(FOCUSABLE) || el).focus({ preventScroll: true }));
    };
    // Tab по кругу внутри окна (и разрешённых keep), а не в адресную строку браузера
    document.addEventListener("keydown", (e) => {
      if (!isOpen || e.key !== "Tab") return;
      const items = [el, ...keep].flatMap((root) => [...(root.matches(FOCUSABLE) ? [root] : []), ...root.querySelectorAll(FOCUSABLE)])
        .filter((n) => !n.inert && !n.closest("[inert]") && n.offsetParent !== null)
        .sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));  // порядок как у Tab
      if (!items.length) return;
      const i = items.indexOf(document.activeElement);
      const next = e.shiftKey ? (i <= 0 ? items.length - 1 : i - 1) : (i === -1 || i === items.length - 1 ? 0 : i + 1);
      if ((e.shiftKey && i <= 0) || (!e.shiftKey && (i === -1 || i === items.length - 1))) {
        e.preventDefault();
        items[next].focus();
      }
    });
    el.inert = true;
    el.setAttribute("aria-hidden", "true");
    return { open, close, get isOpen() { return isOpen; } };
  };

  window.PF = { $, rub, plural, toast, lead, sheet };
})();
