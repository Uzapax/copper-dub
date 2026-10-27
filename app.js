// State
let allAnime = [];
let currentAnime = null;
let currentFilter = 'Все';
let searchQuery = '';

// Check if running inside Telegram WebApp
const isTelegramWebApp = Boolean(window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData);
const tg = window.Telegram?.WebApp;

// DOM Elements
const animeGrid = document.getElementById('anime-grid');
const filterPills = document.querySelectorAll('.pill');
const searchInput = document.getElementById('search-input');
const animeModal = document.getElementById('anime-modal');
const linkModal = document.getElementById('link-modal');

// Status elements
const tgStatusIndicator = document.getElementById('tg-status-indicator');
const tgStatusText = document.getElementById('tg-status-text');
const statAnimeCount = document.getElementById('stat-anime-count');
const statEpisodesCount = document.getElementById('stat-episodes-count');

// Modal Elements
const modalBanner = document.getElementById('modal-banner');
const modalPoster = document.getElementById('modal-poster');
const modalTitleRu = document.getElementById('modal-title-ru');
const modalTitleEn = document.getElementById('modal-title-en');
const modalStatusBadge = document.getElementById('modal-status-badge');
const modalFormatBadge = document.getElementById('modal-format-badge');
const modalProgressFill = document.getElementById('modal-progress-fill');
const modalProgressText = document.getElementById('modal-progress-text');
const modalCast = document.getElementById('modal-cast');
const modalDesc = document.getElementById('modal-desc');
const modalNotes = document.getElementById('modal-notes');
const episodesList = document.getElementById('episodes-list');
const episodesCountNum = document.getElementById('episodes-count-num');

document.addEventListener('DOMContentLoaded', () => {
  // If running in Telegram WebApp, setup TMA settings
  if (isTelegramWebApp && tg) {
    tg.ready();
    tg.expand();
    if (tg.enableClosingConfirmation) {
      tg.enableClosingConfirmation();
    }
    document.body.classList.add('inside-telegram');
  }

  initApp();
  setupEventListeners();
});

async function initApp() {
  await fetchStatus();
  await loadAnimeList();
}

// Fetch Status
async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    
    statAnimeCount.textContent = data.anime_count;
    statEpisodesCount.textContent = data.episodes_count;

    if (data.tg_connected) {
      tgStatusIndicator.className = 'status-indicator online';
      tgStatusText.textContent = `🟢 @${data.tg_channel} синхронизирован`;
    } else {
      tgStatusIndicator.className = 'status-indicator online';
      tgStatusText.textContent = `@${data.tg_channel}`;
    }
  } catch (err) {
    console.error('Error fetching status:', err);
  }
}

// Load All Anime
async function loadAnimeList() {
  try {
    let loaded = false;
    
    // 1. Try static catalog.json (instant for Cloudflare Pages and local)
    try {
      const resStatic = await fetch('./catalog.json');
      if (resStatic.ok) {
        allAnime = await resStatic.json();
        loaded = true;
      }
    } catch (e) {}

    // 2. Fallback to API if catalog.json not yet loaded
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
      // Auto-update stats from loaded catalog
      statAnimeCount.textContent = allAnime.length;
      let totalEps = 0;
      allAnime.forEach(a => {
        totalEps += (a.episodes ? a.episodes.length : (a.episodes_done || 0));
      });
      statEpisodesCount.textContent = totalEps;
      renderGrid();
    } else {
      animeGrid.innerHTML = `<div class="error-msg">Каталог пуст или загружается...</div>`;
    }
  } catch (err) {
    animeGrid.innerHTML = `<div class="error-msg">Не удалось загрузить каталог.</div>`;
    console.error('Failed to load anime:', err);
  }
}

