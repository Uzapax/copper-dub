// State
let allAnime = [];
let currentAnime = null;
let currentCategory = 'main'; // 'main' or 'other'
let currentFilter = 'Все';
let searchQuery = '';
let currentEditingAnime = null;

// GitHub Config for direct publishing from Admin Panel
const GITHUB_OWNER = "Uzapax";
const GITHUB_REPO = "copper-dub";

function getGitHubToken() {
  const input = document.getElementById('adm-gh-token');
  if (input && input.value.trim()) {
    localStorage.setItem('copperdub_gh_token', input.value.trim());
    return input.value.trim();
  }
  return localStorage.getItem('copperdub_gh_token') || "";
}

// Check if running inside Telegram WebApp
const isTelegramWebApp = Boolean(window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData);
const tg = window.Telegram?.WebApp;

// DOM Elements
const animeGrid = document.getElementById('anime-grid');
const filterPills = document.querySelectorAll('.pill');
const searchInput = document.getElementById('search-input');
const animeModal = document.getElementById('anime-modal');
const adminModal = document.getElementById('admin-modal');

// Category tabs
const catTabs = document.querySelectorAll('.cat-tab');
const catMainCount = document.getElementById('cat-main-count');
const catOtherCount = document.getElementById('cat-other-count');
const categoryDesc = document.getElementById('category-desc');
const heroBanner = document.getElementById('hero-banner');

// Stats Elements
const statAnimeCount = document.getElementById('stat-anime-count');
const statEpisodesCount = document.getElementById('stat-episodes-count');

// Anime Modal Elements
const modalBanner = document.getElementById('modal-banner');
const modalPoster = document.getElementById('modal-poster');
const modalTitleRu = document.getElementById('modal-title-ru');
const modalTitleEn = document.getElementById('modal-title-en');
const modalStatusBadge = document.getElementById('modal-status-badge');
const modalCategoryBadge = document.getElementById('modal-category-badge');
const modalFormatBadge = document.getElementById('modal-format-badge');
const modalProgressFill = document.getElementById('modal-progress-fill');
const modalProgressText = document.getElementById('modal-progress-text');
const modalCast = document.getElementById('modal-cast');
const modalDesc = document.getElementById('modal-desc');
const modalNotes = document.getElementById('modal-notes');
const episodesList = document.getElementById('episodes-list');
const episodesCountNum = document.getElementById('episodes-count-num');

// Admin Panel Elements
const adminAnimeList = document.getElementById('admin-anime-list');
const admAnimeId = document.getElementById('adm-anime-id');
const admTitleRu = document.getElementById('adm-title-ru');
const admTitleEn = document.getElementById('adm-title-en');
const admCategory = document.getElementById('adm-category');
const admFormat = document.getElementById('adm-format');
const admStatus = document.getElementById('adm-status');
const admEpisodesDone = document.getElementById('adm-episodes-done');
const admEpisodesTotal = document.getElementById('adm-episodes-total');
const admPosterUrl = document.getElementById('adm-poster-url');
const admPosterPreview = document.getElementById('adm-poster-preview');
const admBannerUrl = document.getElementById('adm-banner-url');
const admBannerPreview = document.getElementById('adm-banner-preview');
const admCast = document.getElementById('adm-cast');
const admDesc = document.getElementById('adm-desc');
const admNotes = document.getElementById('adm-notes');
const admAliases = document.getElementById('adm-aliases');
const admEpCount = document.getElementById('adm-ep-count');
const admEpisodesTbody = document.getElementById('adm-episodes-tbody');

// --- THEME SWITCHER (Белая тема vs Тёмная тема) ---
function initTheme() {
  const savedTheme = localStorage.getItem('copperdub_theme') || 'white';
  applyTheme(savedTheme);

  const themeBtn = document.getElementById('theme-toggle-btn');
  if (themeBtn) {
    themeBtn.addEventListener('click', toggleTheme);
  }
}

function applyTheme(themeName) {
  const icon = document.getElementById('theme-icon');
  const label = document.getElementById('theme-label');
  const isWhite = (themeName === 'white' || themeName === 'copper' || themeName === 'light');

  if (isWhite) {
    document.body.classList.add('theme-white');
    document.body.classList.add('theme-copper');
    if (icon) icon.textContent = '☀️';
    if (label) label.textContent = 'Белая тема';
  } else {
    document.body.classList.remove('theme-white');
    document.body.classList.remove('theme-copper');
    if (icon) icon.textContent = '🌙';
    if (label) label.textContent = 'Тёмная тема';
  }
}

function toggleTheme() {
  const isWhite = document.body.classList.contains('theme-white') || document.body.classList.contains('theme-copper');
  const nextTheme = isWhite ? 'dark' : 'white';
  localStorage.setItem('copperdub_theme', nextTheme);
  applyTheme(nextTheme);
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  if (isTelegramWebApp && tg) {
    tg.ready();
    tg.expand();
    document.body.classList.add('inside-telegram');
  }

  initApp();
  setupEventListeners();
});

async function initApp() {
  await loadAnimeList();
}

