// Демо-клиент ведёт себя так же, как сервер.
// 1. Чистые функции расчёта: из projects/shared/api.js берутся сгенерированные правила (RULES) и функции
//    (ENGINE) и прогоняются на примерах заказов, записи и дат CSV.
// 2. Демо-движок целиком: api.js загружается в песочнице с localStorage в памяти, и формы, админка
//    и команда проверяются на тех же примерах, что backend/tests/test_parity.py шлёт настоящему API.
// Все примеры — backend/tests/parity_cases.json. Запуск: node tools/parity.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const root = new URL("../", import.meta.url);
const src = readFileSync(new URL("projects/shared/api.js", root), "utf8");
const cases = JSON.parse(readFileSync(new URL("backend/tests/parity_cases.json", root), "utf8"));

const block = (start, end) => {
  const a = src.indexOf(start);
  const b = src.indexOf(end, a);
  if (a < 0 || b < 0) throw new Error(`В api.js нет блока ${start} … ${end}`);
  return src.slice(a, b + end.length);
};
const code = `${block("/* RULES:START", "/* RULES:END */")}\n${block("/* ENGINE:START", "/* ENGINE:END */")}
return { SITES, CATALOGS, priceOrder, checkSlot, siteNow, localStamp };`;
const { SITES, CATALOGS, priceOrder, checkSlot, siteNow, localStamp } = new Function(code)();
const SITE = Object.fromEntries(SITES.map((s) => [s.slug, s]));

let failed = 0, total = 0;
const check = (title, got, want) => {
  total++;
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) failed++;
  console.log(`${ok ? "ok  " : "FAIL"} ${title}${ok ? "" : `\n     ждали:    ${JSON.stringify(want)}\n     получили: ${JSON.stringify(got)}`}`);
};
const run = (fn) => {
  try { return { value: fn() }; } catch (e) { return { error: { status: e.status, message: e.message } }; }
};

// ---------- 1. Чистые функции ----------
for (const c of cases.orders) {
  const catalog = CATALOGS[c.site].map(([ref, name, category, price]) => ({ ref, name, category, price, active: !c.inactive.includes(ref) }));
  const r = run(() => priceOrder(SITE[c.site].pricing, catalog, c.items, c.mode, c.promo));
  check(c.title, r.error ? { error: r.error } : { lines: r.value }, c.error ? { error: c.error } : { lines: c.lines });
}

const pad = (n) => String(n).padStart(2, "0");
const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
// Дата из примера: day_offset — дни от сегодняшней даты заведения, weekday — ближайший такой день с завтра
function caseDay(c, s) {
  const day = siteNow(s.tz);
  if ("weekday" in c) {
    do day.setDate(day.getDate() + 1); while ((day.getDay() + 6) % 7 !== c.weekday);
  } else {
    day.setDate(day.getDate() + c.day_offset);
  }
  return ymd(day);
}
for (const c of cases.slots) {
  const s = SITE[c.site];
  const r = run(() => checkSlot(s, c.resource, `${caseDay(c, s)}T${c.time}:00`));
  check(c.title, r.error ? r.error.message : null, c.error);
}
for (const c of cases.csv_dates) check(c.title, localStamp(`${c.created_at}Z`, c.tz), c.expected);

// ---------- 2. Демо-движок целиком ----------
// Свежая «вкладка»: свой localStorage, страница админки, таймеры без задержки
function freshApi() {
  const storage = () => {
    const m = new Map();
    return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) };
  };
  const noop = () => {};
  const el = () => ({ style: {}, setAttribute: noop, appendChild: noop, addEventListener: noop, querySelector: () => null, querySelectorAll: () => [] });
  const ctx = {
    console, crypto: globalThis.crypto, URL, URLSearchParams, queueMicrotask,
    setTimeout: (fn) => { queueMicrotask(fn); return 0; }, clearTimeout: noop, setInterval: () => 0, clearInterval: noop,
    localStorage: storage(), sessionStorage: storage(),
    location: { search: "", pathname: "/admin/", href: "http://localhost/admin/" },
    navigator: { webdriver: true },
    document: { currentScript: null, readyState: "complete", head: el(), body: el(), createElement: el, querySelector: () => null,
      querySelectorAll: () => [], getElementById: () => null, addEventListener: noop },
    addEventListener: noop, removeEventListener: noop, confirm: () => false,
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { filename: "api.js" });
  const api = ctx.PortfolioAPI;
  const db = () => JSON.parse(ctx.localStorage.getItem("pf-db-v1"));
  return { api, db };
}
// Как check_response в test_parity.py: код ответа, текст ошибки (если задан) и сохранилось ли
async function outcome(c, fn, count) {
  const before = count ? count() : 0;
  let status = c.status >= 200 && c.status < 300 ? c.status : 0, message;
  try { await fn(); } catch (e) { status = e.status; message = e.message; }
  const got = { status };
  if ("message" in c) got.message = message;
  if ("stored" in c) got.stored = count() > before;
  const want = { status: c.status };
  if ("message" in c) want.message = c.message;
  if ("stored" in c) want.stored = c.stored;
  return [got, want];
}
const asOwner = async () => {
  const t = freshApi();
  await t.api.login("demo@feyegetsu.dev", "demo");
  return t;
};

for (const c of cases.leads) {
  const { api, db } = await asOwner();
  check(c.title, ...(await outcome(c, () => api.createLead(c.site, structuredClone(c.body)), () => db().leads.length)));
}
for (const c of cases.orders_validation) {
  const { api, db } = await asOwner();
  check(c.title, ...(await outcome(c, () => api.createOrder(c.site, structuredClone(c.body)), () => db().orders.length)));
}
for (const c of cases.bookings) {
  const { api, db } = await asOwner();
  const body = { resource: c.resource, starts_at: `${caseDay(c, SITE[c.site])}T${c.time}:00${c.suffix}`, name: "Иван", phone: "+79001234567" };
  if ("website" in c) body.website = c.website;
  check(c.title, ...(await outcome(c, () => api.createBooking(c.site, body), () => db().bookings.length)));
}
for (const c of cases.catalog_patch) {
  const { api } = await asOwner();
  const item = (await api.admin.catalog({ site: c.site })).find((x) => x.ref === c.ref);
  check(c.title, ...(await outcome(c, () => api.admin.updateCatalog(item.id, structuredClone(c.body)))));
}
for (const c of cases.users) {
  const { api } = await asOwner();
  const fn = c.action === "add" ? () => api.admin.addUser(structuredClone(c.body)) : () => api.admin.removeUser(99999);
  check(c.title, ...(await outcome(c, fn)));
}
for (const c of cases.search) {
  const { api } = await asOwner();
  const seeded = (await api.admin.leads({ q: c.q })).total;  // в демо-данных уже есть заявки: считаем прирост
  for (const name of c.names) await api.createLead("cafe", { kind: "table", name, phone: "+79001234567" });
  check(c.title, (await api.admin.leads({ q: c.q })).total - seeded, c.total);
}

console.log(failed ? `\nРасхождений: ${failed} из ${total}` : `\nСовпадают с сервером все примеры: ${total}`);
process.exit(failed ? 1 : 0);
