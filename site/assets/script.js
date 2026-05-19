// Главная: каталог. Карточка показывает план проекта как основную картинку.
(async function renderCatalog() {
  const grid = document.getElementById('catalog-grid');
  if (!grid) return;
  try {
    const res = await fetch('data/projects.json');
    const projects = await res.json();
    grid.innerHTML = projects.map(p => `
      <a href="project.html?id=${p.id}" class="project-card">
        <div class="project-card-plan">
          <img src="assets/projects/${p.plan_image}" alt="План ${p.title}" loading="lazy">
          <span class="status ${p.ready ? 'ready' : ''}">${p.ready ? 'Готов' : 'В разработке'}</span>
        </div>
        <div class="project-card-body">
          <div class="project-meta">
            <span>${p.area_m2} м²</span>
            <span class="dot"></span>
            <span>${p.corpus}</span>
            <span class="dot"></span>
            <span>Артикул: ${p.article}</span>
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

// Страница проекта: карусель (план + визуализации) + специфика
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
    if (!p) {
      root.innerHTML = '<div class="container" style="padding:96px 0;"><h1>Проект не найден</h1><p><a href="index.html#catalog">← в каталог</a></p></div>';
      return;
    }
    document.title = `${p.title} — ${p.subtitle} · МЕТР² ПОД КЛЮЧ`;
    // Список слайдов: первым план, дальше визуализации
    const slides = [
      { src: `assets/projects/${p.plan_image}`, title: 'Планировка', is_plan: true },
      ...p.images.map(img => ({ src: `assets/projects/${img.file}`, title: img.title, is_plan: false })),
    ];
    root.innerHTML = `
      <div class="container project-hero">
        <div class="breadcrumb">
          <a href="index.html">Главная</a> · <a href="index.html#catalog">Каталог</a> · ${p.title}
        </div>
        <div class="project-detail-grid">
          <div class="carousel">
            <div class="carousel-main" id="carousel-main">
              ${slides.map((s, i) => `
                <div class="carousel-slide ${i === 0 ? 'active' : ''}" data-idx="${i}">
                  <img src="${s.src}" alt="${s.title}" loading="${i === 0 ? 'eager' : 'lazy'}">
                </div>
              `).join('')}
              <button class="carousel-arrow prev" aria-label="Назад">‹</button>
              <button class="carousel-arrow next" aria-label="Вперёд">›</button>
              <div class="carousel-counter"><span id="carousel-idx">1</span> / ${slides.length}</div>
            </div>
            <div class="carousel-thumbs">
              ${slides.map((s, i) => `
                <button class="thumb ${i === 0 ? 'active' : ''}" data-idx="${i}" aria-label="${s.title}">
                  <img src="${s.src}" alt="${s.title}" loading="lazy">
                  <span class="thumb-label">${s.title}</span>
                </button>
              `).join('')}
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
              <li><span class="key">Артикул</span> <span class="val">${p.article}</span></li>
              <li><span class="key">Бюджет на оснащение</span> <span class="val">~ ${formatPrice(p.budget_furnish)} ₽</span></li>
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
              По нажатию — попадёте в Telegram-бот, оставите заявку. Лично свяжусь в течение дня.
            </p>
          </div>
        </div>
      </div>
    `;
    // Логика карусели
    let current = 0;
    const N = slides.length;
    const slidesDom = root.querySelectorAll('.carousel-slide');
    const thumbsDom = root.querySelectorAll('.thumb');
    const counter = root.querySelector('#carousel-idx');
    function goto(i) {
      current = (i + N) % N;
      slidesDom.forEach((el, k) => el.classList.toggle('active', k === current));
      thumbsDom.forEach((el, k) => el.classList.toggle('active', k === current));
      counter.textContent = current + 1;
    }
    root.querySelector('.carousel-arrow.next').onclick = () => goto(current + 1);
    root.querySelector('.carousel-arrow.prev').onclick = () => goto(current - 1);
    thumbsDom.forEach((t, i) => t.onclick = () => goto(i));
    document.addEventListener('keydown', e => {
      if (e.key === 'ArrowRight') goto(current + 1);
      if (e.key === 'ArrowLeft') goto(current - 1);
    });
  } catch (e) {
    console.error('Project load failed:', e);
  }
})();

function formatPrice(n) { return new Intl.NumberFormat('ru-RU').format(n); }
