// static/js/wifi.js
(function () {
  'use strict';

  const grid   = document.getElementById('loginGrid');
  const toast  = document.getElementById('notifSuccess');
  const API    = '/api/wifi_data';

  function showToast(msg, ok = true) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.remove('hidden');
    toast.classList.toggle('bg-green-500', ok);
    toast.classList.toggle('bg-red-500', !ok);
    setTimeout(() => toast.classList.add('hidden'), 2000);
  }

  function titleCase(str) {
    str = String(str || '');
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  }

  function renderSkeleton(n = 8) {
    if (!grid) return;
    grid.innerHTML = '';
    for (let i = 0; i < n; i++) {
      const sk = document.createElement('div');
      sk.className = 'h-28 rounded-2xl bg-gray-100 dark:bg-gray-700 animate-pulse';
      grid.appendChild(sk);
    }
  }

  function renderCards(logins) {
    if (!grid) return;

    if (!Array.isArray(logins) || logins.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full text-center py-16 rounded-2xl bg-white dark:bg-gray-800 shadow">
          <div class="text-gray-500 dark:text-gray-400">Hech qanday login topilmadi</div>
        </div>`;
      return;
    }

    grid.innerHTML = logins.map(name => {
      const label = titleCase(name);
      const href  = '/link_login/' + encodeURIComponent(String(name));
      return `
        <a href="${href}"
           class="group relative overflow-hidden rounded-2xl border border-indigo-200/60
                  bg-white dark:bg-gray-800 dark:border-indigo-900/40
                  shadow-sm hover:shadow-lg hover:border-indigo-400 transition p-8">
          <div class="absolute -top-8 -right-8 w-24 h-24 rounded-full
                      bg-indigo-100 group-hover:bg-indigo-200
                      dark:bg-indigo-900/30 dark:group-hover:bg-indigo-900/50 transition"></div>
          <div class="relative flex items-center gap-3">
            <svg class="w-8 h-8 text-indigo-600 dark:text-indigo-300" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 3l8 4-8 4-8-4 8-4zm0 8l8 4-8 4-8-4 8-4z"></path>
            </svg>
            <h4 class="text-3xl font-extrabold tracking-wide
                       text-indigo-700 dark:text-indigo-200">${label}</h4>
          </div>
          <p class="mt-3 text-sm text-gray-500 dark:text-gray-400">O‘tish uchun bosing</p>
        </a>
      `;
    }).join('');
  }

  async function loadLogins() {
    try {
      renderSkeleton();
      const res = await fetch(API, { method: 'GET', headers: { 'Accept': 'application/json' } });
      if (!res.ok) throw new Error('Server xatosi: ' + res.status);
      const json = await res.json();
      let arr = Array.isArray(json?.logins) ? json.logins : [];
      // uniq + alfavit
      arr = [...new Set(arr.map(s => String(s).trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'uz'));
      renderCards(arr);
      showToast('Yuklandi', true);
    } catch (e) {
      console.error(e);
      renderCards([]);
      showToast("Ma'lumotlarni yuklashda xatolik", false);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const loggedInUser = localStorage.getItem('loggedInUser');
    const expirationTime = localStorage.getItem('loginExpiration');

    if (loggedInUser && expirationTime) {
        const currentTime = new Date().getTime();

        if (currentTime > expirationTime) {
            localStorage.removeItem('loggedInUser');
            localStorage.removeItem('loginExpiration');
            alert("Your session has expired. Please log in again.");
            window.location.href = '/admin_panel_login';
        }
    } else {
        window.location.href = '/admin_panel_login';
    }
    window.loadLogins = loadLogins; // "Yangilash" tugmasi uchun
    loadLogins();
  });
})();
