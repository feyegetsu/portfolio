// ================= НАСТРОЙКИ: контакты и данные о себе меняются только здесь =================
const CONFIG = {
  telegram: "feyegetsu",           // ник в Telegram без @
  email: "feyegetsu.dev@yandex.ru",
  github: "feyegetsu",
  repo: "https://github.com/feyegetsu/portfolio",
  pilotLeft: 2,                    // сколько мест по пилотной цене ещё осталось: меняйте вручную
  // Блок «Кто это делает» и подвал. Пустое поле просто не показывается
  name: "",                        // имя, например «Владимир»
  city: "",                        // город, например «Петербург»
  status: "",                      // статус, например «самозанятый»
  photo: "",                       // фото, например «assets/me.jpg»: по пояс, при дневном свете
};

const $ = (id) => document.getElementById(id);
const O = window.PF_OFFERS;
const { rub, plural } = O;
const tgLink = (text) => `https://t.me/${CONFIG.telegram}${text ? `?text=${encodeURIComponent(text)}` : ""}`;

// ---------- Контакты ----------
document.querySelectorAll("[data-contact]").forEach((el) => {
  const type = el.dataset.contact;
  if (type === "telegram") {
    el.href = tgLink();
    if (el.hasAttribute("data-nick")) el.textContent = `@${CONFIG.telegram}`;
  }
  if (type === "github") el.href = `https://github.com/${CONFIG.github}`;
  if (type === "email") {
    el.textContent = CONFIG.email;
    if (el.tagName === "A") el.href = `mailto:${CONFIG.email}`;
  }
});
$("year").textContent = new Date().getFullYear();
$("botWant").href = tgLink("Здравствуйте! Хочу такого же Telegram-бота для своего кафе.");
$("reviewLink").href = tgLink("Здравствуйте! Пришлите, пожалуйста, бесплатный разбор моего сайта: ");

// ---------- Кто это делает ----------
{
  const who = [CONFIG.name, CONFIG.status, CONFIG.city].filter(Boolean);
  if (CONFIG.name) $("aboutIntro").textContent = `Меня зовут ${CONFIG.name}. ${$("aboutIntro").textContent}`;
  if (CONFIG.status || CONFIG.city) $("aboutMeta").prepend(`${[CONFIG.status, CONFIG.city].filter(Boolean).join(" · ")} · `);
  if (who.length) { $("footerWho").textContent = who.join(" · "); $("footerWho").hidden = false; }
  if (CONFIG.photo) {
    const img = new Image();
    img.src = CONFIG.photo;
    img.alt = CONFIG.name || "Фото";
    img.loading = "lazy";
    $("aboutPhoto").replaceChildren(img);
    $("aboutPhoto").classList.add("about__photo--img");
  }
}

// ---------- Пилотные места ----------
{
  const left = Math.max(0, Math.min(O.pilot.total, CONFIG.pilotLeft));
  const places = `${left} ${plural(left, "место", "места", "мест")}`;
  document.querySelectorAll(".pilot-left-places").forEach((el) => { el.textContent = places; });
  if (left) {
    document.querySelector(".pilot__left").innerHTML = `Осталось <b>${left}</b> ${plural(left, "место", "места", "мест")} из ${O.pilot.total}`;
    document.querySelector(".pilot__dots").innerHTML = Array.from({ length: O.pilot.total }, (_, i) => `<i class="${i < O.pilot.total - left ? "taken" : ""}"></i>`).join("");
  } else {
    // Места закончились: пилотная цена пропадает отовсюду
    document.querySelector(".badge").innerHTML = '<span class="dot"></span> Беру новые проекты';
    document.querySelector(".hero__pilot").hidden = true;
    $("pilot").hidden = true;
    $("calcPilot").checked = false;
    $("calcPilot").closest("label").hidden = true;
  }
}

// ---------- Мобильное меню ----------
const burger = $("burger");
const nav = $("nav");
const setMenu = (open) => {
  nav.classList.toggle("open", open);
  burger.classList.toggle("open", open);
  burger.setAttribute("aria-expanded", open);
};
burger.addEventListener("click", () => setMenu(!nav.classList.contains("open")));
nav.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => setMenu(false)));

// ---------- Кнопка в шапке подстраивается под то, где человек сейчас ----------
// Дошёл до услуг и цен — «Рассчитать за минуту», у самого калькулятора и ниже — снова «Написать в Telegram»
const headerCta = $("headerCta");
const ctaLabel = headerCta.querySelector("span");
let ctaMode = "";
function updateHeaderCta() {
  const h = innerHeight;
  const services = $("services").getBoundingClientRect().top;
  const calc = $("calc").getBoundingClientRect().top;
  const mode = services < h * 0.6 && calc > h * 0.5 ? "calc" : "tg";
  if (mode === ctaMode) return;
  ctaMode = mode;
  headerCta.classList.toggle("is-calc", mode === "calc");
  if (mode === "calc") {
    ctaLabel.textContent = "Рассчитать за минуту";
    headerCta.href = "#calc";
    headerCta.removeAttribute("target");
  } else {
    ctaLabel.textContent = "Написать в Telegram";
    headerCta.href = tgLink();
    headerCta.target = "_blank";
  }
}

// ---------- Кнопка «наверх» и липкая панель связи на телефоне ----------
const toTop = $("toTop");
const stickyCta = $("stickyCta");
const contactSec = $("contact");
const updateTop = () => {
  const nearContact = contactSec.getBoundingClientRect().top < innerHeight;
  stickyCta.classList.toggle("show", scrollY > innerHeight * 0.7 && !nearContact);
  const max = document.documentElement.scrollHeight - innerHeight;
  toTop.style.setProperty("--p", max > 0 ? Math.min(1, scrollY / max).toFixed(3) : 0);
  toTop.classList.toggle("show", scrollY > 240);
  updateHeaderCta();
};
addEventListener("scroll", updateTop, { passive: true });
addEventListener("resize", updateTop);
updateTop();

