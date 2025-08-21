document.addEventListener('DOMContentLoaded', async function () {
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

    const profileBtn = document.getElementById('sidebarProfileBtn');
    const profileMenu = document.getElementById('profileMenu');
    profileBtn.addEventListener('click', () => {
        profileMenu.classList.toggle('hidden');
    });
    document.addEventListener('click', (e) => {
        if (!profileBtn.contains(e.target) && !profileMenu.contains(e.target)) {
            profileMenu.classList.add('hidden');
        }
    });
    document.getElementById('sidebarLogoutBtn').onclick = () => {
        window.location.href = '/';
    };

    const wifiMenuBtn = document.getElementById('wifiMenuBtn');
    const wifiMenu = document.getElementById('wifiMenu');
    const wifiMenuArrow = document.getElementById('wifiMenuArrow');
    wifiMenuBtn.addEventListener('click', () => {
        wifiMenu.classList.toggle('hidden');
        wifiMenuArrow.classList.toggle('rotate-180');
    });

    let dashboard = {};
    try {
        const res = await fetch('/api/dashboard');
        dashboard = await res.json();
    } catch (e) {
        alert("Ma'lumotlarni yuklab bo'lmadi!");
        return;
    }

    document.getElementById('totalConnections').textContent = dashboard.total_connections || 0;
    document.getElementById('totalWifi').textContent = dashboard.total_wifi || 0;
    document.getElementById('monthlyIncome').textContent = dashboard.monthly_income ? `${dashboard.monthly_income} so'm` : "0 so'm";

    const months = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek'];
    let connectionsChart = new Chart(document.getElementById('connectionsChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: months,
            datasets: [{
                label: 'Ulanishlar soni',
                data: dashboard.connections_chart || [],
                backgroundColor: '#6366f1'
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } }
        }
    });

    function getIncomePieData() {
        return {
            labels: (dashboard.wifi_income_data || []).map(w => w.name),
            datasets: [{
                data: (dashboard.wifi_income_data || []).map(w => w.value),
                backgroundColor: ['#6366f1', '#10b981', '#f59e42', '#f43f5e', '#3b82f6']
            }]
        };
    }
    let incomeChart = new Chart(document.getElementById('incomeChart').getContext('2d'), {
        type: 'doughnut',
        data: getIncomePieData(),
        options: {
            plugins: {
                legend: { display: true, position: 'bottom' }
            }
        }
    });

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
            <td class="py-2 px-2">${t.amount}</td>
            <td class="py-2 px-2">${t.status}</td>
            <td class="py-2 px-2">${t.desc}</td>
        </tr>`
    ).join('');
});
