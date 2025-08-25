(function(){
  const root = document.getElementById('pageRoot');
  if(!root) return;
  const UNI = root.dataset.university;

  const elTotalConn  = document.getElementById('totalConnections');
  const elDailyInc   = document.getElementById('dailyIncome');
  const elMonthlyInc = document.getElementById('monthlyIncome');

  const accountsTable     = document.getElementById('accountsTable');
  const transactionsTable = document.getElementById('transactionsTable');

  const btnUsers = document.getElementById('seeAllUsers');
  const btnTx    = document.getElementById('seeAllTransactions');
  if (btnUsers) btnUsers.onclick = () => location.href = `/link_login/${UNI}/users`;
  if (btnTx)    btnTx.onclick    = () => location.href = `/link_login/${UNI}/transactions`;

  // ==== helpers ====
  const fmtNumber = (n) => {
    n = Math.round(Number(n || 0));
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  };
  const fmtSom = (n) => `${fmtNumber(n)} so'm`;
  const titleCase = (s) => (s || '').toString().replace(/\b\w/g, c => c.toUpperCase());

  // ==== load ====
  async function loadDashboard(){
    const res = await fetch(`/api/link_login/${encodeURIComponent(UNI)}/dashboard`);
    const data = await res.json();
    window.dashboard = data; // agar kerak bo'lsa

    // cards
    elTotalConn.textContent  = data.total_connections ?? 0;
    elDailyInc.textContent   = fmtSom(data.daily_income ?? 0);
    elMonthlyInc.textContent = fmtSom(data.monthly_income ?? 0);

    // mini tables
    accountsTable.innerHTML = (data.new_accounts||[]).map(a=>`
      <tr class="border-b dark:border-gray-700">
        <td class="py-2 px-2">${a.id ?? ''}</td>
        <td class="py-2 px-2">${a.date ?? ''}</td>
        <td class="py-2 px-2">${a.user ?? ''}</td>
        <td class="py-2 px-2">${a.account ?? ''}</td>
        <td class="py-2 px-2">${a.username ?? ''}</td>
      </tr>`).join('');

    transactionsTable.innerHTML = (data.recent_transactions||[]).map(t=>`
      <tr class="border-b dark:border-gray-700">
        <td class="py-2 px-2">${t.id ?? ''}</td>
        <td class="py-2 px-2">${t.date ?? ''}</td>
        <td class="py-2 px-2">${fmtSom(t.amount ?? 0)}</td>
        <td class="py-2 px-2">${t.status ?? ''}</td>
        <td class="py-2 px-2">${t.desc ?? ''}</td>
      </tr>`).join('');

    // ===== Charts =====

    // Ulanishlar (Yil/Oy/Kun)
    const connCtx = document.getElementById('connectionsChart').getContext('2d');
    let connectionsChart = new Chart(connCtx, {
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
      const series = (data.connections_series && data.connections_series[view]) || null;
      if (!series) return;
      connectionsChart.data.labels = series.labels;
      connectionsChart.data.datasets[0].data = series.data;
      connectionsChart.update();
    };

    const connBtns = Array.from(document.querySelectorAll('.connViewBtn'));
    connBtns.forEach(btn => btn.addEventListener('click', () => { applyActive(connBtns, btn); updateConnections(btn.dataset.view); }));
    // default
    const defaultConnBtn = connBtns.find(b => b.dataset.view === 'month');
    if (defaultConnBtn) applyActive(connBtns, defaultConnBtn);
    updateConnections('month');

    // WiFi lar bo‘yicha tushum (universitet kesimida, Yil/Oy/Kun) — stacked bar (1 dataset)
    const palette = ['#6366f1','#10b981','#f59e0b','#ef4444','#3b82f6','#8b5cf6','#06b6d4','#84cc16','#f97316','#ec4899','#22c55e','#a855f7','#14b8a6','#64748b'];

    const wifiCtx = document.getElementById('wifiIncomeChart').getContext('2d');
    let wifiIncomeChart = new Chart(wifiCtx, {
      type: 'bar',
      data: { labels: [], datasets: [] },
      options: {
        responsive: true,
        plugins: { legend: { display: true, position: 'bottom' } },
        scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }
      }
    });
    const wifiNoData = document.getElementById('wifiNoData');

    function updateWifiIncome(view = 'month'){
      const block = data.income_dynamic ? data.income_dynamic[view] : null;
      if (!block) return;
      const labels = block.labels || [];
      const series = block.series || {};
      const keys = Object.keys(series);
      const datasets = keys.map((k,idx)=>({
        label: titleCase(k),
        data: series[k] || [],
        backgroundColor: palette[idx % palette.length]
      }));
      // reset datasets to avoid ghost state
      wifiIncomeChart.data.labels = labels;
      wifiIncomeChart.data.datasets.length = 0;
      datasets.forEach(ds => wifiIncomeChart.data.datasets.push(ds));
      wifiIncomeChart.update('none');

      const total = datasets.reduce((s, ds) => s + (ds.data || []).reduce((a,b)=>a+Number(b||0),0), 0);
      if (wifiNoData){
        if (!labels.length || total === 0){ wifiNoData.classList.remove('hidden'); wifiNoData.classList.add('flex'); }
        else { wifiNoData.classList.add('hidden'); wifiNoData.classList.remove('flex'); }
      }
    }

    const wifiBtnsWrap = document.querySelector('.wifiIncomeControls');
    const wifiIncomeBtns = Array.from(document.querySelectorAll('.wifiIncomeBtn'));
    if (wifiBtnsWrap){
      wifiBtnsWrap.addEventListener('click', (e) => {
        const btn = e.target.closest('.wifiIncomeBtn');
        if (!btn) return;
        applyActive(wifiIncomeBtns, btn);
        updateWifiIncome(btn.dataset.view);
      });
    }
    const defaultWifiBtn = wifiIncomeBtns.find(b => b.dataset.view === 'month');
    if (defaultWifiBtn) applyActive(wifiIncomeBtns, defaultWifiBtn);
    updateWifiIncome('month');
  }

  loadDashboard().catch(err => console.error('link_login dashboard load failed', err));
})();
