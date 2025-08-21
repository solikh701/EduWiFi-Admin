// ====== State ======
let currentPage = 1;
let limit = 20;
let totalPages = 1;
let usersData = [];
let currentSortKey = null;   // e.g. 'id', 'MAC', 'fio', ...
let currentSortDir = 'asc';  // 'asc' | 'desc'
let searchTimeout = null;

// ====== Utils ======
function isAdmin(lastTariffLimit) {
  return /^\d+$/.test(String(lastTariffLimit || '').trim());
}

// dd-mm-YYYY HH:MM:SS -> Date
function parseDMYDate(s) {
  if (!s || typeof s !== 'string') return null;
  const [dmy, hms] = s.split(' ');
  if (!dmy) return null;
  const [d, m, y] = dmy.split('-').map(n => parseInt(n, 10));
  let hh = 0, mm = 0, ss = 0;
  if (hms) {
    const t = hms.split(':').map(n => parseInt(n, 10));
    hh = t[0] || 0; mm = t[1] || 0; ss = t[2] || 0;
  }
  // Months in JS: 0..11
  const dt = new Date(y, (m || 1) - 1, d || 1, hh, mm, ss);
  return isNaN(dt.getTime()) ? null : dt;
}

function cmp(a, b) { if (a > b) return 1; if (a < b) return -1; return 0; }

// ====== Search (live debounce) ======
const searchInputEl = document.getElementById('searchInput');
if (searchInputEl) {
  searchInputEl.addEventListener('input', function (e) {
    clearTimeout(searchTimeout);
    const val = e.target.value.trim();
    if (!val) {
      fetchUsers(); // reset to default
      return;
    }
    searchTimeout = setTimeout(() => searchUsers(val), 300);
  });
}

async function searchUsers(term) {
  try {
    const response = await fetch(`/api/users/search?search=${encodeURIComponent(term)}`);
    if (!response.ok) throw new Error(`Server returned ${response.status}`);
    const data = await response.json();

    // We sort client-side as the user clicks headers
    usersData = data.users.slice();
    renderUserTable();

    // Update count + hide pagination when searching
    document.getElementById('userCount').textContent = data.total;
    document.getElementById('paginationButtons').innerHTML = '';
  } catch (err) {
    console.error('Search error:', err);
    alert('Foydalanuvchilarni qidirishda xatolik yuz berdi.');
  }
}

// ====== Fetch & Pagination ======
async function fetchUsers() {
  try {
    limit = Number(localStorage.getItem('admin_users_limit')) || 20;
    const urlParams = new URLSearchParams(window.location.search);
    currentPage = Number(urlParams.get('page')) || Number(localStorage.getItem('admin_users_currentPage')) || 1;

    const response = await fetch(`/api/users?page=${currentPage}&limit=${limit}`);
    if (!response.ok) throw new Error("Error fetching users:" + response.status);

    const data = await response.json();
    totalPages = Math.ceil(data.total / limit);
    usersData = data.users.slice(); // copy
    renderUserTable();

    setupPagination();
    document.getElementById('userCount').textContent = data.total;

  } catch (error) {
    console.error('Error fetching user data:', error);
  }
}

function setupPagination() {
  const container = document.getElementById('paginationButtons');
  container.innerHTML = '';

  const makeButton = (text, disabled, onClick) => {
    const btn = document.createElement('button');
    btn.textContent = text;
    btn.disabled = disabled;
    btn.className = "px-3 py-1 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-indigo-400 dark:hover:bg-indigo-600 mx-1";
    btn.onclick = onClick;
    return btn;
  };

  container.appendChild(makeButton('«', currentPage === 1, () => {
    if (currentPage > 1) {
      const prevPage = currentPage - 1;
      localStorage.setItem('admin_users_currentPage', prevPage);
      window.location.href = `/admin_panel_users?page=${prevPage}`;
    }
  }));

  const pages = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else if (currentPage <= 4) {
    pages.push(1, 2, 3, 4, 5, '...', totalPages);
  } else if (currentPage >= totalPages - 3) {
    pages.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
  } else {
    pages.push(1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages);
  }

  for (const p of pages) {
    if (p === '...') {
      const span = document.createElement('span');
      span.textContent = '...';
      span.className = "mx-1";
      container.appendChild(span);
    } else {
      const btn = makeButton(p, false, () => {
        localStorage.setItem('admin_users_currentPage', p);
        window.location.href = `/admin_panel_users?page=${p}`;
      });
      if (p === currentPage) btn.classList.add('active-page');
      container.appendChild(btn);
    }
  }

  container.appendChild(makeButton('»', currentPage === totalPages, () => {
    if (currentPage < totalPages) {
      const nextPage = currentPage + 1;
      localStorage.setItem('admin_users_currentPage', nextPage);
      window.location.href = `/admin_panel_users?page=${nextPage}`;
    }
  }));

  document.getElementById('pageInput').value = currentPage;
}

