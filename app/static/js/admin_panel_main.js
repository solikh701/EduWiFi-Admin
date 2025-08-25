// /static/js/admin_panel_main.js
document.addEventListener('DOMContentLoaded', async function () {
  // === Session tekshiruvi ===
  const loggedInUser = localStorage.getItem('loggedInUser');
  const expirationTime = localStorage.getItem('loginExpiration');
  if (loggedInUser && expirationTime) {
    const currentTime = new Date().getTime();
    if (currentTime > expirationTime) {
      localStorage.removeItem('loggedInUser');
      localStorage.removeItem('loginExpiration');
      alert("Your session has expired. Please log in again.");
      window.location.href = '/admin_panel_login';
      return;
    }
  } else {
    window.location.href = '/admin_panel_login';
    return;
  }

  // === Profil menyu ===
  const profileBtn = document.getElementById('sidebarProfileBtn');
  const profileMenu = document.getElementById('profileMenu');
  if (profileBtn && profileMenu) {
    profileBtn.addEventListener('click', () => profileMenu.classList.toggle('hidden'));
    document.addEventListener('click', (e) => {
      if (!profileBtn.contains(e.target) && !profileMenu.contains(e.target)) {
        profileMenu.classList.add('hidden');
      }
    });
  }
  const logoutBtn = document.getElementById('sidebarLogoutBtn');
  if (logoutBtn) logoutBtn.onclick = () => { window.location.href = '/'; };

  // === WiFi menyu ===
  const wifiMenuBtn = document.getElementById('wifiMenuBtn');
  const wifiMenu = document.getElementById('wifiMenu');
  const wifiMenuArrow = document.getElementById('wifiMenuArrow');
  if (wifiMenuBtn && wifiMenu && wifiMenuArrow) {
    wifiMenuBtn.addEventListener('click', () => {
      wifiMenu.classList.toggle('hidden');
      wifiMenuArrow.classList.toggle('rotate-180');
    });
  }

  // === Ma'lumotlarni olish
  let dashboard = {};
  try {
    const res = await fetch('/api/dashboard');
    dashboard = await res.json();
    window.dashboard = dashboard; // boshqa skriptlar uchun
  } catch (e) {
    alert("Ma'lumotlarni yuklab bo'lmadi!");
    return;
  }

  // === Format helpers
  const fmtNumber = (n) => {
    n = Math.round(Number(n || 0));
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  };
  const fmtSom = (n) => `${fmtNumber(n)} so'm`;
  const titleCase = (s) => (s || '').toString().replace(/\b\w/g, c => c.toUpperCase());

  // === Kartkalar
  document.getElementById('totalConnections').textContent = dashboard.total_connections || 0;
  document.getElementById('totalWifi').textContent = dashboard.total_wifi || 0;
  document.getElementById('dailyIncome').textContent = fmtSom(dashboard.daily_income || 0);
  document.getElementById('monthlyIncome').textContent = fmtSom(dashboard.monthly_income || 0);

  // === Ulanishlar (Yil/Oy/Kun)
  const connCanvas = document.getElementById('connectionsChart').getContext('2d');
  let connectionsChart = new Chart(connCanvas, {
    type: 'bar',
    data: { labels: [], datasets: [{ label: 'Ulanishlar soni', data: [], backgroundColor: '#6366f1' }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
  });

  const applyActive = (btns, activeBtn) => {
    btns.forEach(b => {
      const isActive = b === activeBtn;
      b.classList.toggle('bg-indigo-50', isActive);
      b.classList.toggle('dark:bg-indigo-800', isActive);
      b.classList.toggle('text-indigo-600', isActive);
      b.classList.toggle('dark:text-indigo-300', isActive);
      b.classList.toggle('text-gray-600', !isActive);
      b.classList.toggle('dark:text-gray-200', !isActive);
    });
  };

  const updateConnections = (view = 'month') => {
    const series = (dashboard.connections_series && dashboard.connections_series[view]) || null;
    if (series) {
      connectionsChart.data.labels = series.labels;
      connectionsChart.data.datasets[0].data = series.data;
      connectionsChart.update();
      return;
    }
    const months = ['Yan','Fev','Mar','Apr','May','Iyn','Iyl','Avg','Sen','Okt','Noy','Dek'];
    connectionsChart.data.labels = months;
    connectionsChart.data.datasets[0].data = dashboard.connections_chart || [];
    connectionsChart.update();
  };
  const connBtns = Array.from(document.querySelectorAll('.connViewBtn'));
  connBtns.forEach(btn => btn.addEventListener('click', () => { applyActive(connBtns, btn); updateConnections(btn.dataset.view); }));
  updateConnections('month');

  // === Tushum dinamikasi (stacked bar, universitetlar bo'yicha)
  const dynCanvas = document.getElementById('incomeDynChart').getContext('2d');
  const palette = [
    '#6366f1','#10b981','#f59e0b','#ef4444','#3b82f6','#8b5cf6','#06b6d4',
    '#84cc16','#f97316','#ec4899','#22c55e','#a855f7','#14b8a6','#64748b'
  ];
  let incomeDynChart = new Chart(dynCanvas, {
    type: 'bar',
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      plugins: { legend: { display: true, position: 'bottom' } },
      scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }
    }
  });
  const updateIncomeDyn = (view = 'month') => {
    const block = dashboard.income_dynamic ? dashboard.income_dynamic[view] : null;
    if (!block) return;
    const labels = block.labels || [];
    const series = block.series || {};
    const domains = Object.keys(series).sort();
    incomeDynChart.data.labels = labels;
    incomeDynChart.data.datasets = domains.map((dom, idx) => ({
      label: titleCase(dom),
      data: series[dom] || [],
      backgroundColor: palette[idx % palette.length]
    }));
    incomeDynChart.update();
  };
  const incomeDynBtns = Array.from(document.querySelectorAll('.incomeDynBtn'));
  incomeDynBtns.forEach(btn => btn.addEventListener('click', () => { applyActive(incomeDynBtns, btn); updateIncomeDyn(btn.dataset.view); }));
  updateIncomeDyn('month');

  // === WiFi lar bo'yicha tushum — RASMDAGI kabi (stacked bar, Yil/Oy/Kun)
  const wifiChartCtx = document.getElementById('wifiIncomeChart').getContext('2d');
  let wifiIncomeChart = new Chart(wifiChartCtx, {
    type: 'bar',
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      plugins: { legend: { display: true, position: 'bottom' } },
      scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }
    }
  });
  const wifiNoData = document.getElementById('wifiNoData');
  if (wifiNoData) wifiNoData.style.pointerEvents = 'none';

  const updateWifiIncome = (view = 'month') => {
    const block = dashboard.income_dynamic ? dashboard.income_dynamic[view] : null;
    if (!block) return;
    const labels = block.labels || [];
    const series = block.series || {};
    const domains = Object.keys(series).sort();

    const datasets = domains.map((dom, idx) => ({
      label: titleCase(dom),
      data: series[dom] || [],
      backgroundColor: palette[idx % palette.length]
    }));

    wifiIncomeChart.data.labels = labels;
    wifiIncomeChart.data.datasets = datasets;
    wifiIncomeChart.update();

    // No data overlay
    const total = datasets.reduce((s, ds) => s + (ds.data || []).reduce((a,b)=>a+Number(b||0),0), 0);
    if (wifiNoData) {
      if (!labels.length || total === 0) {
        wifiNoData.classList.remove('hidden');
        wifiNoData.classList.add('flex');
      } else {
        wifiNoData.classList.add('hidden');
        wifiNoData.classList.remove('flex');
      }
    }
  };
  const wifiIncomeBtns = Array.from(document.querySelectorAll('.wifiIncomeBtn'));
  wifiIncomeBtns.forEach(btn => btn.addEventListener('click', () => { applyActive(wifiIncomeBtns, btn); updateWifiIncome(btn.dataset.view); }));
  const defaultWifiBtn = wifiIncomeBtns.find(b => b.dataset.view === 'month');
  if (defaultWifiBtn) applyActive(wifiIncomeBtns, defaultWifiBtn);
  updateWifiIncome('month');
  updateWifiIncome('month');

  // === Jadvallar
  document.getElementById('accountsTable').innerHTML = (dashboard.new_accounts || []).map(a =>
    `<tr>
      <td class="py-2 px-2">${a.id}</td>
      <td class="py-2 px-2">${a.date}</td>
      <td class="py-2 px-2">${a.user}</td>
      <td class="py-2 px-2">${a.account}</td>
      <td class="py-2 px-2">${a.username}</td>
    </tr>`
  ).join('');

  document.getElementById('transactionsTable').innerHTML = (dashboard.recent_transactions || []).map(t =>
    `<tr>
      <td class="py-2 px-2">${t.id}</td>
      <td class="py-2 px-2">${t.date}</td>
      <td class="py-2 px-2">${fmtSom(t.amount)}</td>
      <td class="py-2 px-2">${t.status}</td>
      <td class="py-2 px-2">${t.desc}</td>
    </tr>`
  ).join('');
});
