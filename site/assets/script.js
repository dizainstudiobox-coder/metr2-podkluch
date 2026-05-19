// Каталог: грузим из data/projects.json и рендерим карточки
(async function renderCatalog() {
  const grid = document.getElementById('catalog-grid');
  if (!grid) return;
  try {
    const res = await fetch('data/projects.json');
    const projects = await res.json();
    grid.innerHTML = projects.map(p => `
      <a href="project.html?id=${p.id}" class="project-card">
        <div class="project-img">
          <span class="project-img-placeholder">${p.rooms_short}</span>
          <span class="status ${p.ready ? 'ready' : ''}">${p.ready ? 'Готов' : 'В разработке'}</span>
        </div>
        <div class="project-card-body">
          <div class="project-meta">
            <span>${p.area_m2} м²</span>
            <span class="dot"></span>
            <span>${p.corpus}</span>
          </div>
          <h3>${p.title}</h3>
          <p class="subtitle">${p.subtitle}</p>
          <div class="price-row">
            <div>
              <div class="price-label">Цена проекта</div>
              <div class="price">${formatPrice(p.price)} ₽</div>
            </div>
            <span class="cta">Подробнее →</span>
          </div>
        </div>
      </a>
    `).join('');
  } catch (e) {
    grid.innerHTML = '<p>Каталог временно недоступен. Напишите нам в Telegram.</p>';
    console.error('Catalog load failed:', e);
  }
})();

// Project page: грузим один проект по ?id=
(async function renderProject() {
  const root = document.getElementById('project-root');
  if (!root) return;
  const params = new URLSearchParams(location.search);
  const id = params.get('id');
  if (!id) { location.href = 'index.html#catalog'; return; }
  try {
    const res = await fetch('data/projects.json');
    const projects = await res.json();
    const p = projects.find(x => x.id === id);
    if (!p) { root.innerHTML = '<div class="container" style="padding:96px 0;"><h1>Проект не найден</h1><p><a href="index.html#catalog">← вернуться в каталог</a></p></div>'; return; }
    document.title = `${p.title} — ${p.subtitle} · МЕТР² ПОД КЛЮЧ`;
    root.innerHTML = `
      <div class="container project-hero">
        <div class="breadcrumb">
          <a href="index.html">Главная</a> · <a href="index.html#catalog">Каталог</a> · ${p.title}
        </div>
        <div class="project-detail-grid">
          <div>
            <div class="project-detail-img">
              <span class="placeholder">${p.rooms_short}</span>
            </div>
          </div>
          <div class="project-detail">
            <h1>${p.title}</h1>
            <div class="style-line">${p.subtitle}</div>
            <ul class="specs">
              <li><span class="key">Площадь</span> <span class="val">${p.area_m2} м²</span></li>
              <li><span class="key">Тип квартиры</span> <span class="val">${p.rooms}</span></li>
              <li><span class="key">Стиль</span> <span class="val">${p.style}</span></li>
              <li><span class="key">Корпус ЖК</span> <span class="val">${p.corpus}</span></li>
              <li><span class="key">Статус</span> <span class="val">${p.ready ? 'Готов к покупке' : 'В разработке — первые в очереди'}</span></li>
            </ul>
            <p class="project-description">${p.description}</p>
            <div class="price-block">
              <div class="label">Стоимость проекта</div>
              <div class="amount">${formatPrice(p.price)}<sup> ₽</sup></div>
              <a href="https://t.me/Metr_pod_klyuch_bot?start=project_${p.id}" class="btn" target="_blank" rel="noopener" style="width:100%; justify-content:center;">
                ${p.ready ? 'Купить проект' : 'Хочу этот проект →'}
              </a>
            </div>
            <p style="font-size:13px;color:var(--text-muted);">
              По нажатию — вы попадаете в Telegram-бот, где оставляете заявку.
              Лично свяжусь с вами в течение дня.
            </p>
          </div>
        </div>
      </div>
    `;
  } catch (e) {
    console.error('Project load failed:', e);
  }
})();

function formatPrice(n) {
  return new Intl.NumberFormat('ru-RU').format(n);
}