function goToPage() {
  const page = parseInt(document.getElementById('pageInput').value, 10);
  if (page >= 1 && page <= totalPages) {
    localStorage.setItem('admin_users_currentPage', page);
    window.location.href = `/admin_panel_users?page=${page}`;
  } else {
    alert(`Iltimos 1 dan ${totalPages} gacha son kiriting.`);
  }
}
window.goToPage = goToPage;

// ====== Sorting ======
function updateSortArrows() {
  document.querySelectorAll('#usersTable th.sortable .sort-arrow').forEach(span => {
    span.textContent = '';
  });
  if (currentSortKey) {
    const th = document.querySelector(`#usersTable th.sortable[data-key="${currentSortKey}"] .sort-arrow`);
    if (th) th.textContent = currentSortDir === 'asc' ? '▲' : '▼';
  }
}

function attachTheadSortHandlers() {
  document.querySelectorAll('#usersTable th.sortable').forEach(th => {
    th.addEventListener('click', function () {
      const key = th.dataset.key;
      if (!key) return;
      if (currentSortKey === key) {
        currentSortDir = (currentSortDir === 'asc') ? 'desc' : 'asc';
      } else {
        currentSortKey = key;
        currentSortDir = 'asc';
      }
      renderUserTable();
    });
  });
}

// ====== Render ======
function renderUserTable() {
  // sort client-side
  if (currentSortKey) {
    usersData.sort((a, b) => {
      let v1, v2;

      if (currentSortKey === 'activated_by') {
        v1 = isAdmin(a.last_tariff_limit) ? 'Admin' : 'Portal';
        v2 = isAdmin(b.last_tariff_limit) ? 'Admin' : 'Portal';
        // Admin > Portal (so asc: Portal,Admin)
        const rank = (v) => (v === 'Admin' ? 2 : 1);
        return currentSortDir === 'asc' ? rank(v1) - rank(v2) : rank(v2) - rank(v1);
      }

      v1 = a[currentSortKey];
      v2 = b[currentSortKey];

      // numeric id
      if (currentSortKey === 'id') {
        const n1 = Number(v1) || 0, n2 = Number(v2) || 0;
        return currentSortDir === 'asc' ? n1 - n2 : n2 - n1;
      }

      // status rank
      if (currentSortKey === 'authorization_activeness') {
        const rank = (s) => (s === 'AKTIV' ? 2 : (s === 'NOAKTIV' ? 1 : 0));
        const r1 = rank(v1), r2 = rank(v2);
        return currentSortDir === 'asc' ? r1 - r2 : r2 - r1;
      }

      // dates
      if (currentSortKey === 'last_authorization' || currentSortKey === 'last_authorization_limit') {
        const d1 = parseDMYDate(v1) || new Date(0);
        const d2 = parseDMYDate(v2) || new Date(0);
        return currentSortDir === 'asc' ? d1 - d2 : d2 - d1;
      }

      // strings
      v1 = v1 == null ? '' : String(v1);
      v2 = v2 == null ? '' : String(v2);
      return currentSortDir === 'asc' ? v1.localeCompare(v2) : v2.localeCompare(v1);
    });
  }

  const tbody = document.getElementById('userTableBody');
  tbody.innerHTML = '';

  usersData.forEach(user => {
    const act = user.authorization_activeness;
    const showDates = !(act === 'NOINTERNET' || act === 'NOINTERNETPAY' || act == null);

    const row = document.createElement('tr');
    row.className = "hover:bg-indigo-50 dark:hover:bg-indigo-900 transition rounded-xl shadow";

    const statusClass =
      act === 'AKTIV' ? 'status-aktiv' :
      act === 'NOAKTIV' ? 'status-noaktiv' : 'status-other';

    const activatedBy = isAdmin(user.last_tariff_limit) ? 'Admin' : 'Portal';

    row.innerHTML = `
      <td class="px-4 py-3 font-bold text-gray-800 dark:text-gray-100">${user.id}</td>
      <td class="px-4 py-3"><span class="status-badge ${statusClass}">${showDates ? (act ?? '-') : '-'}</span></td>
      <td class="px-4 py-3 font-mono text-indigo-700 dark:text-indigo-300">${user.MAC}</td>
      <td class="px-4 py-3">${user.fio}</td>
      <td class="px-4 py-3">${user.phone_number}</td>
      <td class="px-4 py-3">${user.role}</td>
      <td class="px-4 py-3">${showDates ? (user.last_authorization ?? '-') : '-'}</td>
      <td class="px-4 py-3">${showDates ? (user.last_authorization_limit ?? '-') : '-'}</td>
      <td class="px-4 py-3">${activatedBy}</td>
      <td class="px-4 py-3 text-center">
          <button onclick="viewDetails(${user.id});event.stopPropagation();" 
                  class="p-1 text-indigo-600 dark:text-indigo-300 hover:text-indigo-800 dark:hover:text-indigo-100"
                  title="Batafsil">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10"></circle>
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 12H9m0 0l3-3m-3 3l3 3"></path>
              </svg>
          </button>
      </td>
    `;

    tbody.appendChild(row);
  });

  updateSortArrows();
}

