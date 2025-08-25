// ====== State ======
let currentPage = 1;
let limit = 20;
let totalPages = 1;

let transactionsData = [];
let currentTransSortKey = null; // 'id','fio','phone','amount','paymentSystem','trans_id','status','date'
let currentTransSortDir = 'asc';

const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');

// ====== Utils ======
function getPaymentSystem(trans_id) {
  if (!trans_id) return '';
  if (/^\d+$/.test(trans_id)) return 'Click';
  if (/^[a-fA-F0-9]{24}$/.test(trans_id)) return 'PayMe';
  return '';
}

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
  const dt = new Date(y, (m || 1) - 1, d || 1, hh, mm, ss);
  return isNaN(dt.getTime()) ? null : dt;
}

// ====== Search ======
async function searchTransactions() {
  const term = searchInput.value.trim().toLowerCase();
  if (!term) {
    currentPage = 1;
    fetchTransactions();
    return;
  }
  try {
    const response = await fetch(`/api/transactions/search?search=${encodeURIComponent(term)}`);
    if (!response.ok) throw new Error(`Server returned ${response.status}`);
    const data = await response.json();
    transactionsData = data.transactions.slice();
    renderTransactionTable();

    document.getElementById('userCount').textContent = data.total;
    document.getElementById('paginationButtons').innerHTML = ''; // hide pagin while searching
  } catch (err) {
    console.error('Search error:', err);
    alert('To‘lovlarni qidirishda xatolik yuz berdi.');
  }
}

if (searchInput) searchInput.addEventListener('input', searchTransactions);
if (searchButton) searchButton.addEventListener('click', (e) => { e.preventDefault(); searchTransactions(); });

// ====== Fetch & Pagination ======
document.addEventListener('DOMContentLoaded', () => {
  // session check
  const loggedInUser = localStorage.getItem('loggedInUser');
  const expirationTime = localStorage.getItem('loginExpiration');
  if (loggedInUser && expirationTime) {
    if (Date.now() > +expirationTime) {
      localStorage.removeItem('loggedInUser');
      localStorage.removeItem('loginExpiration');
      alert("Your session has expired. Please log in again.");
      return (window.location.href = '/admin_panel_login');
    }
  } else {
    return (window.location.href = '/admin_panel_login');
  }

  // limit
  const limitSelect = document.getElementById('limitSelect');
  if (limitSelect) {
    limitSelect.addEventListener('change', (e) => {
      limit = parseInt(e.target.value, 10);
      currentPage = 1;
      fetchTransactions();
    });
  }

  // sort handlers
  attachTransTheadHandlers();
  updateTransSortArrows();

  // Setup WebSocket for this page (room: 'transactions')
  setupTransactionsSocket();

  fetchTransactions();
});

async function fetchTransactions() {
  try {
    const response = await fetch(`/api/transactions?page=${currentPage}&limit=${limit}`);
    if (!response.ok) {
      console.error("Server error:", response.statusText);
      return;
    }
    const data = await response.json();
    const transactions = data.transactions;
    const totalTransactions = data.total;

    totalPages = Math.ceil(totalTransactions / (limit || 20));
    transactionsData = transactions.slice();
    renderTransactionTable();
    setupPagination();

    document.getElementById('userCount').textContent = totalTransactions;
  } catch (error) {
    console.error('Error fetching transactions:', error);
  }
}

function setupPagination() {
  const paginationButtons = document.getElementById('paginationButtons');
  paginationButtons.innerHTML = '';

  const prevButton = document.createElement('button');
  prevButton.textContent = '«';
  prevButton.disabled = currentPage === 1;
  prevButton.className = "px-3 py-1 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-indigo-400 dark:hover:bg-indigo-600 mx-1";
  prevButton.onclick = () => {
    if (currentPage > 1) { currentPage--; fetchTransactions(); }
  };
  paginationButtons.appendChild(prevButton);

  const pageButtons = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pageButtons.push(i);
  } else {
    if (currentPage <= 4) {
      pageButtons.push(1, 2, 3, 4, 5, '...', totalPages);
    } else if (currentPage >= totalPages - 3) {
      pageButtons.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
    } else {
      pageButtons.push(1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages);
    }
  }

  pageButtons.forEach(page => {
    if (page === '...') {
      const dots = document.createElement('span');
      dots.textContent = '...';
      dots.className = "mx-1";
      paginationButtons.appendChild(dots);
    } else {
      const button = document.createElement('button');
      button.textContent = page;
      if (page === currentPage) button.classList.add('active-page');
      button.className += " px-3 py-1 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-indigo-400 dark:hover:bg-indigo-600 mx-1";
      button.onclick = () => { currentPage = page; fetchTransactions(); };
      paginationButtons.appendChild(button);
    }
  });

  const nextButton = document.createElement('button');
  nextButton.textContent = '»';
  nextButton.disabled = currentPage === totalPages;
  nextButton.className = "px-3 py-1 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-indigo-400 dark:hover:bg-indigo-600 mx-1";
  nextButton.onclick = () => {
    if (currentPage < totalPages) { currentPage++; fetchTransactions(); }
  };
  paginationButtons.appendChild(nextButton);

  document.getElementById('pageInput').value = currentPage;
}

