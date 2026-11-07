// Демо-клиент считает так же, как сервер.
// Берёт из projects/shared/api.js сгенерированные правила (RULES) и функции расчёта (ENGINE)
// и прогоняет их на тех же примерах, что и pytest: backend/tests/parity_cases.json.
// Запуск: node tools/parity.mjs
import { readFileSync } from "node:fs";

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
return { SITES, CATALOGS, priceOrder, checkSlot, siteNow };`;
const { SITES, CATALOGS, priceOrder, checkSlot, siteNow } = new Function(code)();
const SITE = Object.fromEntries(SITES.map((s) => [s.slug, s]));

let failed = 0;
const check = (title, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) failed++;
  console.log(`${ok ? "ok  " : "FAIL"} ${title}${ok ? "" : `\n     ждали:    ${JSON.stringify(want)}\n     получили: ${JSON.stringify(got)}`}`);
};
const run = (fn) => {
  try { return { value: fn() }; } catch (e) { return { error: { status: e.status, message: e.message } }; }
};

for (const c of cases.orders) {
  const catalog = CATALOGS[c.site].map(([ref, name, category, price]) => ({ ref, name, category, price, active: !c.inactive.includes(ref) }));
  const r = run(() => priceOrder(SITE[c.site].pricing, catalog, c.items, c.mode, c.promo));
  check(c.title, r.error ? { error: r.error } : { lines: r.value }, c.error ? { error: c.error } : { lines: c.lines });
}

const pad = (n) => String(n).padStart(2, "0");
for (const c of cases.slots) {
  const s = SITE[c.site];
  const day = siteNow(s.tz);
  day.setDate(day.getDate() + c.day_offset);
  const startsAt = `${day.getFullYear()}-${pad(day.getMonth() + 1)}-${pad(day.getDate())}T${c.time}:00`;
  const r = run(() => checkSlot(s, c.resource, startsAt));
  check(c.title, r.error ? r.error.message : null, c.error);
}

console.log(failed ? `\nРасхождений: ${failed}` : `\nСовпадают с сервером все примеры: ${cases.orders.length + cases.slots.length}`);
process.exit(failed ? 1 : 0);
