let page = 1, limit = 20, sort = "id", order = "desc", q = "";
let totalPages = 1;

async function loadMonitoring() {
  try {
    const params = new URLSearchParams({ page, limit, sort, order });
    if (q) params.set("search", q);

    const res = await fetch(`/api/monitoring?${params.toString()}`);
    if (!res.ok) throw new Error("Server error: " + res.status);

    const data = await res.json();

    document.getElementById("monitoringCount").textContent = data.total;
    totalPages = data.pages || 1;

    const tbody = document.getElementById("monitoringBody");
    tbody.innerHTML = (data.items || []).map(r => `
      <tr class="hover:bg-gray-100 dark:hover:bg-gray-800 transition">
        <td class="px-3 py-2">${r.id}</td>
        <td class="px-3 py-2">${r.ts}</td>
        <td class="px-3 py-2">${r.client_ip}</td>
        <td class="px-3 py-2">${(r.mac || "-").toUpperCase()}</td>
        <td class="px-3 py-2">${r.hostname || "-"}</td>
        <td class="px-3 py-2">${r.domain || "-"}</td>
        <td class="px-3 py-2">${r.protocol}</td>
        <td class="px-3 py-2">${r.uid}</td>
      </tr>
    `).join("");

    renderPagination();
    updateSortArrows();
  } catch (err) {
    console.error("Error loading monitoring:", err);
  }
}

function renderPagination() {
  const container = document.getElementById("paginationButtons");
  container.innerHTML = "";

  function makeBtn(text, disabled, onclick, active=false) {
    const cls = `px-3 py-1 rounded-lg mx-1 ${
      active ? "bg-indigo-500 text-white font-bold" : "bg-gray-200 dark:bg-gray-700 hover:bg-indigo-400 dark:hover:bg-indigo-600"
    } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`;
    return `<button ${disabled ? "disabled" : ""} class="${cls}" onclick="${disabled?"":onclick}">${text}</button>`;
  }

  let html = "";
  html += makeBtn("«", page === 1, `gotoPage(${page-1})`);

  if (totalPages <= 7) {
    for (let i=1;i<=totalPages;i++) {
      html += makeBtn(i, false, `gotoPage(${i})`, page===i);
    }
  } else if (page <= 4) {
    for (let i=1;i<=5;i++) {
      html += makeBtn(i,false,`gotoPage(${i})`, page===i);
    }
    html += `<span class="px-2">...</span>`;
    html += makeBtn(totalPages,false,`gotoPage(${totalPages})`);
  } else if (page >= totalPages-3) {
    html += makeBtn(1,false,`gotoPage(1)`);
    html += `<span class="px-2">...</span>`;
    for (let i=totalPages-4;i<=totalPages;i++) {
      html += makeBtn(i,false,`gotoPage(${i})`, page===i);
    }
  } else {
    html += makeBtn(1,false,`gotoPage(1)`);
    html += `<span class="px-2">...</span>`;
    html += makeBtn(page-1,false,`gotoPage(${page-1})`);
    html += makeBtn(page,false,`gotoPage(${page})`, true);
    html += makeBtn(page+1,false,`gotoPage(${page+1})`);
    html += `<span class="px-2">...</span>`;
    html += makeBtn(totalPages,false,`gotoPage(${totalPages})`);
  }

  html += makeBtn("»", page===totalPages, `gotoPage(${page+1})`);

  container.innerHTML = html;
}

function gotoPage(p) {
  if (p>=1 && p<=totalPages) {
    page = p;
    loadMonitoring();
  }
}

function updateSortArrows() {
  document.querySelectorAll("#monitoringTable th.sort .sort-arrow").forEach(span => {
    span.textContent = "⬍";
  });
  const active = document.querySelector(`#monitoringTable th.sort[data-sort="${sort}"] .sort-arrow`);
  if (active) {
    active.textContent = order==="asc" ? "▲" : "▼";
  }
}

document.getElementById("searchInput").addEventListener("input", e=>{
  q = e.target.value.trim();
  page = 1;
  loadMonitoring();
});

document.getElementById("limitSelect").addEventListener("change", e=>{
  limit = parseInt(e.target.value,10) || 20;
  page = 1;
  loadMonitoring();
});

document.getElementById("goBtn").addEventListener("click", ()=>{
  const p = parseInt(document.getElementById("pageInput").value,10);
  if (p>=1 && p<=totalPages) gotoPage(p);
});

document.querySelectorAll(".sort").forEach(th=>{
  th.addEventListener("click", ()=>{
    const s = th.dataset.sort;
    if (sort===s) order = (order==="asc" ? "desc" : "asc");
    else { sort = s; order = "asc"; }
    page=1;
    loadMonitoring();
  });
});

loadMonitoring();