// Render Anime Cards
function renderGrid() {
  const filtered = allAnime.filter(a => {
    const matchFilter = currentFilter === 'Все' || a.status === currentFilter;
    const matchSearch = !searchQuery || 
      a.title_ru.toLowerCase().includes(searchQuery) ||
      (a.title_en && a.title_en.toLowerCase().includes(searchQuery)) ||
      (a.aliases && a.aliases.toLowerCase().includes(searchQuery));
    return matchFilter && matchSearch;
  });

  if (filtered.length === 0) {
    animeGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px 0;">Ничего не найдено по запросу.</div>`;
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
          <img class="card-poster" src="${anime.poster_url || 'https://via.placeholder.com/300x420?text=Постер'}" alt="${anime.title_ru}" loading="lazy">
          <span class="card-badge ${badgeClass}">${anime.status}</span>
          <span class="card-format-tag">${anime.format}</span>
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
              <span>Серий: ${anime.episodes_done} / ${anime.episodes_total || anime.episodes_done}</span>
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

    modalPoster.src = currentAnime.poster_url || '';
    modalBanner.src = currentAnime.banner_url || currentAnime.poster_url || '';
    modalTitleRu.textContent = currentAnime.title_ru;
    modalTitleEn.textContent = currentAnime.title_en || '';
    modalStatusBadge.textContent = currentAnime.status;
    modalFormatBadge.textContent = currentAnime.format;
    modalCast.textContent = currentAnime.cast || 'Copper Dub';
    modalDesc.textContent = currentAnime.description || 'Описание отсутствует.';
    modalNotes.textContent = currentAnime.notes || '—';

    const percent = currentAnime.episodes_total > 0 
      ? Math.round((currentAnime.episodes_done / currentAnime.episodes_total) * 100) 
      : 100;
    modalProgressFill.style.width = `${percent}%`;
    modalProgressText.textContent = `${currentAnime.episodes_done} из ${currentAnime.episodes_total || currentAnime.episodes_done} серий (${percent}%)`;

    episodesCountNum.textContent = currentAnime.episodes ? currentAnime.episodes.length : 0;

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
    episodesList.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">Серии пока не добавлены.</div>`;
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
            <button class="btn btn-secondary btn-sm" onclick="openLinkModal(${ep.id}, '${ep.episode_num}')">
              🔗 Привязать
            </button>
          `}
          <button class="btn-icon-link" title="Изменить привязку" onclick="openLinkModal(${ep.id}, '${ep.episode_num}')">
            ✏️
          </button>
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

  // 1. If running inside Telegram Mini App: use native Telegram SDK!
  if (isTelegramWebApp && tg && tg.openTelegramLink) {
    tg.openTelegramLink(postUrl);
    return;
  }

  // 2. If in mobile / desktop browser:
  // Convert https://t.me/gygdub/123 to tg://resolve?domain=gygdub&post=123 for direct app launch
  const m = postUrl.match(/t\.me\/([^\/]+)\/(\d+)/);
  if (m) {
    const channel = m[1];
    const postId = m[2];
    const deepLink = `tg://resolve?domain=${channel}&post=${postId}`;
    
    // Try opening Telegram desktop/mobile app directly
    window.location.href = deepLink;
    
    // Fallback to web link in new tab after 500ms
    setTimeout(() => {
      window.open(postUrl, '_blank', 'noopener');
    }, 500);
  } else {
    window.open(postUrl, '_blank', 'noopener');
  }
}