// Load Anime List
async function loadAnimeList() {
  try {
    let loaded = false;
    
    // 1. Try static catalog.json (instant)
    try {
      const resStatic = await fetch('./catalog.json?v=' + Date.now());
      if (resStatic.ok) {
        allAnime = await resStatic.json();
        loaded = true;
      }
    } catch (e) {}

    // 2. Fallback to API if available
    if (!loaded) {
      try {
        const res = await fetch('/api/anime');
        if (res.ok) {
          allAnime = await res.json();
          loaded = true;
        }
      } catch (e) {}
    }

    if (loaded && allAnime && allAnime.length > 0) {
      updateStats();
      renderHeroBanner();
      renderLatestEpisodeReminder();
      renderGrid();
      checkAuthStatus();
    } else {
      animeGrid.innerHTML = `<div class="error-msg">Каталог пуст или загружается...</div>`;
    }
  } catch (err) {
    animeGrid.innerHTML = `<div class="error-msg">Не удалось загрузить каталог.</div>`;
    console.error('Failed to load anime:', err);
  }
}

// Update Stats & Category Counters
function updateStats() {
  const mainList = allAnime.filter(a => (a.category || 'main') === 'main');
  const otherList = allAnime.filter(a => a.category === 'other');

  if (catMainCount) catMainCount.textContent = mainList.length;
  if (catOtherCount) catOtherCount.textContent = otherList.length;

  if (statAnimeCount) statAnimeCount.textContent = allAnime.length;

  let totalEps = 0;
  allAnime.forEach(a => {
    totalEps += (a.episodes ? a.episodes.length : (a.episodes_done || 0));
  });
  if (statEpisodesCount) statEpisodesCount.textContent = totalEps;
}

// Render Latest Episode Reminder Banner
function renderLatestEpisodeReminder() {
  const container = document.getElementById('latest-release-section');
  if (!container || !allAnime || allAnime.length === 0) return;

  // Find the episode with the highest tg_message_id across all anime
  let latestEp = null;
  let latestAnime = null;
  let maxTgId = -1;

  allAnime.forEach(anime => {
    if (anime.episodes && Array.isArray(anime.episodes)) {
      anime.episodes.forEach(ep => {
        const tgId = Number(ep.tg_message_id) || 0;
        if (tgId > maxTgId) {
          maxTgId = tgId;
          latestEp = ep;
          latestAnime = anime;
        }
      });
    }
  });

  // Fallback: if no tg_message_id found, pick the last episode of the first anime
  if (!latestEp) {
    for (const anime of allAnime) {
      if (anime.episodes && anime.episodes.length > 0) {
        latestAnime = anime;
        latestEp = anime.episodes[anime.episodes.length - 1];
        break;
      }
    }
  }

  if (!latestEp || !latestAnime) {
    container.style.display = 'none';
    return;
  }

  container.style.display = 'block';
  const posterEl = document.getElementById('latest-ep-poster');
  const titleEl = document.getElementById('latest-ep-anime-title');
  const epTitleEl = document.getElementById('latest-ep-title');
  const metaEl = document.getElementById('latest-ep-meta');
  const watchBtn = document.getElementById('btn-watch-latest-ep');
  const posterWrap = document.getElementById('latest-ep-poster-wrap');

  if (posterEl) {
    posterEl.src = latestAnime.poster_url || '';
    posterEl.alt = latestAnime.title_ru || '';
  }
  if (titleEl) {
    titleEl.textContent = latestAnime.title_ru || '';
    titleEl.onclick = () => openAnimeModal(latestAnime.id);
  }
  if (posterWrap) {
    posterWrap.onclick = () => openAnimeModal(latestAnime.id);
  }
  if (epTitleEl) {
    const epNum = latestEp.episode_num || `Серия ${latestEp.episode_order || ''}`;
    const epName = latestEp.title && latestEp.title !== epNum ? ` • ${latestEp.title}` : '';
    epTitleEl.textContent = `${epNum}${epName}`;
  }
  if (metaEl) {
    const cast = latestEp.cast_credits || latestAnime.cast_credits || 'Copper Dub';
    metaEl.textContent = `🎙 Озвучка: ${cast}`;
  }
  if (watchBtn) {
    watchBtn.onclick = (e) => {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      const url = latestEp.tg_post_url || (latestEp.tg_message_id ? `https://t.me/gygdub/${latestEp.tg_message_id}` : '');
      if (url) {
        watchEpisodeInTelegram(url);
      } else {
        openAnimeModal(latestAnime.id);
      }
    };
  }
}

// Render Flagship Hero Banner dynamically from catalog data
function renderHeroBanner() {
  const bleach = allAnime.find(a => a.id === 1 || (a.title_ru && a.title_ru.includes('Блич')));
  if (!bleach) return;

  const epsDone = bleach.episodes ? bleach.episodes.length : (bleach.episodes_done || 32);
  const epsTotal = bleach.episodes_total || 50;

  const heroTitle = document.getElementById('hero-title');
  const heroSubtitle = document.getElementById('hero-subtitle');
  const heroPlayBtn = document.getElementById('hero-play-btn');
  const heroPosterImg = document.querySelector('.hero-poster-img');

  if (heroTitle) heroTitle.textContent = bleach.title_ru;
  if (heroSubtitle) {
    heroSubtitle.textContent = `${bleach.title_en || 'Bleach: Thousand-Year Blood War'} • ${epsDone} из ${epsTotal} серий (${bleach.format || 'Куры 1–3'})`;
  }
  if (heroPlayBtn) {
    heroPlayBtn.textContent = `▶ Смотреть серии (1–${epsDone})`;
    heroPlayBtn.onclick = () => openAnimeModal(bleach.id);
  }
  if (heroPosterImg && bleach.poster_url) {
    heroPosterImg.src = bleach.poster_url;
  }
}

