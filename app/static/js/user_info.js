document.addEventListener('DOMContentLoaded', () => {
  const loggedInUser   = localStorage.getItem('loggedInUser');
  const expirationTime = localStorage.getItem('loginExpiration');
  if (!loggedInUser || !expirationTime || Date.now() > +expirationTime) {
    localStorage.clear();
    alert("Your session has expired. Please log in again.");
    return window.location.href = '/admin_panel_login';
  }

  const tbody          = document.getElementById('sessionsTbody');
  const prevBtn        = document.getElementById('prevBtn');
  const nextBtn        = document.getElementById('nextBtn');
  const pageInfo       = document.getElementById('pageInfo');
  const pageSizeSelect = document.getElementById('pageSizeSelect');
  const searchInput    = document.getElementById('searchInput');
  const gotoInput      = document.getElementById('gotoInput');
  const goBtn          = document.getElementById('goBtn');

  const topUserIdEl = document.getElementById('topUserId');
  const chipMAC     = document.getElementById('chipMAC');
  const chipFIO     = document.getElementById('chipFIO');
  const chipPhone   = document.getElementById('chipPhone');

  const urlParams  = new URLSearchParams(window.location.search);
  const userId     = urlParams.get('id');
  let currentPage  = 1;
  let totalPages   = 1;
  let perPage      = Number(localStorage.getItem('user_sessions_limit')) || 20;
  let searchTerm   = '';

  // NEW: sort state
  let sortBy  = localStorage.getItem('user_sessions_sort_by')  || 'date';
  let sortDir = localStorage.getItem('user_sessions_sort_dir') || 'desc'; // 'asc' | 'desc'

  pageSizeSelect.value = perPage;

  // Theme toggle
  (function themeInit(){
    const btn  = document.getElementById('themeToggle');
    const path = document.getElementById('themeIconPath');
    function setTheme(mode){
      if(mode==='dark'){
        document.documentElement.classList.add('dark');
        localStorage.setItem('theme','dark');
        path.setAttribute('d','M21 12.79A9 9 0 1111.21 3a7 7 0 109.79 9.79z');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('theme','light');
        path.setAttribute('d','M12 3v1m0 16v1m8.66-13.66l-.71.71M4.05 19.95l-.71.71M21 12h-1M4 12H3m16.66 4.95l-.71-.71M4.05 4.05l-.71-.71M12 7a5 5 0 100 10 5 5 0 000-10z');
      }
    }
    setTheme(localStorage.getItem('theme') || (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'));
    if (btn) btn.onclick = ()=> setTheme(document.documentElement.classList.contains('dark') ? 'light' : 'dark');
  })();

  // Profile menu
  (function profileMenu(){
    const btn = document.getElementById('sidebarProfileBtn');
    const menu = document.getElementById('profileMenu');
    const logout = document.getElementById('sidebarLogoutBtn');
    if (btn && menu) btn.onclick = () => menu.classList.toggle('hidden');
    if (logout) logout.onclick = () => {
      localStorage.removeItem('loggedInUser');
      localStorage.removeItem('loginExpiration');
      window.location.href = '/admin_panel_login';
    };
  })();

  document.getElementById('backBtn').onclick = () => {
    window.location.href = `/admin_panel_details?id=${encodeURIComponent(userId)}`;
  };

  if (!userId) {
    console.error('User ID not found in URL');
    return;
  }

  // Header chips
  fetch(`/api/users/${userId}`)
    .then(r => r.ok ? r.json() : Promise.reject(r.status))
    .then(user => {
      topUserIdEl.textContent = user.id ?? '—';
      chipMAC.textContent   = user.MAC || 'MAC: —';
      chipFIO.textContent   = user.fio || '—';
      chipPhone.textContent = user.phone_number || '—';
    })
    .catch(console.error);

  function buildQuery(){
    const p = new URLSearchParams({
      page: currentPage,
      per_page: perPage,
      search: searchTerm,
      sort_by: sortBy,
      sort_dir: sortDir
    });
    return p.toString();
  }

  function statusText(raw){
    if (raw === 'AKTIV') return 'AKTIV';
    if (raw === 'NOAKTIV') return "MUDDATI O'TGAN";
    return '';
  }

  function updateSortUI(){
    document.querySelectorAll('th[data-key] .sort-arrow').forEach(s => s.textContent = '');
    const span = document.querySelector(`th[data-key="${sortBy}"] .sort-arrow`);
    if (span) span.textContent = sortDir === 'asc' ? '▲' : '▼';
  }

  async function fetchPage(){
    try{
      const res = await fetch(`/api/users/${userId}/authorizations?${buildQuery()}`);
      if (!res.ok) throw new Error(`Failed to fetch: ${res.status}`);
      const data = await res.json();

      currentPage = data.page;
      totalPages  = data.total_pages;

      tbody.innerHTML = '';
      (data.items || []).forEach(item => {
        const tr = document.createElement('tr');
        const active = item.status === 'AKTIV';
        tr.className = `transition ${active ? 'bg-green-50 dark:bg-green-900/30' : 'bg-transparent'}`;
        tr.innerHTML = `
          <td class="px-3 py-2">${(item.hostname || item.ssid || '').toString()}</td>
          <td class="px-3 py-2 whitespace-nowrap">${item.date || ''}</td>
          <td class="px-3 py-2">${item.tarif || ''}</td>
          <td class="px-3 py-2">${item.price || ''}</td>
          <td class="px-3 py-2">
            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold
                         ${active
                            ? 'bg-green-100 text-green-700 dark:bg-green-800 dark:text-green-200'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-100'}">
              ${statusText(item.status)}
            </span>
          </td>
        `;
        tbody.appendChild(tr);
      });

      prevBtn.disabled = currentPage <= 1;
      nextBtn.disabled = currentPage >= totalPages;
      pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
      gotoInput.value = currentPage;

      updateSortUI();
    } catch (e){
      console.error(e);
      tbody.innerHTML = `<tr><td class="px-3 py-4 text-red-600 dark:text-red-400" colspan="5">
        Ma'lumotlarni olishda xatolik yuz berdi.
      </td></tr>`;
    }
  }

  // events
  prevBtn.onclick = () => { if (currentPage > 1) { currentPage--; fetchPage(); } };
  nextBtn.onclick = () => { if (currentPage < totalPages) { currentPage++; fetchPage(); } };
  pageSizeSelect.onchange = (e) => {
    perPage = Number(e.target.value) || 20;
    localStorage.setItem('user_sessions_limit', perPage);
    currentPage = 1;
    fetchPage();
  };
  let searchTimer = null;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      searchTerm = e.target.value.trim();
      currentPage = 1;
      fetchPage();
    }, 300);
  });
  goBtn.onclick = () => {
    const p = Number(gotoInput.value);
    if (Number.isInteger(p) && p >= 1 && p <= totalPages){
      currentPage = p; fetchPage();
    } else {
      alert(`Iltimos 1 dan ${totalPages} gacha son kiriting.`);
    }
  };

  // NEW: header click -> sort toggle
  document.querySelectorAll('thead th[data-key]').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.dataset.key;
      if (sortBy === key) {
        sortDir = (sortDir === 'asc') ? 'desc' : 'asc';
      } else {
        sortBy  = key;
        sortDir = 'asc'; // first click asc
      }
      localStorage.setItem('user_sessions_sort_by',  sortBy);
      localStorage.setItem('user_sessions_sort_dir', sortDir);
      currentPage = 1;
      fetchPage();
    });
  });

  // WebSocket for this page (room: user_sessions:<id>)
  try {
    if (typeof io !== 'undefined') {
      let debounceId;
      const safeRefresh = () => {
        clearTimeout(debounceId);
        debounceId = setTimeout(()=>{ if(!document.hidden) fetchPage(); }, 250);
      };
      const socket = io('/updates', {
        transports: ['websocket','polling'],
        query: { page: `user_sessions:${userId}` }
      });
      socket.on('refresh', (msg) => {
        if (!msg || (msg.page && msg.page !== `user_sessions:${userId}`)) return;
        safeRefresh();
      });
      window.addEventListener('beforeunload', () => { try { socket.disconnect(); } catch(e){} });
    }
  } catch(e) { console.warn('WS disabled:', e); }

  fetchPage();
});