function closeAnimeModal() {
  animeModal.classList.remove('active');
  animeModal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

// Link Modal Functions
function openLinkModal(epId, epNum) {
  document.getElementById('link-ep-id').value = epId;
  document.getElementById('link-modal-desc').innerHTML = `Укажите номер поста в @gygdub для серии <b>${epNum}</b>:`;
  document.getElementById('link-msg-id').value = '';
  linkModal.classList.add('active');
}

function closeLinkModal() {
  linkModal.classList.remove('active');
}

// Setup Event Listeners
function setupEventListeners() {
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
  document.getElementById('hero-play-btn').addEventListener('click', () => {
    if (allAnime.length > 0) {
      openAnimeModal(allAnime[0].id);
    }
  });

  // Modals Close handlers
  document.getElementById('modal-close-x').addEventListener('click', closeAnimeModal);
  document.getElementById('modal-close-backdrop').addEventListener('click', closeAnimeModal);

  document.getElementById('link-close-x').addEventListener('click', closeLinkModal);
  document.getElementById('link-close-backdrop').addEventListener('click', closeLinkModal);
  document.getElementById('btn-cancel-link').addEventListener('click', closeLinkModal);

  // Link Form Submit
  document.getElementById('link-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const epId = parseInt(document.getElementById('link-ep-id').value);
    const msgId = parseInt(document.getElementById('link-msg-id').value);

    try {
      const res = await fetch('/api/link-episode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ episode_id: epId, tg_message_id: msgId })
      });
      const data = await res.json();
      if (data.status === 'ok') {
        closeLinkModal();
        if (currentAnime) {
          const updated = await (await fetch(`/api/anime/${currentAnime.id}`)).json();
          currentAnime = updated;
          renderEpisodesList();
        }
      }
    } catch (err) {
      alert('Ошибка при сохранении: ' + err.message);
    }
  });

  // Sync button (Telegram Channel)
  document.getElementById('btn-sync-tg').addEventListener('click', async () => {
    const btn = document.getElementById('btn-sync-tg');
    btn.textContent = '⏳ Синхронизация...';
    btn.disabled = true;

    try {
      const res = await fetch('/api/sync', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'ok') {
        alert(`Синхронизация завершена!\nПросканировано постов: ${data.scanned}\nПривязано серий: ${data.added_or_updated}`);
        await loadAnimeList();
        if (currentAnime) {
          openAnimeModal(currentAnime.id);
        }
      } else {
        alert(data.message || 'Ошибка синхронизации');
      }
    } catch (err) {
      alert('Ошибка: ' + err.message);
    } finally {
      btn.textContent = '🔄 Обновить серии';
      btn.disabled = false;
    }
  });

  // Sync all anime with Shikimori
  const btnSyncShikimori = document.getElementById('btn-sync-shikimori');
  if (btnSyncShikimori) {
    btnSyncShikimori.addEventListener('click', async () => {
      btnSyncShikimori.textContent = '🌸 Загрузка...';
      btnSyncShikimori.disabled = true;
      try {
        const res = await fetch('/api/shikimori/sync-all', { method: 'POST' });
        const data = await res.json();
        alert(`Синхронизация с Shikimori завершена!\nОбновлено обложек: ${data.updated_anime_count}`);
        await loadAnimeList();
        if (currentAnime) {
          await openAnimeModal(currentAnime.id);
        }
      } catch (err) {
        alert('Ошибка при связи с Shikimori: ' + err.message);
      } finally {
        btnSyncShikimori.textContent = '🌸 Shikimori';
        btnSyncShikimori.disabled = false;
      }
    });
  }

  // Sync current anime with Shikimori
  const btnModalShikimori = document.getElementById('btn-modal-shikimori');
  if (btnModalShikimori) {
    btnModalShikimori.addEventListener('click', async () => {
      if (!currentAnime) return;
      btnModalShikimori.textContent = '🌸 Загрузка...';
      btnModalShikimori.disabled = true;
      try {
        const res = await fetch(`/api/anime/${currentAnime.id}/sync-shikimori`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'ok') {
          alert('Обложка и данные успешно обновлены с Shikimori!');
          await loadAnimeList();
          await openAnimeModal(currentAnime.id);
        } else {
          alert(data.detail || 'Не удалось найти на Shikimori');
        }
      } catch (err) {
        alert('Ошибка: ' + err.message);
      } finally {
        btnModalShikimori.textContent = '🌸 Обновить обложку и описание с Shikimori';
        btnModalShikimori.disabled = false;
      }
    });
  }

  // Close modals on Escape key
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeAnimeModal();
      closeLinkModal();
    }
  });
}