// Render Anime Cards
function renderGrid() {
  const filtered = allAnime.filter(a => {
    // 1. Filter by Category ('main' vs 'other')
    const animeCat = a.category || 'main';
    if (animeCat !== currentCategory) return false;

    // 2. Filter by Status
    const matchFilter = currentFilter === 'Все' || a.status === currentFilter;
    
    // 3. Search query
    const matchSearch = !searchQuery || 
      a.title_ru.toLowerCase().includes(searchQuery) ||
      (a.title_en && a.title_en.toLowerCase().includes(searchQuery)) ||
      (a.aliases && a.aliases.toLowerCase().includes(searchQuery));

    return matchFilter && matchSearch;
  });

  // Toggle Hero banner visibility
  if (heroBanner) {
    if (currentCategory === 'other') {
      heroBanner.style.display = 'none';
    } else {
      heroBanner.style.display = 'flex';
    }
  }

  if (filtered.length === 0) {
    animeGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px 0;">Ничего не найдено в этом разделе.</div>`;
    return;
  }

  animeGrid.innerHTML = filtered.map(anime => {
    let badgeClass = 'badge-in-progress';
    if (anime.status === 'Завершено') badgeClass = 'badge-completed';
    if (anime.status === 'На паузе') badgeClass = 'badge-pause';

    const percent = anime.episodes_total > 0 
      ? Math.round((anime.episodes_done / anime.episodes_total) * 100) 
      : 100;

    return `
      <div class="anime-card" onclick="openAnimeModal(${anime.id})">
        <div class="card-poster-wrap">
          <img class="card-poster" src="${anime.poster_url || 'https://via.placeholder.com/300x420?text=Постер'}" alt="${anime.title_ru}" loading="lazy" onerror="this.src='https://via.placeholder.com/300x420?text=Нет+обложки'">
          <span class="card-badge ${badgeClass}">${anime.status}</span>
          <span class="card-format-tag">${anime.format || 'ТВ-сериал'}</span>
        </div>
        <div class="card-content">
          <h3 class="card-title-ru" title="${anime.title_ru}">${anime.title_ru}</h3>
          <div class="card-title-en">${anime.title_en || '—'}</div>
          <div class="card-cast">🎙 <b>Каст:</b> ${anime.cast || 'Copper Dub'}</div>
          <div class="card-progress">
            <div class="progress-bar">
              <div class="progress-fill" style="width: ${percent}%"></div>
            </div>
            <div class="progress-text">
              <span>Серий: ${anime.episodes ? anime.episodes.length : (anime.episodes_done || 0)} / ${anime.episodes_total || anime.episodes_done}</span>
              <span>${percent}%</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// Open Details Modal
async function openAnimeModal(animeId) {
  try {
    currentAnime = allAnime.find(a => a.id === animeId);
    if (!currentAnime) {
      try {
        const res = await fetch(`/api/anime/${animeId}`);
        if (res.ok) currentAnime = await res.json();
      } catch (e) {}
    }
    if (!currentAnime) return;

    modalPoster.src = currentAnime.poster_url || 'https://via.placeholder.com/300x420?text=Постер';
    modalPoster.onerror = () => { modalPoster.src = 'https://via.placeholder.com/300x420?text=Нет+обложки'; };

    modalBanner.src = currentAnime.banner_url || currentAnime.poster_url || '';
    modalTitleRu.textContent = currentAnime.title_ru;
    modalTitleEn.textContent = currentAnime.title_en || '';
    modalStatusBadge.textContent = currentAnime.status;
    
    if (modalCategoryBadge) {
      modalCategoryBadge.textContent = currentAnime.category === 'other' ? 'Релизы ребят' : 'Основной релиз';
    }
    modalFormatBadge.textContent = currentAnime.format || 'ТВ-сериал';
    modalCast.textContent = currentAnime.cast || 'Copper Dub';
    modalDesc.textContent = currentAnime.description || 'Описание отсутствует.';
    modalNotes.textContent = currentAnime.notes || '—';

    const epsCount = currentAnime.episodes ? currentAnime.episodes.length : (currentAnime.episodes_done || 0);
    const percent = currentAnime.episodes_total > 0 
      ? Math.round((epsCount / currentAnime.episodes_total) * 100) 
      : 100;
    modalProgressFill.style.width = `${percent}%`;
    modalProgressText.textContent = `${epsCount} из ${currentAnime.episodes_total || epsCount} серий (${percent}%)`;

    episodesCountNum.textContent = epsCount;

    renderEpisodesList();

    animeModal.classList.add('active');
    animeModal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  } catch (err) {
    console.error('Error opening anime details:', err);
  }
}

function renderEpisodesList() {
  if (!currentAnime || !currentAnime.episodes || currentAnime.episodes.length === 0) {
    episodesList.innerHTML = `<div style="color: var(--text-muted); font-size: 13px; padding: 12px 0;">Серии пока не добавлены.</div>`;
    return;
  }

  episodesList.innerHTML = currentAnime.episodes.map(ep => {
    const isLinked = Boolean(ep.tg_message_id);
    const postUrl = ep.tg_post_url || (isLinked ? `https://t.me/gygdub/${ep.tg_message_id}` : '');
    const sizeMb = ep.file_size ? (ep.file_size / (1024 * 1024)).toFixed(0) + ' МБ' : '';

    return `
      <div class="tma-episode-card">
        <div class="tma-ep-info">
          <div class="tma-ep-top">
            <span class="tma-ep-num">${ep.episode_num}</span>
            ${sizeMb ? `<span class="tma-ep-size">📦 ${sizeMb}</span>` : ''}
            ${isLinked ? `<span class="tma-ep-tg-tag">В Telegram</span>` : `<span class="tma-ep-no-tag">Скоро</span>`}
          </div>
          
          <div class="tma-ep-credits">
            ${ep.cast_credits ? `<span>🎙 ${ep.cast_credits}</span>` : ''}
            ${ep.sub_credits && ep.sub_credits !== '—' ? `<span> • 📝 ${ep.sub_credits}</span>` : ''}
          </div>
          ${ep.notes && ep.notes !== '—' ? `<div class="tma-ep-notes">${ep.notes}</div>` : ''}
        </div>

        <div class="tma-ep-actions">
          ${isLinked ? `
            <button class="btn btn-primary btn-sm btn-watch-tg" onclick="watchEpisodeInTelegram('${postUrl}')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.52 2.77-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
              </svg>
              Смотреть
            </button>
          ` : `
            <span style="font-size:12px; color:var(--text-dim);">Без ссылки</span>
          `}
        </div>
      </div>
    `;
  }).join('');
}

