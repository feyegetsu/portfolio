/*
 * Общие анимации для демо-сайтов. Подключение: <script src="../_shared/motion.js" defer></script>
 *
 *   data-reveal            появление при прокрутке (значения: up по умолчанию, left, right, zoom)
 *   data-stagger           дети элемента появляются по очереди
 *   data-count="18000"     число «набегает» при появлении (data-suffix="+", data-decimals="1")
 *   data-parallax="0.15"   сдвиг при прокрутке, коэффициент скорости
 *   data-tilt              карточка слегка наклоняется за курсором
 *   img[data-fade]         картинка плавно проявляется после загрузки
 *   header[data-shrink]    получает класс .scrolled, когда страницу прокрутили
 *   кнопка «наверх»        добавляется сама, цвет берётся у первой кнопки .btn на странице
 */
(() => {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const css = document.createElement("style");
  css.textContent = `
    [data-reveal] { opacity: 0; transform: translateY(40px); transition: opacity .9s cubic-bezier(.2,.8,.2,1), transform .9s cubic-bezier(.2,.8,.2,1); transition-delay: var(--d, 0ms); }
    [data-reveal="left"] { transform: translateX(-50px); }
    [data-reveal="right"] { transform: translateX(50px); }
    [data-reveal="zoom"] { transform: scale(.92); }
    [data-reveal].in { opacity: 1; transform: none; }
    [data-stagger] > * { opacity: 0; transform: translateY(30px); transition: opacity .7s cubic-bezier(.2,.8,.2,1), transform .7s cubic-bezier(.2,.8,.2,1); }
    [data-stagger].in > * { opacity: 1; transform: none; }
    img[data-fade] { opacity: 0; transition: opacity .8s ease; }
    img[data-fade].loaded { opacity: 1; }
    [data-tilt] { transition: transform .4s cubic-bezier(.2,.8,.2,1); transform-style: preserve-3d; }
    body { overflow-x: clip; }
    @media (max-width: 760px) { [data-reveal="left"], [data-reveal="right"] { transform: translateY(40px); } }
    @media (prefers-reduced-motion: reduce) {
      [data-reveal], [data-stagger] > *, img[data-fade] { opacity: 1 !important; transform: none !important; transition: none !important; }
    }`;
  document.head.appendChild(css);

  function init() {
    // Появление
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (!e.isIntersecting) return;
      const el = e.target;
      if (el.hasAttribute("data-stagger")) {
        [...el.children].forEach((c, i) => { c.style.transitionDelay = `${i * 90}ms`; });
      }
      el.classList.add("in");
      if (el.dataset.count !== undefined) countUp(el);
      io.unobserve(el);
    }), { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    document.querySelectorAll("[data-reveal], [data-stagger], [data-count]").forEach((el) => io.observe(el));
    // Страховка: если наблюдатель не сработал (например, вкладка в фоне), показываем всё
    setTimeout(() => document.querySelectorAll("[data-reveal], [data-stagger]").forEach((el) => {
      if (el.getBoundingClientRect().top < innerHeight) el.classList.add("in");
    }), 1500);

    // Картинки
    document.querySelectorAll("img[data-fade]").forEach((img) => {
      if (img.complete && img.naturalWidth) img.classList.add("loaded");
      else {
        img.addEventListener("load", () => img.classList.add("loaded"), { once: true });
        img.addEventListener("error", () => img.classList.add("loaded"), { once: true });
      }
    });

    // Шапка
    const header = document.querySelector("[data-shrink]");
    // Параллакс
    const layers = reduce ? [] : [...document.querySelectorAll("[data-parallax]")];
    let ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        if (header) header.classList.toggle("scrolled", scrollY > 30);
        layers.forEach((el) => {
          const r = el.parentElement.getBoundingClientRect();
          if (r.bottom < 0 || r.top > innerHeight) return;
          el.style.transform = `translate3d(0, ${(-r.top * +el.dataset.parallax).toFixed(1)}px, 0) scale(1.15)`;
        });
        ticking = false;
      });
    };
    addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    toTopButton();

    // Наклон карточек за курсором
    if (!reduce && matchMedia("(hover: hover)").matches) {
      document.querySelectorAll("[data-tilt]").forEach((el) => {
        el.addEventListener("mousemove", (e) => {
          const r = el.getBoundingClientRect();
          const x = (e.clientX - r.left) / r.width - 0.5;
          const y = (e.clientY - r.top) / r.height - 0.5;
          el.style.transform = `perspective(900px) rotateY(${x * 6}deg) rotateX(${-y * 6}deg) translateY(-4px)`;
        });
        el.addEventListener("mouseleave", () => { el.style.transform = ""; });
      });
    }
  }

  // Кнопка «наверх» с кольцом прогресса прокрутки, в цветах сайта
  function toTopButton() {
    const sample = document.querySelector(".btn");
    const cs = sample ? getComputedStyle(sample) : null;
    const bg = cs && cs.backgroundColor !== "rgba(0, 0, 0, 0)" ? cs.backgroundColor : "#111";
    const fg = cs ? cs.color : "#fff";
    const style = document.createElement("style");
    style.textContent = `
      .pf-top { position: fixed; right: 18px; bottom: 18px; z-index: 45; width: 52px; height: 52px; border-radius: 50%; display: grid; place-items: center;
        background: ${bg}; color: ${fg}; box-shadow: 0 14px 28px -12px rgba(0, 0, 0, .55); opacity: 0; translate: 0 20px; scale: .8; pointer-events: none;
        transition: opacity .3s, translate .4s cubic-bezier(.2,.8,.2,1), scale .4s cubic-bezier(.2,.8,.2,1); -webkit-tap-highlight-color: transparent; }
      .pf-top.show { opacity: 1; translate: 0 0; scale: 1; pointer-events: auto; animation: pf-bob 3s ease-in-out infinite; }
      .pf-top:hover { scale: 1.08; animation-play-state: paused; }
      @keyframes pf-bob { 50% { translate: 0 -5px; } }
      .pf-top svg { position: absolute; inset: 0; width: 100%; height: 100%; rotate: -90deg; }
      .pf-top circle { fill: none; stroke: currentColor; stroke-width: 2.5; }
      .pf-top .track { opacity: .25; }
      .pf-top .bar { stroke-linecap: round; stroke-dasharray: 144.5; stroke-dashoffset: calc(144.5 - 144.5 * var(--p, 0)); }
      .pf-top i { font-style: normal; font-size: 20px; line-height: 1; font-weight: 700; }
      @media (prefers-reduced-motion: reduce) { .pf-top.show { animation: none; } }`;
    document.head.appendChild(style);
    const a = document.createElement("a");
    a.href = "#";
    a.className = "pf-top";
    a.setAttribute("aria-label", "Наверх");
    a.innerHTML = '<svg viewBox="0 0 52 52" aria-hidden="true"><circle class="track" cx="26" cy="26" r="23"/><circle class="bar" cx="26" cy="26" r="23"/></svg><i aria-hidden="true">↑</i>';
    a.addEventListener("click", (e) => { e.preventDefault(); scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" }); });
    document.body.appendChild(a);
    const update = () => {
      const max = document.documentElement.scrollHeight - innerHeight;
      a.style.setProperty("--p", max > 0 ? Math.min(1, scrollY / max).toFixed(3) : 0);
      a.classList.toggle("show", scrollY > 240);
    };
    addEventListener("scroll", update, { passive: true });
    update();
  }

  function countUp(el) {
    const to = parseFloat(el.dataset.count);
    const dec = +(el.dataset.decimals || 0);
    const suffix = el.dataset.suffix || "";
    const fmt = (n) => n.toLocaleString("ru-RU", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + suffix;
    if (reduce) { el.textContent = fmt(to); return; }
    // Резервируем итоговую ширину, чтобы соседние элементы не прыгали, пока число растёт
    el.textContent = fmt(to);
    if (getComputedStyle(el).display === "inline") el.style.display = "inline-block";
    el.style.minWidth = `${el.getBoundingClientRect().width}px`;
    el.style.fontVariantNumeric = "tabular-nums";
    const start = performance.now();
    const dur = 1600;
    const step = (t) => {
      const p = Math.min(1, (t - start) / dur);
      el.textContent = fmt(to * (1 - Math.pow(1 - p, 4)));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
    setTimeout(() => { el.textContent = fmt(to); }, dur + 200);
  }

  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", init) : init();
})();