// ---------- Работы и кейсы ----------
// task и can — для карточки, goal/done/tech — для подробного окна кейса
const projects = [
  { slug: "restaurant", title: "Ресторан «Терруар»", niche: "Ресторан",
    task: "Заполнять все 28 мест бронями заранее.",
    can: "Гость выбирает сезонный сет и вино, видит сумму ужина и бронирует стол на свободное время. Бронь сразу у администратора.",
    chips: ["Бронь стола", "Брони в Telegram"],
    text: "Ресторан сезонной кухни: дегустационный сет по сезонам, винное сопровождение и бронь стола по слотам.",
    goal: "Ресторану высокой кухни нужно заранее заполнять 28 мест: гости бронируют ужин целиком, с сетом и вином.",
    done: ["Четыре сезонных меню: при смене сезона меняются подачи, описания и вина, текущий сезон выбран сам", "Лента из шести подач и переключатель винного сопровождения с пересчётом цены", "Бронь: дата, свободное время, число гостей, повод и сумма ужина на всех", "Подарочные сертификаты, история шефа и фотоальбомы зала, кухни и погреба"],
    tech: ["Бронь уходит в общий API и сразу видна в админке в разделе «Записи»", "Прошедшее время и выходной день недоступны, по умолчанию выбран ближайший день со свободными столами", "Шрифтовая пара Prata и IBM Plex Sans, бронь в шапке, как у ресторанов из гидов"] },
  { slug: "sushi", title: "Суши «Кайсэн»", niche: "Доставка суши",
    task: "Принимать заказы без звонков и не возить еду туда, куда курьер не доезжает.",
    can: "Сайт проверяет адрес до оформления, а заказ приходит админу в Telegram за секунду. Стоп-лист и цены меняются из админки.",
    chips: ["Зона доставки", "Цены меняете сами"],
    text: "Доставка суши: проверка зоны доставки, корзина с палочками, стоп-лист из админки и отслеживание заказа.",
    goal: "Суши-бару нужен свой канал заказов без комиссии агрегаторов, где цены и стоп-лист меняют без программиста.",
    done: ["Меню по разделам с липкой навигацией, которая подсвечивает текущий раздел", "Проверка района: время в пути и условия бесплатной доставки", "Корзина-шторка: количество, палочки на персон, доставка или самовывоз, прогресс до бесплатной доставки", "После заказа экран статуса: принят, готовим, курьер в пути, доставлено"],
    tech: ["Цены и наличие приходят из каталога API: администратор ставит позицию в стоп-лист, и она сразу недоступна на сайте", "Итог заказа сервер считает по своим ценам, подменить цену из браузера нельзя", "Корзина и район сохраняются между визитами"] },
  { slug: "dental", title: "Стоматология «Белая линия»", niche: "Медицина",
    task: "Перестать по сто раз в день отвечать на «сколько стоит».",
    can: "Квиз считает стоимость лечения за минуту, человек видит цену и оставляет номер. Администратор получает заявку с уже посчитанной суммой.",
    chips: ["Квиз с ценой", "Заявки в Telegram"],
    text: "Клиника с прайсом по вкладкам и квизом, который считает стоимость лечения.",
    goal: "Клинике нужно снять страх «сколько это будет стоить» и получать больше заявок на первичную консультацию.",
    done: ["Квиз из трёх вопросов с расчётом примерной стоимости и закреплением скидки", "Прайс по направлениям, переключается без перезагрузки", "Кликабельные карточки врачей и клиники: специализация, график, оборудование", "Кнопка «Записаться к врачу» сама выбирает врача в форме записи"],
    tech: ["Шаги и итог квиза считаются из данных, вопросы легко менять", "Обязательная медицинская оговорка в подвале", "Заявка с квиза приходит вместе с выбранными ответами"] },
  { slug: "autoservice", title: "Автосервис «МоторЛайн»", niche: "Авто",
    task: "Вызвать доверие до визита: честная цена и прозрачный ремонт.",
    can: "Калькулятор считает ремонт под тип машины, запись — прямо из расчёта, а клиент видит этап ремонта по номеру заказа.",
    chips: ["Калькулятор ремонта", "Статус машины"],
    text: "Калькулятор стоимости ремонта и отслеживание статуса машины по номеру заказа.",
    goal: "Автосервису нужно вызвать доверие: честная цена до визита и прозрачный ремонт.",
    done: ["Калькулятор: тип машины меняет коэффициент, итог и время работ считаются сразу", "Запись на ремонт прямо из калькулятора", "«Где моя машина?»: этапы ремонта по номеру заказа"],
    tech: ["Итог плавно «набегает», но всегда приходит к точной сумме", "Номер заказа проверяется перед выводом на страницу", "Иконки нарисованы SVG"] },
  { slug: "miniapp", title: "Сытый Лис", niche: "Telegram Mini App", phone: true,
    task: "Свой канал заказов без комиссии агрегаторов и без мобильного приложения.",
    can: "Клиент не выходит из Telegram, ничего не ставит и не регистрируется: заказ в три касания, статус — там же.",
    chips: ["Внутри Telegram", "Промокоды"],
    text: "Доставка еды внутри Telegram: меню, размеры пиццы, промокод, оформление и статус заказа.",
    goal: "Ресторану доставки нужен канал заказов без комиссии агрегаторов и без разработки мобильного приложения.",
    done: ["Меню с поиском и «липкими» категориями, которые подсвечиваются при прокрутке", "Шторка товара: размер пиццы и добавки с пересчётом цены", "Корзина, доставка или самовывоз, промокод, бесплатная доставка от суммы", "Оформление с автоподстановкой имени из Telegram и живой статус заказа"],
    tech: ["Цвета берутся из темы Telegram, поэтому приложение выглядит родным в светлой и тёмной теме", "Нативные кнопки Telegram и вибрация; в обычном браузере их заменяют свои элементы", "Весит мало и открывается быстро даже на слабом мобильном интернете"] },
  { slug: "bar", title: "Бар «Полночь»", niche: "Коктейльный бар",
    task: "Сохранить атмосферу секретного места и при этом собирать брони и гест-лист.",
    can: "Гость проходит проверку 18+, подбирает коктейль за три вопроса и записывается в гест-лист или бронирует кабинет.",
    chips: ["Гест-лист", "Бронь"],
    text: "Спикизи-бар: проверка возраста, неоновая вывеска, коктейли по вкусу, подбор коктейля, гест-лист и бронь.",
    goal: "Бару без вывески нужно сохранить атмосферу секретного места и при этом собирать брони и гест-лист.",
    done: ["Проверка возраста 18+ при первом входе", "«Постучите три раза» открывает пароль дня и кнопку брони", "Коктейли с фильтром по вкусу, крепостью, ценой и рецептом", "Подбор коктейля за три вопроса, вечера недели с гест-листом и бронь стойки, дивана или кабинета"],
    tech: ["Бронь после полуночи записывается на правильную дату", "Гест-лист и бронь уходят в API и видны в админке", "На сенсорных экранах рецепт открывается отдельной кнопкой, а не наведением"] },
  { slug: "florist", title: "Пион & Ко", niche: "Интернет-магазин",
    task: "Продавать букеты, когда магазин закрыт.",
    can: "Корзина не теряется, если человек ушёл и вернулся завтра, а заказ падает флористу в Telegram с адресом и временем.",
    chips: ["Корзина", "Доставка ко времени"],
    text: "Магазин цветов: каталог с фильтрами, корзина с сохранением, оформление доставки.",
    goal: "Цветочной мастерской нужен магазин, где букет можно выбрать и оформить с телефона за минуту.",
    done: ["Каталог с фильтром по категориям и сортировкой по цене и популярности", "Выезжающая корзина с изменением количества и подсказкой до бесплатной доставки", "Оформление: адрес, дата и интервал доставки", "Подписка на цветы и быстрая кнопка «В корзину» на фото"],
    tech: ["Корзина переживает перезагрузку страницы", "Цены и наличие букетов приходят из админки", "Анимации отключаются при системной настройке «уменьшить движение»"] },
  { slug: "cafe", title: "Кофейня «Зерно»", niche: "Общепит",
    task: "Передать атмосферу и превратить просмотр меню в визит.",
    can: "Меню как печатная карта с ценами и бронь столика в виде билета. Бронь сразу у администратора.",
    chips: ["Меню с ценами", "Бронь столика"],
    text: "Сайт кофейни в стиле газеты: печатное меню, полароиды атмосферы и бронь столика.",
    goal: "Кофейне нужен сайт, который передаёт атмосферу и превращает просмотр меню в визит.",
    done: ["Вёрстка в стиле газеты: шапка с датой выпуска, статья в три колонки, буквица", "Меню как печатная карта: название, точки до цены, переключение разделов", "Полароиды атмосферы и бронь столика в виде билета"],
    tech: ["Нельзя выбрать прошедшую дату брони", "Фото подгружаются лениво и в нужном размере", "Надпись по кругу на печати сделана SVG-текстом по контуру"] },
  { slug: "gastrobar", title: "Гастробар «Соль и Солод»", niche: "Гастробар",
    task: "Собирать гостей на квизы и концерты и заранее бронировать под них столы.",
    can: "Доска дня, краны с фильтром по стилю, подбор пива к блюду, афиша с записью и бронь стола по зонам.",
    chips: ["Афиша с записью", "Бронь"],
    text: "Гастробар: меловая доска дня, краны с фильтром по стилю, подбор пива к блюду, афиша с записью и бронь.",
    goal: "Гастробару нужно собирать гостей на квизы и концерты и заранее бронировать под них столы.",
    done: ["Статус «прямо сейчас»: открыто или закрыто, идут ли счастливые часы", "Меловая доска с блюдами дня: сегодняшний день выбран сам", "Краны с крепостью и горечью, фильтр по стилю и цены со скидкой в счастливые часы", "Подбор пива к блюду, афиша недели с записью и бронь по зонам"],
    tech: ["Запись на событие и бронь стола уходят в API и видны в админке", "Афиша строится от сегодняшней даты: всегда ближайшие события", "Индустриальная типографика и рукописный шрифт для доски"] },
  { slug: "barbershop", title: "Барбершоп BLADE", niche: "Красота",
    task: "Разгрузить администратора: клиенты записываются сами, в любое время.",
    can: "Запись в три шага: услуга, мастер, свободное время. Занятые и прошедшие слоты недоступны.",
    chips: ["Онлайн-запись", "Запись в Telegram"],
    text: "Олдскульная вывеска и онлайн-запись в 3 шага: услуга, мастер, свободное время.",
    goal: "Барбершопу нужно разгрузить администратора: клиенты должны записываться сами, в любое время.",
    done: ["Запись в три шага с прогресс-баром и сводкой перед подтверждением", "Календарь на неделю, занятые и прошедшие слоты недоступны", "Вывеска с эмблемой, фото в золотой раме и прайс в виде таблички"],
    tech: ["На одно время к мастеру записаться может только один человек, даже если нажали одновременно", "Сегодняшние слоты, которые уже прошли, блокируются по текущему времени", "Чёрно-белые фото становятся цветными при наведении"] },
  { slug: "fitness", title: "Фитнес-клуб PULSE", niche: "Спорт",
    task: "Чтобы клиенты сами записывались на занятия и видели свободные места.",
    can: "Расписание на неделю с записью в один клик и счётчиком мест, абонементы с переключением периода.",
    chips: ["Расписание", "Запись на занятия"],
    text: "Сайт-плакат: расписание на неделю с записью и абонементы с переключением периода.",
    goal: "Клубу нужно, чтобы клиенты сами записывались на групповые занятия и видели свободные места.",
    done: ["Расписание на 7 дней с фильтром по типу тренировок", "Запись и отмена в один клик, счётчик свободных мест", "Первый экран как спортивный плакат и направления-полосы, которые раскрываются по наведению"],
    tech: ["Мест на занятии не может стать больше, чем в зале", "Пустой результат фильтра показывает подсказку, а не пустоту", "Живой счётчик «сейчас в клубе»"] },
  { slug: "realty", title: "Агентство «Квадрат»", niche: "Недвижимость",
    task: "Помочь клиенту быстро сузить выбор и сразу понять платёж по ипотеке.",
    can: "Фильтры и избранное, карточка объекта с галереей и ипотечный калькулятор с переплатой.",
    chips: ["Каталог", "Ипотечный калькулятор"],
    text: "Каталог квартир с фильтрами и избранным, карточка объекта с галереей, ипотечный калькулятор.",
    goal: "Агентству нужен каталог, где клиент быстро сужает выбор и сразу понимает платёж по ипотеке.",
    done: ["Фильтры по комнатам, цене, типу и району, избранное", "Карточка объекта с галереей и платежом по ипотеке", "Ипотечный калькулятор с программами и долей переплаты"],
    tech: ["Платёж по формуле банка, переплата на круговой диаграмме", "Избранное сохраняется между визитами", "Карточки открываются и с клавиатуры, окно закрывается по Esc"] },
  { slug: "saas", title: "Taskly", niche: "IT-стартап",
    task: "Показать продукт в действии прямо на лендинге и довести до регистрации.",
    can: "Канбан-доска на первом экране перетаскивается мышью и пальцем, тариф считается по числу людей.",
    chips: ["Живая демо-доска", "Расчёт тарифа"],
    text: "Лендинг SaaS-сервиса с интерактивной канбан-доской и расчётом тарифа по числу людей.",
    goal: "Стартапу нужно показать продукт в действии прямо на лендинге и довести до регистрации.",
    done: ["Канбан-доска на первом экране: карточки перетаскиваются между колонками", "Тарифы с ползунком числа участников и скидкой за год", "Сетка возможностей, отзывы и FAQ"],
    tech: ["Перетаскивание работает и мышью, и пальцем", "Конфетти при переносе задачи в «Готово»", "Карточки вставляются по позиции курсора, а не только в конец"] },
  { slug: "admin", title: "Админка", niche: "Панель управления", url: "admin/", code: "backend",
    task: "Заявки с сайтов должны куда-то приходить, а владелец — управлять ими без программиста.",
    can: "Заявки, записи и заказы со всех демо в одной панели: статусы, стоп-лист, цены и доступы сотрудников.",
    chips: ["Демо-вход открыт", "Все сайты в одной панели"],
    text: "Общий бэкенд для всех сайтов: заявки, записи, заказы, каталог, роли сотрудников и живая админ-панель.",
    goal: "Заявки с сайтов должны куда-то приходить, а владелец должен ими управлять без программиста и без доступа к коду.",
    done: ["Заявки, запись на время, заказы, каталог, статистика, выгрузка в таблицу", "Дашборд, таблицы с поиском и фильтрами, статусы, стоп-лист и цены, команда", "Роли «владелец», «администратор», «сотрудник» и доступ только к своим сайтам", "Все 13 демо-сайтов отправляют формы сюда; изменения в админке сразу видны на сайте"],
    tech: ["Двойную запись на один слот не пропустит сама база: за это отвечает ограничение в БД, даже если два человека нажали одновременно", "Цену заказа сервер считает сам: каталог, размеры, добавки, промокод и доставка; цена из браузера не используется", "Валидация телефонов, защита от ботов и лимит заявок с одного IP", "50 автотестов на pytest в CI, включая тесты по QA-ревью, Docker и docker-compose с PostgreSQL", "На GitHub Pages сервера нет, поэтому здесь работает демо-режим: те же правила, данные в браузере"] },
];
const MAIN_WORKS = 6;
const caseUrl = (p) => p.url || `projects/${p.slug}/`;
const codeUrl = (p) => `${CONFIG.repo}/tree/main/${p.code || `projects/${p.slug}`}`;
const daysLabel = (n) => `${n} ${plural(n, "день", "дня", "дней")}`;

