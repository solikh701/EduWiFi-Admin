// app/static/js/teachers.js
(() => {
  // --------- State ----------
  const state = {
    page: 1,
    limit: 20,
    search: "",
    sort: "id",
    order: "desc",
    university: "off", // 'off' => hammasi
  };

  // --------- Refs ----------
  const tbody = document.getElementById("teachersTbody");
  const totalCountEl = document.getElementById("totalCount");
  const limitSelect = document.getElementById("limitSelect");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const pageInfo = document.getElementById("pageInfo");
  const pageInput = document.getElementById("pageInput");
  const goBtn = document.getElementById("goBtn");
  const searchInput = document.getElementById("searchInput");

  const sortHeaders = Array.from(document.querySelectorAll("th.sort"));

  // filter dropdown
  const uniBtn = document.getElementById("uniFilterBtn");
  const uniText = document.getElementById("uniFilterText");
  const uniDd   = document.getElementById("uniDropdown");
  const uniItemsWrap = document.getElementById("uniItems");

  // sidebar WiFi collapsible — **BOSHQARILMAYDI** (inline skript boshqaradi)
  const wifiMenuBtn = document.getElementById("wifiMenuBtn");
  const wifiMenu = document.getElementById("wifiMenu");
  const wifiArrow = document.getElementById("wifiMenuArrow");

  // user icon dropdown (agar bor bo'lsa)
  const profileBtn = document.getElementById("sidebarProfileBtn");
  const profileMenu = document.getElementById("profileMenu");
  const logoutBtn = document.getElementById("sidebarLogoutBtn");

  // --------- Helpers ----------
  const fetchJSON = async (url) => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  };

  const extractUniversity = (link) => {
    if (!link) return "";
    try {
      const u = new URL(link);
      const parts = u.hostname.split(".");
      return parts.length >= 2 ? parts[parts.length - 2].toLowerCase() : "";
    } catch {
      const host = String(link).replace(/^https?:\/\//, "").split("/")[0];
      const parts = host.split(".");
      return parts.length >= 2 ? parts[parts.length - 2].toLowerCase() : "";
    }
  };

  const setDisabled = (btn, disabled) => {
    btn.disabled = disabled;
    btn.classList.toggle("opacity-50", disabled);
    btn.classList.toggle("pointer-events-none", disabled);
  };

  const arrowFor = (key) => {
    if (state.sort !== key) return " ⬍";
    return state.order === "asc" ? " ↑" : " ↓";
  };

  const updateSortHeaders = () => {
    sortHeaders.forEach((th) => {
      const key = th.dataset.sort;
      const base = th.textContent.split(/[↑↓⬍]/)[0].trim(); // tozalash
      th.textContent = base + arrowFor(key);
    });
  };

  const buildQS = () => {
    const qs = new URLSearchParams();
    qs.set("page", state.page);
    qs.set("limit", state.limit);
    if (state.search) qs.set("q", state.search);  // <<<
    qs.set("sort", state.sort);
    qs.set("order", state.order);
    if (state.university !== "off") qs.set("university", state.university);
    return qs.toString();
  };

  const renderRows = (items) => {
    if (!items || !items.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center py-6 text-gray-400 dark:text-gray-500">
            Ma'lumot topilmadi
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = items
      .map((it) => {
        const uni = (it.university && String(it.university)) || extractUniversity(it.link_login);
        const role = it.role || "Teacher";
        return `
          <tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
            <td class="px-3 py-2">${it.id ?? ""}</td>
            <td class="px-3 py-2">${it.MAC ?? it.mac ?? ""}</td>
            <td class="px-3 py-2">${it.fio ?? ""}</td>
            <td class="px-3 py-2">${it.phone_number ?? it.phone ?? ""}</td>
            <td class="px-3 py-2">${uni || "-"}</td>
            <td class="px-3 py-2">${role}</td>
          </tr>`;
      })
      .join("");
  };

  const updatePagination = (total) => {
    const totalNum = Number(total || 0);
    totalCountEl.textContent = totalNum;

    if (totalNum === 0) {
      pageInfo.textContent = "0 / 0";
      setDisabled(prevBtn, true);
      setDisabled(nextBtn, true);
      return;
    }

    const totalPages = Math.max(1, Math.ceil(totalNum / state.limit));
    if (state.page > totalPages) state.page = totalPages;
    if (state.page < 1) state.page = 1;

    pageInfo.textContent = `${state.page} / ${totalPages}`;

    setDisabled(prevBtn, state.page <= 1);
    setDisabled(nextBtn, state.page >= totalPages);
  };

  const loadTeachers = async () => {
    try {
      const data = await fetchJSON(`/api/teachers?${buildQS()}`);
      const items = data.items || data.data || [];
      const total = data.total ?? data.count ?? 0;

      renderRows(items);
      updatePagination(total);
      updateSortHeaders();
    } catch (e) {
      console.error("loadTeachers failed:", e);
      renderRows([]);
      updatePagination(0);
    }
  };

  const loadUniversities = async () => {
    try {
      const data = await fetchJSON("/api/teachers/universities");
      const list = Array.isArray(data.universities) ? data.universities : [];
      if (!list.length) {
        uniItemsWrap.innerHTML = `<div class="px-4 py-2 text-sm text-gray-400 dark:text-gray-500">Universitet topilmadi</div>`;
        return;
      }
      uniItemsWrap.innerHTML = list
        .map(
          (u) =>
            `<button data-uni="${u}" class="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-800 capitalize">${u}</button>`
        )
        .join("");
    } catch (e) {
      console.error("loadUniversities failed:", e);
      uniItemsWrap.innerHTML = `<div class="px-4 py-2 text-sm text-red-500">Xatolik</div>`;
    }
  };

  // --------- Events ----------
  prevBtn.addEventListener("click", () => {
    if (prevBtn.disabled) return;
    state.page = Math.max(1, state.page - 1);
    loadTeachers();
  });

  nextBtn.addEventListener("click", () => {
    if (nextBtn.disabled) return;
    state.page += 1;
    loadTeachers();
  });

  goBtn.addEventListener("click", () => {
    const n = Number(pageInput.value);
    if (!Number.isFinite(n) || n < 1) return;
    state.page = Math.floor(n);
    loadTeachers();
  });

  limitSelect.addEventListener("change", () => {
    state.limit = Number(limitSelect.value) || 20;
    state.page = 1;
    loadTeachers();
  });

  // search (debounced)
  let tId;
  searchInput.addEventListener("input", () => {
    clearTimeout(tId);
    tId = setTimeout(() => {
      state.search = searchInput.value.trim();
      state.page = 1;
      loadTeachers();
    }, 350);
  });

  // sorting
  sortHeaders.forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (!key) return;
      if (state.sort === key) {
        state.order = state.order === "asc" ? "desc" : "asc";
      } else {
        state.sort = key;
        state.order = "asc";
      }
      state.page = 1;
      loadTeachers();
    });
  });

  // filter dropdown toggle
  const toggleDd = (open) => {
    const wantOpen = open ?? !uniDd.classList.contains("dd-open");
    uniDd.classList.toggle("dd-open", wantOpen);
    uniDd.classList.toggle("dd-close", !wantOpen);
  };

  uniBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleDd();
  });

  document.addEventListener("click", () => toggleDd(false));
  uniDd.addEventListener("click", (e) => e.stopPropagation());

  // filter select
  uniDd.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-uni]");
    if (!btn) return;
    const val = btn.dataset.uni;
    state.university = val || "off";
    uniText.textContent = `Filter: ${state.university === "off" ? "Off" : state.university}`;
    state.page = 1;
    toggleDd(false);
    loadTeachers();
  });

  // user icon dropdown
  if (profileBtn && profileMenu) {
    profileBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      profileMenu.classList.toggle("hidden");
    });
    document.addEventListener("click", () => profileMenu.classList.add("hidden"));
  }
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem("loggedInUser");
      localStorage.removeItem("loginExpiration");
      window.location.href = "/admin_panel_login";
    });
  }

  // --------- Init ----------
  limitSelect.value = String(state.limit);
  loadUniversities().then(loadTeachers);

  // WebSocket for this page (room: 'teachers') — polling-only fallback
  try {
    if (typeof io !== 'undefined') {
      let debounceId;
      const safeRefresh = () => {
        clearTimeout(debounceId);
        debounceId = setTimeout(() => {
          if (!document.hidden) {
            const jitter = Math.random() * 800;
            setTimeout(() => { loadTeachers(); }, jitter);
          }
        }, 250);
      };
      const socket = io('/updates', {
        transports: ['polling'],
        query: { page: 'teachers' }
      });
      socket.on('refresh', (msg) => {
        if (!msg || (msg.page && msg.page !== 'teachers')) return;
        safeRefresh();
      });
      window.addEventListener('beforeunload', () => { try { socket.disconnect(); } catch(e){} });
    }
  } catch(e) { console.warn('WS disabled:', e); }
})();
