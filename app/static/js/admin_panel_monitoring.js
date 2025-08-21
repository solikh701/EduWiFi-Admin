// admin_panel_monitoring.js
let page = 1;
let limit = 20;
let sort = 'id';
let order = 'desc';
let q = '';
let totalPages = 1;
let searchTimer = null;

// API dan sahifani yuklash
async function loadMonitoring() {
  try {
    const params = new URLSearchParams({ page, limit, sort, order });
    if (q) params.set('search', q);

    const res = await fetch(`/api/monitoring?${params.toString()}`);
    if (!res.ok) throw new Error('Server error: ' + res.status);

    const data = await res.json();

    // hisoblagich
    document.getElementById('monitoringCount').textContent = data.total ?? 0;
    totalPages = data.pages || 1;

    // jadval
    const tbody = document.getElementById('monitoringBody');
    const items = data.items || [];

    if (items.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" class="px-3 py-6 text-center text-gray-500 dark:text-gray-400">
            Ma'lumot topilmadi
          </td>
        </tr>`;
    } else {
      tbody.innerHTML = items.map(r => `
        <tr class="hover:bg-gray-50 dark:hover:bg-gray-900 transition">
          <td class="px-3 py-2">${r.id ?? ''}</td>
          <td class="px-3 py-2">${r.ts ?? ''}</td>
          <td class="px-3 py-2">${r.client_ip ?? ''}</td>
          <td class="px-3 py-2">${(r.mac ?? '-').toString().toUpperCase()}</td>
          <td class="px-3 py-2">${r.fio ? r.fio : '-'}</td>
          <td class="px-3 py-2">${r.phone_number ? r.phone_number : '-'}</td>
          <td class="px-3 py-2">${r.hostname ?? '-'}</td>
          <td class="px-3 py-2">${r.domain ?? '-'}</td>
          <td class="px-3 py-2">${r.protocol ?? ''}</td>
        </tr>
      `).join('');
    }

    // boshqaruvlar
    renderPagination();
    updateSortArrows();

    // URL holatini yangilash (ixtiyoriy)
    const urlParams = new URLSearchParams();
    urlParams.set('page', page);
    urlParams.set('limit', limit);
    urlParams.set('sort', sort);
    urlParams.set('order', order);
    if (q) urlParams.set('search', q);
    history.replaceState(null, '', `/admin_panel_monitoring?${urlParams.toString()}`);
  } catch (err) {
    console.error('Error loading monitoring:', err);
  }
}

// Pagination rendering
function renderPagination() {
  const container = document.getElementById('paginationButtons');
  container.innerHTML = '';

  const mkBtn = (label, disabled, onClick, active = false) => {
    const btn = document.createElement('button');
    btn.textContent = label;
    btn.disabled = !!disabled;
    btn.className = [
      'px-3 py-1 rounded-lg mx-1',
      active ? 'bg-indigo-500 text-white font-bold' : 'bg-gray-200 dark:bg-gray-700 hover:bg-indigo-400 dark:hover:bg-indigo-600',
      disabled ? 'opacity-50 cursor-not-allowed' : ''
    ].join(' ');
    if (!disabled) btn.addEventListener('click', onClick);
    return btn;
  };

  // « prev
  container.appendChild(mkBtn('«', page === 1, () => gotoPage(page - 1)));

  // pages
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) {
      container.appendChild(mkBtn(String(i), false, () => gotoPage(i), i === page));
    }
  } else if (page <= 4) {
    for (let i = 1; i <= 5; i++) {
      container.appendChild(mkBtn(String(i), false, () => gotoPage(i), i === page));
    }
    container.appendChild(ellipsis());
    container.appendChild(mkBtn(String(totalPages), false, () => gotoPage(totalPages)));
  } else if (page >= totalPages - 3) {
    container.appendChild(mkBtn('1', false, () => gotoPage(1)));
    container.appendChild(ellipsis());
    for (let i = totalPages - 4; i <= totalPages; i++) {
      container.appendChild(mkBtn(String(i), false, () => gotoPage(i), i === page));
    }
  } else {
    container.appendChild(mkBtn('1', false, () => gotoPage(1)));
    container.appendChild(ellipsis());
    container.appendChild(mkBtn(String(page - 1), false, () => gotoPage(page - 1)));
    container.appendChild(mkBtn(String(page), false, () => gotoPage(page), true));
    container.appendChild(mkBtn(String(page + 1), false, () => gotoPage(page + 1)));
    container.appendChild(ellipsis());
    container.appendChild(mkBtn(String(totalPages), false, () => gotoPage(totalPages)));
  }

  // » next
  container.appendChild(mkBtn('»', page === totalPages, () => gotoPage(page + 1)));
}

function ellipsis() {
  const span = document.createElement('span');
  span.textContent = '...';
  span.className = 'px-2 text-gray-500';
  return span;
}

function gotoPage(p) {
  if (p >= 1 && p <= totalPages) {
    page = p;
    loadMonitoring();
  }
}

// Sort-tirnoqlarni yangilash
function updateSortArrows() {
  document.querySelectorAll('#monitoringTable th.sort .sort-arrow').forEach(el => el.textContent = '⬍');
  const active = document.querySelector(`#monitoringTable th.sort[data-sort="${sort}"] .sort-arrow`);
  if (active) active.textContent = (order === 'asc' ? '▲' : '▼');
}

// === Event handlers ===
document.addEventListener('DOMContentLoaded', () => {
  // limit
  const limitSel = document.getElementById('limitSelect');
  if (limitSel) {
    limitSel.value = String(limit);
    limitSel.addEventListener('change', (e) => {
      limit = parseInt(e.target.value, 10) || 20;
      page = 1;
      loadMonitoring();
    });
  }

  // go to page
  const goBtn = document.getElementById('goBtn');
  const pageInput = document.getElementById('pageInput');
  if (goBtn && pageInput) {
    goBtn.addEventListener('click', () => {
      const p = parseInt(pageInput.value, 10);
      if (p >= 1 && p <= totalPages) gotoPage(p);
    });
  }

  // sort headers
  document.querySelectorAll('#monitoringTable th.sort').forEach(th => {
    th.addEventListener('click', () => {
      const s = th.dataset.sort;
      if (!s) return;
      if (sort === s) order = (order === 'asc' ? 'desc' : 'asc');
      else { sort = s; order = 'asc'; }
      page = 1;
      if (s === 'fio' || s === 'phone_number') {
        sortFrontend(s, order);
      } else {
        loadMonitoring(); 
      }
    });
  });

  function sortFrontend(field, order) {
    const tbody = document.getElementById('monitoringBody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort((a, b) => {
      const valA = (a.querySelector(`td:nth-child(${field === 'fio' ? 5 : 6})`).textContent || '').toLowerCase();
      const valB = (b.querySelector(`td:nth-child(${field === 'fio' ? 5 : 6})`).textContent || '').toLowerCase();
      if (valA < valB) return order === 'asc' ? -1 : 1;
      if (valA > valB) return order === 'asc' ? 1 : -1;
      return 0;
    });
    tbody.innerHTML = '';
    rows.forEach(r => tbody.appendChild(r));

    updateSortArrows();
  }

  // search (debounce)
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      clearTimeout(searchTimer);
      const val = (e.target.value || '').trim();
      searchTimer = setTimeout(() => {
        q = val;
        page = 1;
        loadMonitoring();
      }, 350);
    });
  }

  // initial load
  loadMonitoring();
});