// Launch Episode in Telegram
function watchEpisodeInTelegram(postUrl) {
  if (!postUrl) {
    alert('Ссылка на пост пока не указана.');
    return;
  }

  // Normalize postUrl to full https://t.me/ URL
  let fullUrl = postUrl;
  if (!fullUrl.startsWith('http')) {
    if (fullUrl.startsWith('t.me/')) {
      fullUrl = 'https://' + fullUrl;
    } else {
      fullUrl = 'https://t.me/gygdub/' + fullUrl;
    }
  }

  // 1. If in Telegram Mini App (TMA): use native Telegram WebApp SDK
  if (isTelegramWebApp && tg && tg.openTelegramLink) {
    try {
      tg.openTelegramLink(fullUrl);
      return;
    } catch (e) {
      console.warn('tg.openTelegramLink error, fallback to browser link:', e);
    }
  }

  // 2. In browser: use tg:// protocol with web link fallback
  const m = fullUrl.match(/t\.me\/([^\/]+)\/(\d+)/);
  if (m) {
    const channel = m[1];
    const postId = m[2];
    const deepLink = `tg://resolve?domain=${channel}&post=${postId}`;

    // Direct anchor click simulation (works on both mobile Safari & Android)
    const a = document.createElement('a');
    a.href = deepLink;
    a.target = '_blank';
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // Fallback: open web URL if native app didn't capture within 600ms
    setTimeout(() => {
      window.open(fullUrl, '_blank', 'noopener');
    }, 600);
  } else {
    window.open(fullUrl, '_blank', 'noopener');
  }
}

function openEpisodeInTelegram(postUrl) {
  watchEpisodeInTelegram(postUrl);
}
window.openEpisodeInTelegram = openEpisodeInTelegram;
window.watchEpisodeInTelegram = watchEpisodeInTelegram;

