/*
 * Фотоальбомы для демо-сайтов: альбом открывается во весь экран, листается стрелками, свайпом и с клавиатуры.
 *
 *   window.PF_ALBUMS = { hall: { title: "Наш зал", photos: [["unsplash-id", "подпись"], ...] } }
 *   <button data-album="hall">…</button>          открыть альбом
 *   <button data-album="hall" data-index="2">…</button>  открыть на нужном фото
 *   PFGallery.open("hall", 0)                     то же из кода
 *   PFGallery.count("hall")                       сколько фото в альбоме
 */
(() => {
  const big = (id) => `https://images.unsplash.com/photo-${id}?auto=format&fit=max&w=1600&q=80`;
  const thumb = (id) => `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=160&h=120&q=60`;
  const albums = () => window.PF_ALBUMS || {};

  const css = document.createElement("style");
  css.textContent = `
    .pf-gal { color-scheme: dark; position: fixed; inset: 0; margin: 0; width: 100%; height: 100%; max-width: none; max-height: none; border: 0; padding: 0;
      background: rgba(8, 9, 12, .97); color: #f2f3f5; font: 15px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; overflow: hidden; }
    .pf-gal[open] { display: grid; grid-template-rows: auto minmax(0, 1fr) auto auto; animation: pf-gal-in .3s ease; }
    .pf-gal::backdrop { background: transparent; }
    @keyframes pf-gal-in { from { opacity: 0; } }
    .pf-gal__top { display: flex; align-items: center; gap: 14px; padding: 14px 18px; }
    .pf-gal__title { font-weight: 700; font-size: 17px; margin: 0; }
    .pf-gal__count { color: #9aa0ab; font-variant-numeric: tabular-nums; }
    .pf-gal__x { margin: 0 0 0 auto; width: 42px; height: 42px; border-radius: 50%; border: 0; padding: 0; background: rgba(255, 255, 255, .1); color: #fff; font-size: 18px; cursor: pointer; }
    .pf-gal__x:hover { background: rgba(255, 255, 255, .2); }
    .pf-gal__stage { position: relative; min-height: 0; overflow: hidden; display: grid; grid-template: minmax(0, 1fr) / minmax(0, 1fr); place-items: center; padding: 0 70px; touch-action: pan-y; user-select: none; }
    .pf-gal__img { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 6px; transition: opacity .25s, transform .25s; box-shadow: 0 30px 80px -30px #000; }
    .pf-gal__img.out { opacity: 0; transform: scale(.98); }
    .pf-gal__nav { position: absolute; top: 50%; translate: 0 -50%; width: 52px; height: 52px; border-radius: 50%; border: 0; padding: 0; margin: 0;
      background: rgba(255, 255, 255, .12); color: #fff; font-size: 22px; cursor: pointer; transition: background .2s; }
    .pf-gal__nav:hover { background: rgba(255, 255, 255, .25); }
    .pf-gal__prev { left: 12px; } .pf-gal__next { right: 12px; }
    .pf-gal__cap { text-align: center; color: #c9ccd2; padding: 12px 18px 0; min-height: 1.4em; margin: 0; }
    .pf-gal__thumbs { display: flex; gap: 8px; overflow-x: auto; padding: 14px 18px 18px; justify-content: safe center; scrollbar-width: thin; }
    .pf-gal__thumbs button { flex: 0 0 auto; width: 76px; height: 56px; padding: 0; margin: 0; border: 2px solid transparent; border-radius: 8px; overflow: hidden; background: #222; opacity: .5; cursor: pointer; transition: opacity .2s, border-color .2s; }
    .pf-gal__thumbs button:hover { opacity: .85; }
    .pf-gal__thumbs button[aria-current="true"] { opacity: 1; border-color: #fff; }
    .pf-gal__thumbs img { width: 100%; height: 100%; object-fit: cover; display: block; }
    @media (max-width: 640px) {
      .pf-gal__stage { padding: 0 8px; }
      .pf-gal__nav { width: 42px; height: 42px; font-size: 18px; background: rgba(0, 0, 0, .45); }
      .pf-gal__prev { left: 14px; } .pf-gal__next { right: 14px; }
      .pf-gal__thumbs button { width: 60px; height: 46px; }
    }
    @media (prefers-reduced-motion: reduce) { .pf-gal[open], .pf-gal__img { animation: none; transition: none; } }`;
  document.head.appendChild(css);

  let dlg, album, index = 0;

  function build() {
    dlg = document.createElement("dialog");
    dlg.className = "pf-gal";
    dlg.setAttribute("aria-label", "Фотоальбом");
    dlg.innerHTML = `
      <div class="pf-gal__top"><p class="pf-gal__title"></p><span class="pf-gal__count"></span><button class="pf-gal__x" aria-label="Закрыть">✕</button></div>
      <div class="pf-gal__stage">
        <img class="pf-gal__img" alt="">
        <button class="pf-gal__nav pf-gal__prev" aria-label="Предыдущее фото">‹</button>
        <button class="pf-gal__nav pf-gal__next" aria-label="Следующее фото">›</button>
      </div>
      <p class="pf-gal__cap"></p>
      <div class="pf-gal__thumbs" role="group" aria-label="Все фото альбома"></div>`;
    document.body.appendChild(dlg);
    dlg.querySelector(".pf-gal__x").onclick = close;
    dlg.querySelector(".pf-gal__prev").onclick = () => show(index - 1);
    dlg.querySelector(".pf-gal__next").onclick = () => show(index + 1);
    dlg.querySelector(".pf-gal__thumbs").onclick = (e) => { const b = e.target.closest("[data-i]"); if (b) show(+b.dataset.i); };
    dlg.addEventListener("cancel", (e) => { e.preventDefault(); close(); });
    dlg.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") show(index - 1);
      if (e.key === "ArrowRight") show(index + 1);
    });
    dlg.addEventListener("close", () => { document.documentElement.style.overflow = ""; });
    // Свайп по фото
    const stage = dlg.querySelector(".pf-gal__stage");
    let x0 = null;
    stage.addEventListener("pointerdown", (e) => { if (!e.target.closest("button")) x0 = e.clientX; });
    stage.addEventListener("pointerup", (e) => {
      if (x0 === null) return;
      const dx = e.clientX - x0;
      x0 = null;
      if (Math.abs(dx) > 40) show(index + (dx < 0 ? 1 : -1));
    });
    stage.addEventListener("pointercancel", () => { x0 = null; });
  }

  function show(i) {
    const n = album.photos.length;
    index = (i + n) % n;
    const [id, cap] = album.photos[index];
    const img = dlg.querySelector(".pf-gal__img");
    img.classList.add("out");
    const next = new Image();
    next.onload = next.onerror = () => {
      img.src = next.src;
      img.alt = cap || album.title;
      img.classList.remove("out");
    };
    next.src = big(id);
    dlg.querySelector(".pf-gal__count").textContent = `${index + 1} / ${n}`;
    dlg.querySelector(".pf-gal__cap").textContent = cap || "";
    dlg.querySelectorAll(".pf-gal__thumbs button").forEach((b, k) => {
      const on = k === index;
      b.setAttribute("aria-current", on);
      if (on) b.parentElement.scrollTo({ left: b.offsetLeft - (b.parentElement.clientWidth - b.offsetWidth) / 2, behavior: "smooth" });
    });
    // Соседние фото подгружаем заранее, чтобы листание было мгновенным
    [index + 1, index - 1].forEach((k) => { new Image().src = big(album.photos[(k + n) % n][0]); });
  }

  function open(key, i = 0) {
    album = albums()[key];
    if (!album) return;
    if (!dlg) build();
    dlg.querySelector(".pf-gal__title").textContent = album.title;
    dlg.querySelector(".pf-gal__thumbs").innerHTML = album.photos
      .map(([id, cap], k) => `<button data-i="${k}" aria-label="Фото ${k + 1}${cap ? `: ${cap}` : ""}"><img loading="lazy" src="${thumb(id)}" alt=""></button>`).join("");
    const single = album.photos.length < 2;
    dlg.querySelectorAll(".pf-gal__nav").forEach((b) => { b.hidden = single; });
    dlg.showModal();
    document.documentElement.style.overflow = "hidden";
    show(i);
  }

  // Прокрутку страницы возвращаем сразу: событие close в фоновых вкладках может прийти с опозданием
  function close() {
    document.documentElement.style.overflow = "";
    if (dlg && dlg.open) dlg.close();
  }

  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-album]");
    if (!t) return;
    e.preventDefault();
    open(t.dataset.album, +(t.dataset.index || 0));
  });
  document.addEventListener("keydown", (e) => {
    const t = e.target.closest && e.target.closest("[data-album]");
    if (t && !/^(A|BUTTON)$/.test(t.tagName) && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); open(t.dataset.album); }
  });

  window.PFGallery = { open, close, count: (key) => (albums()[key] ? albums()[key].photos.length : 0) };
})();