function workCard(p) {
  const q = O.projects[p.slug] && O.quote(O.projects[p.slug]);
  return `
    <article class="work">
      <button class="work__preview" data-case="${p.slug}" aria-label="Подробнее о проекте: ${p.title}">
        <img class="work__shot" src="assets/previews/${p.slug}.jpg" alt="" loading="lazy" decoding="async" data-slug="${p.slug}">
        <span class="work__open">Подробнее о проекте</span>
      </button>
      <div class="work__body">
        <span class="work__niche">${p.niche}</span>
        <h3>${p.title}</h3>
        <p><b>Задача:</b> ${p.task}</p>
        <p><b>Что умеет:</b> ${p.can}</p>
        <ul class="benefits">${p.chips.map((t) => `<li>${t}</li>`).join("")}</ul>
        <div class="work__foot">
          <a class="btn btn--small btn--ghost work__demo" href="${caseUrl(p)}" target="_blank" rel="noopener">Открыть демо ↗</a>
          ${q ? `<a class="work__price" href="#calc" data-calc="${p.slug}">Такой же: ${rub(q.full)} · ${daysLabel(q.days)}</a>` : ""}
        </div>
      </div>
    </article>`;
}
$("worksGrid").innerHTML = projects.slice(0, MAIN_WORKS).map(workCard).join("");
$("worksMoreGrid").innerHTML = projects.slice(MAIN_WORKS).map(workCard).join("");
$("worksMoreCount").textContent = projects.length - MAIN_WORKS;