function closeAnimeModal() {
  animeModal.classList.remove('active');
  animeModal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

// --- ADMIN ACCESS & AUTHENTICATION (ВХОД ТОЛЬКО ПО GITHUB ТОКЕНУ) ---

function isUserAdminAuthorized() {
  const token = localStorage.getItem('copperdub_gh_token');
  return Boolean(token && (token.startsWith('ghp_') || token.startsWith('github_pat_')));
}

function checkAuthStatus() {
  const isAuth = isUserAdminAuthorized();
  const btnOpenAdmin = document.getElementById('btn-open-admin');
  if (btnOpenAdmin) {
    btnOpenAdmin.style.display = isAuth ? 'inline-flex' : 'none';
  }
  const editRows = document.querySelectorAll('.admin-actions-row');
  editRows.forEach(row => {
    row.style.display = isAuth ? 'block' : 'none';
  });
}

function checkAdminAccessAndOpen(animeId = null) {
  if (isUserAdminAuthorized()) {
    openAdminModal(animeId);
    return;
  }

  const entered = prompt('🔐 Вход в админ-панель Copper Dub:\nВведите ваш GitHub Personal Access Token (начинается на ghp_...):\n\n(Обычные пароли отключены. Доступ только по личному токену владельца)');
  if (!entered) return;

  const trimmed = entered.trim();
  if (trimmed.startsWith('ghp_') || trimmed.startsWith('github_pat_')) {
    localStorage.setItem('copperdub_gh_token', trimmed);
    localStorage.setItem('copperdub_admin_auth', '1');
    checkAuthStatus();
    openAdminModal(animeId);
  } else {
    alert('❌ Доступ запрещён!\nВход в админ-панель возможен ТОЛЬКО по личному GitHub токену (ghp_...).\nОбычные пароли отключены для безопасности.');
  }
}

function logoutAdmin() {
  if (confirm('Выйти из панели управления и удалить токен из этого браузера?')) {
    localStorage.removeItem('copperdub_gh_token');
    localStorage.removeItem('copperdub_admin_auth');
    closeAdminModal();
    checkAuthStatus();
    alert('✓ Вы успешно вышли из админ-панели.');
  }
}

// --- ADMIN PANEL FUNCTIONS ---

function openAdminModal(animeToSelectId = null) {
  const tokenInput = document.getElementById('adm-gh-token');
  const savedToken = localStorage.getItem('copperdub_gh_token');
  if (tokenInput && savedToken) {
    tokenInput.value = savedToken;
  }
  renderAdminSidebar(animeToSelectId);
  adminModal.classList.add('active');
  adminModal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function closeAdminModal() {
  if (currentEditingAnime) {
    syncCurrentAnimeFromForm();
    updateSidebarItem(currentEditingAnime);
  }
  updateStats();
  renderHeroBanner();
  renderLatestEpisodeReminder();
  renderGrid();
  adminModal.classList.remove('active');
  adminModal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

let autoSaveTimer = null;
function showAutoSaveIndicator(text = '✓ Изменения сохранены на лету') {
  const badge = document.getElementById('adm-autosave-badge');
  const label = document.getElementById('adm-autosave-text');
  if (!badge || !label) return;
  label.textContent = text;
  badge.classList.remove('saving');
  clearTimeout(autoSaveTimer);
  autoSaveTimer = setTimeout(() => {
    label.textContent = 'Все изменения применяются на лету';
  }, 2200);
}

function updateSidebarItem(anime) {
  if (!anime) return;
  const item = adminAnimeList.querySelector(`.adm-list-item[data-anime-id="${anime.id}"]`);
  if (!item) return;
  const catIcon = anime.category === 'other' ? '👥' : '🔥';
  const epDone = (anime.episodes_done !== undefined && anime.episodes_done !== null) ? anime.episodes_done : (anime.episodes ? anime.episodes.length : 0);
  const totalStr = anime.episodes_total ? ` / ${anime.episodes_total}` : '';
  const titleEl = item.querySelector('.adm-list-title');
  const subEl = item.querySelector('.adm-list-sub');
  if (titleEl) titleEl.textContent = `${catIcon} ${anime.title_ru}`;
  if (subEl) subEl.textContent = `${epDone}${totalStr} серий • ${anime.status}`;
}

function highlightSidebarItem(animeId) {
  const items = adminAnimeList.querySelectorAll('.adm-list-item');
  items.forEach(el => {
    if (parseInt(el.dataset.animeId) === animeId) {
      el.classList.add('active');
    } else {
      el.classList.remove('active');
    }
  });
}

function syncCurrentAnimeFromForm() {
  if (!currentEditingAnime) return;

  const titleVal = admTitleRu.value.trim();
  if (titleVal) {
    currentEditingAnime.title_ru = titleVal;
  }
  currentEditingAnime.title_en = admTitleEn.value.trim();
  currentEditingAnime.category = admCategory.value;
  currentEditingAnime.format = admFormat.value.trim();
  currentEditingAnime.status = admStatus.value;
  
  const doneVal = admEpisodesDone ? parseInt(admEpisodesDone.value) : null;
  currentEditingAnime.episodes_total = parseInt(admEpisodesTotal.value) || 0;

  currentEditingAnime.poster_url = admPosterUrl.value.trim();
  currentEditingAnime.banner_url = admBannerUrl.value.trim();
  currentEditingAnime.cast = admCast.value.trim();
  currentEditingAnime.description = admDesc.value.trim();
  currentEditingAnime.notes = admNotes.value.trim();
  currentEditingAnime.aliases = admAliases.value.trim();

  // Read episodes from table
  const rows = admEpisodesTbody.querySelectorAll('tr[data-ep-idx]');
  const updatedEpisodes = [];
  rows.forEach((row, idx) => {
    const numInput = row.querySelector('.input-ep-num');
    const tgInput = row.querySelector('.input-ep-tg');
    const credInput = row.querySelector('.input-ep-credits');

    if (!numInput) return;

    const msgId = (tgInput && tgInput.value) ? parseInt(tgInput.value) : null;
    const postUrl = msgId ? `https://t.me/gygdub/${msgId}` : '';

    const origEp = (currentEditingAnime.episodes && currentEditingAnime.episodes[idx]) ? currentEditingAnime.episodes[idx] : {};

    updatedEpisodes.push({
      ...origEp,
      id: origEp.id || Date.now() + idx,
      anime_id: currentEditingAnime.id,
      episode_num: numInput.value.trim() || `${idx + 1} серия`,
      episode_order: idx + 1,
      title: numInput.value.trim() || `${idx + 1} серия`,
      cast_credits: credInput ? credInput.value.trim() : (currentEditingAnime.cast || 'Copper Dub'),
      tg_message_id: msgId,
      tg_post_url: postUrl
    });
  });

  if (rows.length > 0) {
    currentEditingAnime.episodes = updatedEpisodes;
  }
  currentEditingAnime.episodes_done = (doneVal !== null && !isNaN(doneVal)) ? doneVal : (currentEditingAnime.episodes ? currentEditingAnime.episodes.length : 0);
  
  if (admEpCount) {
    admEpCount.textContent = currentEditingAnime.episodes ? currentEditingAnime.episodes.length : 0;
  }
}

function renderAdminSidebar(selectId = null) {
  if (!allAnime || allAnime.length === 0) {
    adminAnimeList.innerHTML = `<div style="padding:16px; color:#888;">Нет тайтлов</div>`;
    return;
  }

  const activeId = selectId || (currentEditingAnime ? currentEditingAnime.id : allAnime[0].id);

  adminAnimeList.innerHTML = allAnime.map(a => {
    const isAct = a.id === activeId;
    const catIcon = a.category === 'other' ? '👥' : '🔥';
    const epDone = (a.episodes_done !== undefined && a.episodes_done !== null) ? a.episodes_done : (a.episodes ? a.episodes.length : 0);
    const totalStr = a.episodes_total ? ` / ${a.episodes_total}` : '';
    return `
      <div class="adm-list-item ${isAct ? 'active' : ''}" data-anime-id="${a.id}" onclick="selectAnimeForEdit(${a.id})">
        <div class="adm-list-title">${catIcon} ${a.title_ru}</div>
        <div class="adm-list-sub">${epDone}${totalStr} серий • ${a.status}</div>
      </div>
    `;
  }).join('');

  if (!currentEditingAnime || (selectId && currentEditingAnime.id !== selectId)) {
    selectAnimeForEdit(activeId);
  }
}

function selectAnimeForEdit(animeId) {
  // CRITICAL: Before switching to another anime, automatically sync current form edits!
  if (currentEditingAnime && currentEditingAnime.id !== animeId) {
    syncCurrentAnimeFromForm();
    updateSidebarItem(currentEditingAnime);
  }

  const anime = allAnime.find(a => a.id === animeId);
  if (!anime) return;

  currentEditingAnime = anime;
  highlightSidebarItem(anime.id);

  admAnimeId.value = anime.id;
  admTitleRu.value = anime.title_ru || '';
  admTitleEn.value = anime.title_en || '';
  admCategory.value = anime.category || 'main';
  admFormat.value = anime.format || 'ТВ-сериал';
  admStatus.value = anime.status || 'В процессе';
  if (admEpisodesDone) {
    admEpisodesDone.value = (anime.episodes_done !== undefined && anime.episodes_done !== null) ? anime.episodes_done : (anime.episodes ? anime.episodes.length : 0);
  }
  admEpisodesTotal.value = anime.episodes_total || '';

  admPosterUrl.value = anime.poster_url || '';
  admPosterPreview.src = anime.poster_url || '';

  admBannerUrl.value = anime.banner_url || '';
  admBannerPreview.src = anime.banner_url || '';

  admCast.value = anime.cast || '';
  admDesc.value = anime.description || '';
  admNotes.value = anime.notes || '';
  admAliases.value = anime.aliases || '';

  renderAdminEpisodesTable(anime.episodes || []);
  showAutoSaveIndicator('✓ Загружен тайтл');
}

function renderAdminEpisodesTable(episodes) {
  admEpCount.textContent = episodes.length;

  if (episodes.length === 0) {
    admEpisodesTbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:#888; padding:16px;">Серий пока нет. Нажмите «➕ Добавить серию».</td></tr>`;
    return;
  }

  admEpisodesTbody.innerHTML = episodes.map((ep, idx) => {
    return `
      <tr data-ep-idx="${idx}">
        <td>
          <input type="text" class="input-ep-num" value="${ep.episode_num || ''}" placeholder="1 серия">
        </td>
        <td>
          <input type="number" class="input-ep-tg" value="${ep.tg_message_id || ''}" placeholder="№ поста в ТГ (например 45)">
        </td>
        <td>
          <input type="text" class="input-ep-credits" value="${ep.cast_credits || ''}" placeholder="Каст / Заметки">
        </td>
        <td style="text-align:center;">
          <button type="button" class="btn-del-ep" onclick="adminDeleteEpisode(${idx})" title="Удалить серию">✕</button>
        </td>
      </tr>
    `;
  }).join('');
}

function adminDeleteEpisode(idx) {
  if (!currentEditingAnime || !currentEditingAnime.episodes) return;
  syncCurrentAnimeFromForm();
  currentEditingAnime.episodes.splice(idx, 1);
  renderAdminEpisodesTable(currentEditingAnime.episodes);
  syncCurrentAnimeFromForm();
  updateSidebarItem(currentEditingAnime);
  showAutoSaveIndicator('✓ Серия удалена');
}

function adminAddEpisodeRow() {
  if (!currentEditingAnime) return;
  syncCurrentAnimeFromForm();
  if (!currentEditingAnime.episodes) currentEditingAnime.episodes = [];

  const nextNum = currentEditingAnime.episodes.length + 1;
  currentEditingAnime.episodes.push({
    id: Date.now(),
    anime_id: currentEditingAnime.id,
    episode_num: `${nextNum} серия`,
    episode_order: nextNum,
    title: `${nextNum} серия`,
    cast_credits: currentEditingAnime.cast || 'Copper Dub',
    sub_credits: '',
    notes: '',
    tg_message_id: null,
    tg_post_url: '',
    file_size: 0
  });

  renderAdminEpisodesTable(currentEditingAnime.episodes);
  syncCurrentAnimeFromForm();
  updateSidebarItem(currentEditingAnime);
  showAutoSaveIndicator('✓ Серия добавлена');
}

function createNewAnimePrompt() {
  if (currentEditingAnime) {
    syncCurrentAnimeFromForm();
    updateSidebarItem(currentEditingAnime);
  }
  const newId = maxId(allAnime) + 1;
  const newAnime = {
    id: newId,
    slug: `anime-${newId}`,
    title_ru: 'Новый проект',
    title_en: '',
    category: currentCategory,
    format: 'ТВ-сериал',
    episodes_done: 0,
    episodes_total: 12,
    status: 'В процессе',
    cast: 'Copper Dub',
    poster_url: 'https://via.placeholder.com/300x420?text=Обложка',
    banner_url: '',
    description: '',
    notes: '',
    aliases: '',
    episodes: []
  };

  allAnime.unshift(newAnime);
  renderAdminSidebar(newId);
  showAutoSaveIndicator('✓ Новый тайтл создан');
}

function maxId(arr) {
  return arr.reduce((max, item) => item.id > max ? item.id : max, 0);
}

// Save edits to current anime (explicit button or form submit)
function saveCurrentAnimeForm(e) {
  if (e) e.preventDefault();
  if (!currentEditingAnime) return;

  syncCurrentAnimeFromForm();
  updateStats();
  renderHeroBanner();
  renderLatestEpisodeReminder();
  renderGrid();
  updateSidebarItem(currentEditingAnime);

  showAutoSaveIndicator('✓ Сохранено локально! Нажмите «💾 Опубликовать на GitHub»');
}

// Publish to GitHub directly via GitHub API
async function publishCatalogToGitHub() {
  if (currentEditingAnime) {
    syncCurrentAnimeFromForm();
    updateSidebarItem(currentEditingAnime);
  }
  updateStats();
  renderHeroBanner();
  renderLatestEpisodeReminder();
  renderGrid();

  const token = getGitHubToken();
  if (!token) {
    const entered = prompt('Для сохранения изменений на GitHub введите ваш Personal Access Token (ghp_...):\n(Он сохранится в вашем браузере в безопасности)');
    if (entered && entered.trim()) {
      localStorage.setItem('copperdub_gh_token', entered.trim());
      const input = document.getElementById('adm-gh-token');
      if (input) input.value = entered.trim();
    } else {
      alert('Публикация отменена: не указан токен.');
      return;
    }
  }
  const activeToken = getGitHubToken();

  const btn = document.getElementById('btn-admin-save-github');
  btn.textContent = '⏳ Публикация...';
  btn.disabled = true;

  try {
    const contentStr = JSON.stringify(allAnime, null, 2);
    // Base64 encode for UTF-8
    const bytes = new TextEncoder().encode(contentStr);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    const contentB64 = btoa(binary);

    // 1. Get SHA of current catalog.json from repo
    const getUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/catalog.json`;
    const checkRes = await fetch(getUrl, {
      headers: {
        'Authorization': `Bearer ${activeToken}`,
        'Accept': 'application/vnd.github+json'
      }
    });

    let sha = null;
    if (checkRes.ok) {
      const existing = await checkRes.json();
      sha = existing.sha;
    }

    // 2. Commit updated catalog.json
    const putRes = await fetch(getUrl, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${activeToken}`,
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: 'Admin Panel: Update catalog, posters and categories',
        content: contentB64,
        sha: sha
      })
    });

    if (putRes.ok) {
      showAutoSaveIndicator('🚀 Опубликовано на GitHub!');
      alert('🚀 УСПЕШНО ОПУБЛИКОВАНО НА GITHUB!\n\nВсе изменения по всем тайтлам сохранены. Cloudflare обновит сайт в течение нескольких секунд!');
    } else {
      const errData = await putRes.json();
      alert('Ошибка при публикации на GitHub: ' + (errData.message || 'Проверьте токен'));
    }
  } catch (err) {
    alert('Сетевая ошибка: ' + err.message);
  } finally {
    btn.textContent = '💾 Опубликовать на GitHub';
    btn.disabled = false;
  }
}

