// Переключатель светлой и тёмной темы — общий для главной, политики и админки.
// Тему до первой отрисовки ставит короткий скрипт в <head> каждой страницы, чтобы не было вспышки.
// Здесь только кнопки: любая кнопка с атрибутом data-theme-toggle переключает тему и запоминает выбор.
(() => {
  const root = document.documentElement;
  const KEY = "theme";
  const LABEL = { light: "Включить тёмную тему", dark: "Включить светлую тему" };

  const current = () => (root.dataset.theme === "dark" ? "dark" : "light");

  const sync = () => {
    const t = current();
    document.querySelectorAll("[data-theme-toggle]").forEach((b) => {
      b.setAttribute("aria-label", LABEL[t]);
      b.title = LABEL[t];
    });
    // Цвет панели браузера на телефоне берём из CSS, у админки он свой
    const meta = document.querySelector('meta[name="theme-color"]');
    const color = getComputedStyle(root).getPropertyValue("--theme-color").trim();
    if (meta && color) meta.content = color;
  };

  const set = (t) => {
    const animate = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (animate) root.classList.add("theme-anim");
    root.dataset.theme = t;
    try { localStorage.setItem(KEY, t); } catch (e) { /* приватный режим: тема просто не запомнится */ }
    sync();
    if (animate) setTimeout(() => root.classList.remove("theme-anim"), 400);
  };

  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-theme-toggle]")) set(current() === "dark" ? "light" : "dark");
  });

  // Тему сменили в другой вкладке — подхватываем
  addEventListener("storage", (e) => {
    if (e.key === KEY && (e.newValue === "light" || e.newValue === "dark")) { root.dataset.theme = e.newValue; sync(); }
  });

  sync();
})();