// Если скриншота ещё нет, показываем живой сайт в уменьшенном iframe
document.querySelectorAll(".work__shot").forEach((img) => {
  img.addEventListener("error", () => {
    const f = document.createElement("iframe");
    f.src = caseUrl(projects.find((p) => p.slug === img.dataset.slug));
    f.title = "Превью";
    f.tabIndex = -1;
    f.setAttribute("aria-hidden", "true");
    f.loading = "lazy";
    img.replaceWith(f);
    const fit = () => { f.style.transform = `scale(${f.parentElement.clientWidth / 1280})`; };
    fit();
    new ResizeObserver(fit).observe(f.parentElement);
  }, { once: true });
});

// ---------- Окно кейса ----------
const caseEl = $("case");
let caseIdx = -1;
let lastFocus = null;

function openCase(slug, push = true) {
  const i = projects.findIndex((p) => p.slug === slug);
  if (i < 0) return;
  const p = projects[i];
  caseIdx = i;
  if (!caseEl.open) {
    lastFocus = document.activeElement;
    caseEl.showModal();
    document.body.classList.add("lock");
  }
  const q = O.projects[p.slug] && O.quote(O.projects[p.slug]);
  const device = p.phone || matchMedia("(max-width: 760px)").matches ? "phone" : "desktop";
  caseEl.querySelector(".case__inner").innerHTML = `
    <div class="case__stage">
      <div class="case__devices" role="group" aria-label="Устройство">
        <button data-device="desktop" aria-pressed="${device === "desktop"}">Компьютер</button>
        <button data-device="phone" aria-pressed="${device === "phone"}">Телефон</button>
      </div>
      <div class="frame frame--${device}" id="caseFrame"><div class="frame__screen">
        <iframe src="${caseUrl(p)}${p.phone ? "?embed" : ""}" title="Демо: ${p.title}" loading="lazy"></iframe>
      </div></div>
      <p class="case__hint">Сайт живой: можно кликать прямо здесь</p>
      <a class="btn case__open" href="${caseUrl(p)}" target="_blank" rel="noopener">Открыть на весь экран ↗</a>
    </div>
    <article class="case__text">
      <span class="work__niche">${p.niche}</span>
      <h2 id="caseTitle">${p.title}</h2>
      <p class="case__lead">${p.text}</p>
      <h3>Задача</h3><p>${p.goal}</p>
      <h3>Что сделано</h3><ul class="checks">${p.done.map((d) => `<li>${d}</li>`).join("")}</ul>
      <h3>Как устроено</h3><ul class="case__tech">${p.tech.map((d) => `<li>${d}</li>`).join("")}</ul>
      <div class="case__actions">
        <a class="btn case__site" href="${caseUrl(p)}" target="_blank" rel="noopener">Открыть демо ↗</a>
        ${q ? `<a class="btn btn--ghost" href="#calc" data-calc="${p.slug}" data-close>Такой же: ${rub(q.full)}</a>` : ""}
      </div>
      <p class="case__code"><a href="${codeUrl(p)}" target="_blank" rel="noopener">Код проекта на GitHub</a></p>
      <div class="case__nav">
        <button data-step="-1">← ${projects[(i - 1 + projects.length) % projects.length].title}</button>
        <button data-step="1">${projects[(i + 1) % projects.length].title} →</button>
      </div>
    </article>`;
  caseEl.setAttribute("aria-labelledby", "caseTitle");
  fitCaseFrame();
  caseEl.querySelector(".case__scroll").scrollTop = 0;
  if (push) history.replaceState(null, "", `#case-${slug}`);
}

