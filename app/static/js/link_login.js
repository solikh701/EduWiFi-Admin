(function(){
  const root = document.getElementById('pageRoot');
  if(!root) return;
  const UNI = root.dataset.university;

  const totalConnections = document.getElementById('totalConnections');
  const totalWifi        = document.getElementById('totalWifi');
  const monthlyIncome    = document.getElementById('monthlyIncome');

  const accountsTable    = document.getElementById('accountsTable');
  const transactionsTable= document.getElementById('transactionsTable');

  const btnUsers = document.getElementById('seeAllUsers');
  const btnTx    = document.getElementById('seeAllTransactions');
  if (btnUsers) btnUsers.onclick = () => location.href = `/link_login/${UNI}/users`;
  if (btnTx)    btnTx.onclick    = () => location.href = `/link_login/${UNI}/transactions`;

  async function loadDashboard(){
    try{
      const res = await fetch(`/api/link_login/${encodeURIComponent(UNI)}/dashboard`);
      const data = await res.json();

      totalConnections.textContent = data.total_connections ?? 0;
      totalWifi.textContent        = data.total_wifi ?? 0;
      monthlyIncome.textContent    = (data.monthly_income ?? 0) + " so'm";

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
          <td class="py-2 px-2">${t.amount ?? ''}</td>
          <td class="py-2 px-2">${t.status ?? ''}</td>
          <td class="py-2 px-2">${t.desc ?? ''}</td>
        </tr>`).join('');

      // charts
      const connCtx = document.getElementById('connectionsChart').getContext('2d');
      new Chart(connCtx, {
        type: 'line',
        data: {
          labels: (data.connections_chart||[]).map((_,i)=>`#${i+1}`),
          datasets: [{ label: 'Ulanishlar', data: data.connections_chart||[] }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });

      const incomeCtx = document.getElementById('incomeChart').getContext('2d');
      const src = data.wifi_income_data || [];
      if (!src.length){
        document.getElementById('noIncomeData')?.classList.remove('hidden');
      } else {
        new Chart(incomeCtx, {
          type: 'bar',
          data: {
            labels: src.map(x=>x.name),
            datasets: [{ label: "Tushum", data: src.map(x=>x.value) }]
          },
          options: { responsive: true, maintainAspectRatio: false }
        });
      }
    }catch(e){
      console.error('dashboard load failed', e);
    }
  }

  loadDashboard();
})();