// ====== Actions ======
function viewDetails(userId) {
  window.location.href = `/admin_panel_details?id=${userId}`;
}
window.viewDetails = viewDetails;

function openAddUserModal() {
  document.getElementById('addUserModal').classList.remove('hidden');
  document.getElementById('modalBackdrop').classList.remove('hidden');
}
function closeAddUserModal() {
  document.getElementById('addUserModal').classList.add('hidden');
  document.getElementById('modalBackdrop').classList.add('hidden');
}
window.openAddUserModal = openAddUserModal;
window.closeAddUserModal = closeAddUserModal;

// ====== Init ======
document.addEventListener('DOMContentLoaded', () => {
  // Session check
  const loggedInUser = localStorage.getItem('loggedInUser');
  const expirationTime = localStorage.getItem('loginExpiration');

  if (!loggedInUser || !expirationTime || Date.now() > +expirationTime) {
    localStorage.clear();
    alert("Your session has expired. Please log in again.");
    return (window.location.href = '/admin_panel_login');
  }

  // Restore state
  const urlParams = new URLSearchParams(window.location.search);
  currentPage = Number(urlParams.get('page')) || Number(localStorage.getItem('admin_users_currentPage')) || 1;
  localStorage.setItem('admin_users_currentPage', currentPage);
  limit = Number(localStorage.getItem('admin_users_limit')) || 20;
  const limitSelect = document.getElementById('limitSelect');
  if (limitSelect) {
    limitSelect.value = String(limit);
    limitSelect.addEventListener('change', e => {
      limit = parseInt(e.target.value, 10);
      localStorage.setItem('admin_users_limit', limit);
      currentPage = 1;
      fetchUsers();
    });
  }

  // Sort handlers
  attachTheadSortHandlers();
  updateSortArrows();

  // Add user form (optional endpoint)
  const addForm = document.getElementById('addUserForm');
  if (addForm) {
    addForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const userType = document.getElementById('userType').value;
      const userFullName = document.getElementById('userFullName').value;
      const userPhone = document.getElementById('userPhone').value;
      const userTarifMinutes = document.getElementById('userTarifMinutes').value;
      try {
        const resp = await fetch('/api/add_user', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ userType, userFullName, userPhone, userTarifMinutes }),
        });
        if (resp.ok) {
          closeAddUserModal();
          fetchUsers();
        } else {
          alert("Foydalanuvchini qo'shishda xatolik yuz berdi.");
        }
      } catch (err) {
        console.error('Error adding user:', err);
      }
    });
  }

  // WebSocket for this page (room: 'users')
  setupUsersSocket();

  // First load
  fetchUsers();
});

// ====== WebSocket (Socket.IO) ======
let usersSocket;
function setupUsersSocket() {
  try {
    if (typeof io === 'undefined') return;
    if (usersSocket) return;
    let debounceId;
    const safeRefresh = () => {
      clearTimeout(debounceId);
      debounceId = setTimeout(() => { if (!document.hidden) fetchUsers(); }, 250);
    };
    usersSocket = io('/updates', { transports: ['websocket','polling'], query: { page: 'users' } });
    usersSocket.on('connect', () => console.debug('[WS] users connected'));
    usersSocket.on('refresh', (msg) => {
      if (!msg || (msg.page && msg.page !== 'users')) return;
      safeRefresh();
    });
    window.addEventListener('beforeunload', () => { try { usersSocket.disconnect(); } catch(e) {} });
  } catch (e) {
    console.warn('WS disabled:', e);
  }
}