// В режиме «Компьютер» сайт рендерится на ширине 1280px и уменьшается под рамку, как настоящий монитор
function fitCaseFrame() {
  const frame = $("caseFrame");
  const f = frame && frame.querySelector("iframe");
  if (!f) return;
  // В режиме «Телефон» на узком экране сайт рисуется на ширине обычного смартфона (390px) и тоже уменьшается
  const base = frame.classList.contains("frame--desktop") ? 1280 : frame.clientWidth < 390 ? 390 : 0;
  if (base) {
    const k = frame.clientWidth / base;
    Object.assign(f.style, { width: `${base}px`, height: `${frame.clientHeight / k}px`, transform: `scale(${k})`, transformOrigin: "0 0", position: "absolute", top: "0", left: "0" });
  } else {
    Object.assign(f.style, { width: "", height: "", transform: "", position: "", top: "", left: "" });
  }
}
addEventListener("resize", () => caseEl.open && fitCaseFrame());
// Рамка меняет размер с анимацией: пересчитываем масштаб, когда она закончилась
caseEl.addEventListener("transitionend", (e) => { if (e.target.id === "caseFrame" && e.propertyName === "width") fitCaseFrame(); });

// Уборка после закрытия делается сразу, не дожидаясь события close: в фоновых вкладках оно может прийти с опозданием
function cleanupCase(restoreFocus = true) {
  if (!document.body.classList.contains("lock")) return;
  document.body.classList.remove("lock");
  caseEl.querySelector(".case__inner").innerHTML = "";
  if (location.hash.startsWith("#case-")) history.replaceState(null, "", "#works");
  // preventScroll: иначе фокус прокручивает страницу обратно к карточке
  if (lastFocus && restoreFocus) lastFocus.focus({ preventScroll: true });
}
function closeCase(restoreFocus = true) {
  if (caseEl.open) caseEl.close();
  cleanupCase(restoreFocus);
}
caseEl.addEventListener("cancel", (e) => {
  e.preventDefault();
  closeCase();
});
caseEl.addEventListener("close", () => cleanupCase());
caseEl.addEventListener("click", (e) => {
  if (e.target === caseEl) return closeCase();
  const t = e.target.closest("button, a");
  if (!t) return;
  if (t.matches("[data-close]")) {
    if (t.dataset.calc) {
      // «Такой же»: закрываем окно, выбираем пункты в калькуляторе и едем к нему
      e.preventDefault();
      closeCase(false);
      applyCalc(O.projects[t.dataset.calc]);
      history.replaceState(null, "", "#calc");
      setTimeout(() => $("calc").scrollIntoView({ behavior: "smooth" }), 30);
    } else closeCase();
    return;
  }
  if (t.dataset.step) openCase(projects[(caseIdx + +t.dataset.step + projects.length) % projects.length].slug);
  if (t.dataset.device) {
    $("caseFrame").className = `frame frame--${t.dataset.device}`;
    caseEl.querySelectorAll("[data-device]").forEach((b) => b.setAttribute("aria-pressed", b === t));
    // ждём, пока рамка поменяет размер
    setTimeout(fitCaseFrame, 460);
    fitCaseFrame();
  }
});
caseEl.addEventListener("keydown", (e) => {
  if (e.target.closest("input, textarea")) return;
  if (e.key === "ArrowRight") openCase(projects[(caseIdx + 1) % projects.length].slug);
  if (e.key === "ArrowLeft") openCase(projects[(caseIdx - 1 + projects.length) % projects.length].slug);
});
document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-case]");
  if (t && !caseEl.contains(t)) openCase(t.dataset.case);
});
// Прямые ссылки вида #case-florist
const fromHash = () => {
  const m = location.hash.match(/^#case-([\w-]+)$/);
  if (!m) return;
  if (projects.findIndex((p) => p.slug === m[1]) >= MAIN_WORKS) $("worksMore").open = true;
  openCase(m[1], false);
};
addEventListener("hashchange", fromHash);

// ---------- С чего начать ----------
const icon = (d) => `<svg viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
const offers = [
  { big: true, type: "site", title: "Сайт для кафе, салона или клиники",
    ic: icon('<path d="M17 8h1a4 4 0 0 1 0 8h-1M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V8zM6 2v3M10 2v3M14 2v3"/>'),
    text: "Меню или прайс с ценами, бронь или запись, карта и часы работы. Гость смотрит меню и свободное время, бронирует стол, а заявка приходит вам в Telegram." },
  { big: true, type: "bot", title: "Telegram-бот",
    ic: icon('<path d="M21 4 3 11l6 2 2 6 3-4 5 4 2-15z"/><path d="m9 13 8-6"/>'),
    text: "Приём заказов, запись, рассылки акций и ответы на частые вопросы. Работает круглосуточно, заказ сразу у администратора. Хороший способ начать с небольшого бюджета." },
  { opt: "booking", title: "Онлайн-запись или бронь",
    ic: icon('<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18M9 16l2 2 4-4"/>'),
    text: "Услуга, мастер, свободное время — к любому сайту." },
  { type: "shop", title: "Магазин или каталог",
    ic: icon('<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6"/>'),
    text: "Каталог с фильтрами, корзина и оформление заказа." },
  { type: "miniapp", title: "Telegram Mini App",
    ic: icon('<rect x="6" y="2" width="12" height="20" rx="2.5"/><path d="M11 18h2"/>'),
    text: "Приложение внутри Telegram: заказ в три касания, без установки." },
  { opt: "calc", title: "Калькулятор или квиз",
    ic: icon('<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8M8 10h8M8 14h2M14 14h2M8 18h2M14 18h2"/>'),
    text: "Клиент сам видит цену и охотнее оставляет заявку." },
];
$("servicesGrid").innerHTML = offers.map((s) => {
  const item = s.type ? O.types.find((t) => t.id === s.type) : O.opts.find((o) => o.id === s.opt);
  const price = s.type ? `от ${rub(item.price)}` : `+${rub(item.price)} к сайту`;
  const data = s.type ? `data-calc-type="${s.type}"` : `data-calc-opt="${s.opt}"`;
  return `<article class="offer${s.big ? " offer--big" : ""}">
      <div class="offer__icon">${s.ic}</div>
      <h3>${s.title}</h3>
      <p>${s.text}</p>
      <p class="offer__price"><b>${price}</b><span>${s.type ? daysLabel(item.days) : `+${daysLabel(item.days)}`}</span></p>
      <a class="offer__link" href="#calc" ${data}>Посчитать для моего случая →</a>
    </article>`;
}).join("");

// ---------- Появление при прокрутке ----------
const io = new IntersectionObserver((entries) => entries.forEach((e) => {
  if (e.isIntersecting) { e.target.classList.add("visible"); io.unobserve(e.target); }
}), { threshold: 0.1 });
document.querySelectorAll(".offer, .work, .steps li, .included__item, .faq, .calc, .promises li").forEach((el) => {
  el.classList.add("reveal");
  io.observe(el);
});
// Карточки из свёрнутого блока показываем сразу при раскрытии
$("worksMore").addEventListener("toggle", () => {
  if ($("worksMore").open) $("worksMoreGrid").querySelectorAll(".reveal").forEach((el) => el.classList.add("visible"));
});

// ---------- Живость: подсветка за курсором, «магнитные» кнопки, счётчики ----------
const finePointer = matchMedia("(hover: hover) and (pointer: fine)").matches;
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
if (finePointer && !reduceMotion) {
  document.addEventListener("pointermove", (e) => {
    const el = e.target.closest(".offer, .work, .included__item, .steps li");
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${e.clientX - r.left}px`);
    el.style.setProperty("--my", `${e.clientY - r.top}px`);
  });
  document.querySelectorAll(".hero__cta, .contact__links .btn").forEach((b) => {
    b.addEventListener("pointermove", (e) => {
      const r = b.getBoundingClientRect();
      b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.18}px, ${(e.clientY - r.top - r.height / 2) * 0.3}px)`;
    });
    b.addEventListener("pointerleave", () => { b.style.transform = ""; });
  });
}

const countIO = new IntersectionObserver((entries) => entries.forEach((e) => {
  if (!e.isIntersecting) return;
  const el = e.target;
  const to = +el.dataset.count;
  countIO.unobserve(el);
  if (reduceMotion) return;
  el.style.minWidth = `${el.getBoundingClientRect().width}px`;
  el.style.fontVariantNumeric = "tabular-nums";
  const start = performance.now();
  const step = (t) => {
    const p = Math.min(1, (t - start) / 1200);
    el.textContent = Math.round(to * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
  setTimeout(() => { el.textContent = to; }, 1400);
}));
document.querySelectorAll("[data-count]").forEach((el) => countIO.observe(el));

// ---------- Telegram-бот прямо на странице ----------
const chat = $("chat");
const keys = $("keys");
const menu = {
  "Кофе": [{ name: "Капучино", price: 220 }, { name: "Латте", price: 240 }, { name: "Флэт уайт", price: 260 }],
  "Выпечка": [{ name: "Круассан", price: 180 }, { name: "Синнабон", price: 210 }],
  "Десерты": [{ name: "Чизкейк", price: 290 }, { name: "Тирамису", price: 320 }],
};
let cart = [];
const cartTotal = () => cart.reduce((s, i) => s + i.price, 0);
const cartSummary = () => Object.entries(cart.reduce((m, i) => ({ ...m, [i.name]: (m[i.name] || 0) + 1 }), {}))
  .map(([n, c]) => `${n} ×${c}`).join(", ");

function addMsg(text, who = "bot") {
  const el = document.createElement("div");
  el.className = `msg msg--${who}`;
  el.textContent = text;
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

// Пока бот «печатает», старые кнопки остаются на месте, но не нажимаются:
// раскладка не прыгает, и второй быстрый тап не попадает в новую кнопку
let keysReadyAt = 0;
function setKeys(buttons) {
  keys.innerHTML = "";
  keys.classList.remove("busy");
  keysReadyAt = performance.now() + 250;
  buttons.forEach(({ label, action, wide }) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    if (wide) b.classList.add("wide");
    b.addEventListener("click", () => {
      if (keys.classList.contains("busy") || performance.now() < keysReadyAt) return;
      keys.classList.add("busy");
      addMsg(label, "user");
      botReply(action);
    });
    keys.appendChild(b);
  });
}

function botReply(action) {
  $("botStatus").textContent = "печатает…";
  setTimeout(() => {
    $("botStatus").textContent = "бот";
    action();
  }, 550);
}

function showMain() {
  addMsg("Выберите, что хотите сделать:");
  setKeys([
    { label: "Меню", action: showCategories },
    { label: `Корзина (${cart.length})`, action: showCart },
    { label: "Адрес и часы", action: showInfo, wide: true },
  ]);
}

function showCategories() {
  addMsg("Выберите категорию:");
  setKeys([
    ...Object.keys(menu).map((cat) => ({ label: cat, action: () => showCategory(cat) })),
    { label: "← Назад", action: showMain },
  ]);
}

function showCategory(cat) {
  addMsg(`${cat}\n\n` + menu[cat].map((i) => `• ${i.name} — ${i.price} ₽`).join("\n"));
  setKeys([
    ...menu[cat].map((item) => ({
      label: `+ ${item.name}`,
      action: () => {
        cart.push(item);
        addMsg(`${item.name} в корзине.\nСумма: ${cartTotal()} ₽`);
        showCategory(cat);
      },
    })),
    { label: "← Категории", action: showCategories },
    { label: `Корзина (${cart.length})`, action: showCart },
  ]);
}

function showCart() {
  if (!cart.length) {
    addMsg("Корзина пока пуста.");
    return showMain();
  }
  addMsg("Ваш заказ:\n\n" + cart.map((i) => `• ${i.name} — ${i.price} ₽`).join("\n") + `\n\nИтого: ${cartTotal()} ₽`);
  setKeys([
    { label: "Оформить заказ", action: checkout },
    { label: "Очистить", action: () => { cart = []; addMsg("Корзина очищена."); showMain(); } },
    { label: "← В меню", action: showMain, wide: true },
  ]);
}

// Финал: заказ принят, и рядом видно, что в ту же секунду получил администратор
function checkout() {
  const num = Math.floor(1000 + Math.random() * 9000);
  addMsg(`Заказ №${num} принят!\nСумма: ${cartTotal()} ₽\n\nБудет готов через 10–15 минут.`);
  $("botAdminTitle").textContent = `Новый заказ №${num}`;
  $("botAdminText").textContent = `${cartSummary()} · ${cartTotal()} ₽`;
  $("botAdmin").hidden = false;
  void $("botAdmin").offsetWidth; // чтобы появление анимировалось из скрытого состояния
  $("botAdmin").classList.add("show");
  cart = [];
  setTimeout(() => addMsg("Ваш заказ готов! Заберите его на кассе."), 1800);
  setTimeout(() => setKeys([{ label: "Начать заново", action: startBot, wide: true }]), 2000);
}

function showInfo() {
  addMsg("Петербург, Литейный пр., 24\nЕжедневно 8:00–22:00\n+7 (812) 407-21-15");
  showMain();
}

function startBot() {
  chat.innerHTML = "";
  cart = [];
  $("botAdmin").classList.remove("show");
  $("botAdmin").hidden = true;
  addMsg("Привет! Я бот кофейни «Зерно».\nПомогу сделать заказ без очереди.");
  showMain();
}
// Уведомление закрывается по нажатию, чтобы не мешало читать чат
$("botAdmin").addEventListener("click", () => $("botAdmin").classList.remove("show"));
startBot();

// ---------- Калькулятор стоимости ----------
const calcState = { type: "site", opts: new Set(["tg"]), k: 1, pilot: $("calcPilot").checked };
const priceLabel = (o) => (o.price ? `+${rub(o.price)}` : "бесплатно");

$("calcTypes").innerHTML = O.types
  .map((t) => `<button type="button" class="calc__type" data-id="${t.id}"><b>${t.name}</b><small>${t.desc} · от ${rub(t.price)}</small><small class="calc__typical">${t.typical}</small></button>`)
  .join("");
$("calcOpts").innerHTML = O.opts
  .map((o) => `<label class="calc__opt"><input type="checkbox" value="${o.id}"><span>${o.name}</span><em${o.price ? "" : ' class="free"'}>${priceLabel(o)}</em></label>`)
  .join("");

// Выставляет калькулятор: тип проекта и допы (из карточки работы, услуги или ссылки из демо)
function applyCalc({ type, opts, add } = {}) {
  if (type && O.types.some((t) => t.id === type)) calcState.type = type;
  if (opts) calcState.opts = new Set(opts.filter((id) => O.opts.some((o) => o.id === id)));
  if (add) {
    calcState.opts.add(add);
    // Запись и калькулятор — допы к сайту: если выбран бот, переключаем на сайт
    if (O.BOT_TYPES.includes(calcState.type)) calcState.type = "site";
  }
  calcState.opts.add("tg");
  syncCalc();
  renderCalc();
}
function syncCalc() {
  document.querySelectorAll(".calc__type").forEach((x) => {
    x.classList.toggle("active", x.dataset.id === calcState.type);
    x.setAttribute("aria-pressed", x.dataset.id === calcState.type);
  });
  $("calcOpts").querySelectorAll("input").forEach((i) => {
    i.checked = calcState.opts.has(i.value);
    // К боту ещё один бот не добавляется
    i.closest("label").classList.toggle("is-off", i.value === "bot" && O.BOT_TYPES.includes(calcState.type));
  });
}

$("calcTypes").addEventListener("click", (e) => {
  const b = e.target.closest(".calc__type");
  if (!b) return;
  calcState.type = b.dataset.id;
  syncCalc();
  renderCalc();
});
$("calcOpts").addEventListener("change", (e) => {
  e.target.checked ? calcState.opts.add(e.target.value) : calcState.opts.delete(e.target.value);
  renderCalc();
});
$("calcPilot").addEventListener("change", (e) => {
  calcState.pilot = e.target.checked;
  renderCalc();
});
$("calcSpeed").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  calcState.k = +b.dataset.k;
  $("calcSpeed").querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
  renderCalc();
});
// Ссылки «Посчитать» в карточках работ и услуг
document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-calc], [data-calc-type], [data-calc-opt]");
  if (!t || caseEl.contains(t)) return;
  if (t.dataset.calc) applyCalc(O.projects[t.dataset.calc]);
  if (t.dataset.calcType) applyCalc({ type: t.dataset.calcType, opts: [...calcState.opts] });
  if (t.dataset.calcOpt) applyCalc({ add: t.dataset.calcOpt });
});

let calcShown = 0;
let calcText = "";
function renderCalc() {
  const q = O.quote({ type: calcState.type, opts: [...calcState.opts], k: calcState.k, pilot: calcState.pilot });
  const { type, opts, full, sum, days, prepay } = q;
  $("calcList").innerHTML = [`<li><span>${type.name}</span><span>${rub(type.price)}</span></li>`,
    ...opts.map((o) => `<li><span>${o.name}</span><span>${priceLabel(o)}</span></li>`),
    calcState.k > 1 ? `<li><span>Срочность</span><span>+30%</span></li>` : "",
    calcState.pilot ? `<li class="calc__pilot"><span>Пилотная цена за отзыв</span><span>−25%</span></li>` : ""].join("");
  $("calcOld").textContent = calcState.pilot ? rub(full) : "";
  $("calcDays").textContent = `Срок: ~${daysLabel(days)}`;
  $("calcPay").innerHTML = `Предоплата ${O.pilot.prepay * 100}% — <b>${rub(prepay)}</b>, после того как одобрите макет. Остальное после сдачи`;
  $("calcLost").innerHTML = `Для сравнения: если в день теряется ${type.lost} со средним чеком ${rub(type.check)}, это <b>${rub(type.check * 30)}</b> в месяц.`;
  calcText = `Здравствуйте! Посчитал проект на сайте:\n• ${type.name}\n${opts.map((o) => `• ${o.name}`).join("\n")}${calcState.k > 1 ? "\n• Срочно" : ""}${calcState.pilot ? "\n• Пилотная цена −25% за отзыв" : ""}\nИтого: ${rub(sum)}, ~${daysLabel(days)}.`;
  animateNumber(sum);
}
function animateNumber(to) {
  // Страховка: если браузер не даёт анимировать (свёрнутое окно), итог всё равно появится
  clearTimeout(animateNumber.done);
  animateNumber.done = setTimeout(() => {
    calcShown = to;
    $("calcSum").textContent = rub(to);
  }, 500);
  const from = calcShown;
  const start = performance.now();
  const step = (t) => {
    const p = Math.min(1, (t - start) / 450);
    calcShown = Math.round(from + (to - from) * (1 - Math.pow(1 - p, 3)));
    $("calcSum").textContent = rub(calcShown);
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
// Чат открываем сразу по нажатию: Safari на iPhone блокирует окна, открытые после await.
// Текст расчёта передаём в ссылке, а в буфер кладём на случай, если Telegram его не подставит.
$("calcSend").addEventListener("click", () => {
  window.open(tgLink(calcText), "_blank", "noopener");
  navigator.clipboard?.writeText(calcText).catch(() => {});
  $("calcHint").innerHTML = "Если сообщение в чате пустое, нажмите в поле ввода и вставьте: <b>расчёт уже скопирован</b>.";
  $("calcHint").classList.add("calc__hint--done");
});

// Ссылка из демо вида ?type=site&opts=booking,tg#calc сразу выбирает нужные пункты
{
  const qs = new URLSearchParams(location.search);
  if (qs.has("type") || qs.has("opts")) {
    applyCalc({ type: qs.get("type"), opts: qs.get("opts") ? qs.get("opts").split(",") : [...calcState.opts] });
    history.replaceState(null, "", location.pathname + location.hash);
  } else {
    syncCalc();
    renderCalc();
  }
}
fromHash();

// ---------- Уведомления ----------
let toastTimer;
function toast(msg) {
  $("toast").textContent = msg;
  $("toast").classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $("toast").classList.remove("show"), 2600);
}