function goToPage() {
  const pageInput = document.getElementById('pageInput').value;
  const pageNumber = parseInt(pageInput, 10);
  if (pageNumber >= 1 && pageNumber <= totalPages) {
    currentPage = pageNumber;
    fetchTransactions();
  } else {
    alert(`Please enter a page number between 1 and ${totalPages}`);
  }
}
window.goToPage = goToPage;

// ====== Sorting ======
function attachTransTheadHandlers() {
  document.querySelectorAll('#paymentTable th.sortable').forEach(th => {
    th.addEventListener('click', function () {
      const key = th.dataset.key;
      if (!key) return;
      if (currentTransSortKey === key) {
        currentTransSortDir = currentTransSortDir === 'asc' ? 'desc' : 'asc';
      } else {
        currentTransSortKey = key;
        currentTransSortDir = 'asc';
      }
      renderTransactionTable();
    });
  });
}

function updateTransSortArrows() {
  document.querySelectorAll('#paymentTable th.sortable .sort-arrow').forEach(span => {
    span.textContent = '';
  });
  if (currentTransSortKey) {
    const th = document.querySelector(`#paymentTable th.sortable[data-key="${currentTransSortKey}"] .sort-arrow`);
    if (th) th.textContent = currentTransSortDir === 'asc' ? '▲' : '▼';
  }
}

function renderTransactionTable() {
  if (currentTransSortKey) {
    transactionsData.sort((a, b) => {
      let v1, v2;

      if (currentTransSortKey === 'paymentSystem') {
        v1 = getPaymentSystem(a.trans_id);
        v2 = getPaymentSystem(b.trans_id);
        return currentTransSortDir === 'asc' ? v1.localeCompare(v2) : v2.localeCompare(v1);
      }

      v1 = a[currentTransSortKey];
      v2 = b[currentTransSortKey];

      if (currentTransSortKey === 'id') {
        const n1 = Number(v1) || 0, n2 = Number(v2) || 0;
        return currentTransSortDir === 'asc' ? n1 - n2 : n2 - n1;
      }

      if (currentTransSortKey === 'amount') {
        const n1 = parseFloat(String(v1).replace(/\s/g, '').replace(/[^\d.]/g, '')) || 0;
        const n2 = parseFloat(String(v2).replace(/\s/g, '').replace(/[^\d.]/g, '')) || 0;
        return currentTransSortDir === 'asc' ? n1 - n2 : n2 - n1;
      }

      if (currentTransSortKey === 'date') {
        const d1 = parseDMYDate(v1) || new Date(0);
        const d2 = parseDMYDate(v2) || new Date(0);
        return currentTransSortDir === 'asc' ? d1 - d2 : d2 - d1;
      }

      v1 = v1 == null ? '' : String(v1);
      v2 = v2 == null ? '' : String(v2);
      return currentTransSortDir === 'asc' ? v1.localeCompare(v2) : v2.localeCompare(v1);
    });
  }

  const tableBody = document.getElementById('paymentTableBody');
  tableBody.innerHTML = '';

  transactionsData.forEach(transaction => {
    const paymentSystem = getPaymentSystem(transaction.trans_id);
    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="px-4 py-3">${transaction.id}</td>
      <td class="px-4 py-3">${transaction.fio}</td>
      <td class="px-4 py-3">${transaction.phone}</td>
      <td class="px-4 py-3">${transaction.amount}</td>
      <td class="px-4 py-3">${paymentSystem}</td>
      <td class="px-4 py-3">${transaction.trans_id}</td>
      <td class="px-4 py-3">${transaction.status}</td>
      <td class="px-4 py-3">${transaction.date}</td>
    `;
    if (transaction.status === "success") {
      row.style.backgroundColor = "#d4edda";
    }
    tableBody.appendChild(row);
  });

  updateTransSortArrows();
}

// ====== WebSocket (Socket.IO) ======
let txSocket;
function setupTransactionsSocket() {
  try {
    if (typeof io === 'undefined') return;
    if (txSocket) return;
    let debounceId;
    const safeRefresh = () => {
      clearTimeout(debounceId);
      debounceId = setTimeout(() => { if (!document.hidden) fetchTransactions(); }, 250);
    };
    txSocket = io('/updates', { transports: ['websocket','polling'], query: { page: 'transactions' } });
    txSocket.on('connect', () => console.debug('[WS] transactions connected'));
    txSocket.on('refresh', (msg) => {
      if (!msg || (msg.page && msg.page !== 'transactions')) return;
      safeRefresh();
    });
    window.addEventListener('beforeunload', () => { try { txSocket.disconnect(); } catch(e) {} });
  } catch (e) {
    console.warn('WS disabled:', e);
  }
}