// Setup Event Listeners
function setupEventListeners() {
  // Category tabs
  catTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      catTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentCategory = tab.dataset.category;

      if (categoryDesc) {
        if (currentCategory === 'main') {
          categoryDesc.textContent = 'Релизы студии Copper Dub с участием Глеба (Uzapax).';
        } else {
          categoryDesc.textContent = 'Сольные релизы других ребят студии (Никита, Регина, Батырхан, Девочка лисичка).';
        }
      }

      renderGrid();
    });
  });

  // Filter pills
  filterPills.forEach(pill => {
    pill.addEventListener('click', () => {
      filterPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentFilter = pill.dataset.filter;
      renderGrid();
    });
  });

  // Search input
  searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value.trim().toLowerCase();
    renderGrid();
  });

  // Hero Play button
  const heroBtn = document.getElementById('hero-play-btn');
  if (heroBtn) {
    heroBtn.addEventListener('click', () => {
      if (allAnime.length > 0) openAnimeModal(1);
    });
  }

  // Modals Close handlers
  document.getElementById('modal-close-x').addEventListener('click', closeAnimeModal);
  document.getElementById('modal-close-backdrop').addEventListener('click', closeAnimeModal);

  document.getElementById('admin-close-x').addEventListener('click', closeAdminModal);
  document.getElementById('admin-close-backdrop').addEventListener('click', closeAdminModal);
  // Stealth / Secret Admin Openers:
  // 1. Hotkey: Ctrl + Shift + A (or Alt + A)
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey && e.shiftKey && (e.key === 'A' || e.key === 'a' || e.code === 'KeyA')) ||
        (e.altKey && (e.key === 'a' || e.key === 'A' || e.code === 'KeyA'))) {
      e.preventDefault();
      checkAdminAccessAndOpen();
    }
  });

  // 2. Secret triple-click on header logo
  let logoClicks = 0;
  let logoTimer = null;
  const headerLogo = document.getElementById('header-logo');
  if (headerLogo) {
    headerLogo.addEventListener('click', () => {
      logoClicks++;
      clearTimeout(logoTimer);
      if (logoClicks >= 3) {
        logoClicks = 0;
        checkAdminAccessAndOpen();
      } else {
        logoTimer = setTimeout(() => { logoClicks = 0; }, 1200);
      }
    });
  }

  // 3. Secret click on footer brand
  const footerBrand = document.getElementById('footer-brand');
  if (footerBrand) {
    footerBrand.addEventListener('click', () => {
      checkAdminAccessAndOpen();
    });
  }

  // 4. Check URL hash / query on startup
  if (window.location.hash === '#admin' || window.location.search.includes('admin')) {
    setTimeout(() => {
      checkAdminAccessAndOpen();
    }, 400);
  }

  const btnOpenAdmin = document.getElementById('btn-open-admin');
  if (btnOpenAdmin) {
    btnOpenAdmin.addEventListener('click', () => checkAdminAccessAndOpen());
  }

  // Edit in Admin button inside Anime details modal
  const btnEditThis = document.getElementById('btn-edit-this-anime');
  if (btnEditThis) {
    btnEditThis.addEventListener('click', () => {
      const id = currentAnime ? currentAnime.id : null;
      closeAnimeModal();
      checkAdminAccessAndOpen(id);
    });
  }

  // Admin form events & Reactive Auto-Save
  const adminAnimeForm = document.getElementById('admin-anime-form');
  if (adminAnimeForm) {
    adminAnimeForm.addEventListener('submit', saveCurrentAnimeForm);
    adminAnimeForm.addEventListener('input', () => {
      syncCurrentAnimeFromForm();
      if (currentEditingAnime) {
        updateSidebarItem(currentEditingAnime);
      }
      showAutoSaveIndicator('✓ Изменения учтены');
    });
    adminAnimeForm.addEventListener('change', () => {
      syncCurrentAnimeFromForm();
      if (currentEditingAnime) {
        updateSidebarItem(currentEditingAnime);
      }
      showAutoSaveIndicator('✓ Изменения применены');
    });
  }

  document.getElementById('btn-admin-save-github').addEventListener('click', publishCatalogToGitHub);
  document.getElementById('btn-admin-new-anime').addEventListener('click', createNewAnimePrompt);
  document.getElementById('btn-adm-add-episode').addEventListener('click', adminAddEpisodeRow);
  
  const btnLogout = document.getElementById('btn-admin-logout');
  if (btnLogout) {
    btnLogout.addEventListener('click', logoutAdmin);
  }

  // Live image previews in admin
  admPosterUrl.addEventListener('input', (e) => {
    admPosterPreview.src = e.target.value;
  });
  admBannerUrl.addEventListener('input', (e) => {
    admBannerPreview.src = e.target.value;
  });

  // Delete Anime button
  document.getElementById('btn-admin-delete-anime').addEventListener('click', () => {
    if (!currentEditingAnime) return;
    if (confirm(`Удалить тайтл «${currentEditingAnime.title_ru}» из каталога?`)) {
      allAnime = allAnime.filter(a => a.id !== currentEditingAnime.id);
      currentEditingAnime = null;
      updateStats();
      renderGrid();
      renderAdminSidebar();
      alert('Тайтл удален. Не забудьте нажать «💾 Опубликовать на GitHub», чтобы изменения применились на сайте.');
    }
  });



  // Close modals on Escape key
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeAnimeModal();
      closeAdminModal();
    }
  });
}
