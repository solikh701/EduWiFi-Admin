(function(){
  const root = document.getElementById('pageRoot');
  if(!root) return;
  const UNI = root.dataset.university;

  const tbody = document.getElementById('txTableBody');
  const txCount = document.getElementById('txCount');
  const limitSelect = document.getElementById('limitSelect');
  const pageInfo = document.getElementById('pageInfo');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const pageInput = document.getElementById('pageInput');
  const goBtn = document.getElementById('goBtn');
  const searchInput = document.getElementById('searchInput');

  let page=1, limit=20, sort='id', order='desc', q='';

  async function load(){
    const params = new URLSearchParams({page, limit, sort, order});
    if (q) params.set('q', q);
    const res = await fetch(`/api/link_login/${encodeURIComponent(UNI)}/transactions?`+params.toString());
    const data = await res.json();
    txCount.textContent = data.total;
    pageInfo.textContent = `${data.page} / ${data.pages || 1}`;
    tbody.innerHTML = (data.items || []).map(t=>`
      <tr>
        <td class="px-3 py-2">${t.id ?? ''}</td>
        <td class="px-3 py-2">${t.date ?? ''}</td>
        <td class="px-3 py-2">${t.amount ?? ''}</td>
        <td class="px-3 py-2">${t.status ?? ''}</td>
        <td class="px-3 py-2">${t.desc ?? ''}</td>
        <td class="px-3 py-2">${t.phone_number ?? ''}</td>
        <td class="px-3 py-2">${t.transaction_id ?? ''}</td>
      </tr>
    `).join('');
    prevBtn.disabled = (page<=1);
    nextBtn.disabled = (page>=(data.pages||1));
  }

  document.querySelectorAll('.sort').forEach(th=>{
    th.addEventListener('click', ()=>{
      const s = th.dataset.sort;
      if (sort === s){ order = (order === 'asc' ? 'desc' : 'asc'); }
      else { sort = s; order = 'asc'; }
      page = 1; load();
    });
  });

  limitSelect.onchange = ()=>{ limit = parseInt(limitSelect.value,10)||20; page=1; load(); };
  prevBtn.onclick = ()=>{ if(page>1){ page--; load(); } };
  nextBtn.onclick = ()=>{ page++; load(); };
  goBtn.onclick = ()=>{ const p = parseInt(pageInput.value,10); if(p>0){ page=p; load(); } };

  // search debounce
  let t=null;
  searchInput.addEventListener('input', ()=>{
    clearTimeout(t);
    t = setTimeout(()=>{ q = searchInput.value.trim(); page=1; load(); }, 350);
  });

  // theme btn (tez)
  const tp=document.getElementById('themeToggle'), p=document.getElementById('themeIconPath');
  function setTheme(mode){ if(mode==='dark'){ document.documentElement.classList.add('dark'); localStorage.setItem('theme','dark'); p.setAttribute('d','M21 12.79A9 9 0 1111.21 3a7 7 0 109.79 9.79z'); } else { document.documentElement.classList.remove('dark'); localStorage.setItem('theme','light'); p.setAttribute('d','M12 3v1m0 16v1m8.66-13.66l-.71.71M4.05 19.95l-.71.71M21 12h-1M4 12H3m16.66 4.95l-.71-.71M4.05 4.05l-.71-.71M12 7a5 5 0 100 10 5 5 0 000-10z'); } }
  setTheme(localStorage.getItem('theme') || (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'));
  if (tp) tp.onclick = ()=> setTheme(document.documentElement.classList.contains('dark') ? 'light' : 'dark');

  // WebSocket for this page (room: link_transactions:<UNI>)
  try {
    if (typeof io !== 'undefined') {
      let debounceId;
      const safeRefresh = () => {
        clearTimeout(debounceId);
        debounceId = setTimeout(()=>{ if(!document.hidden) load(); }, 250);
      };
      const socket = io('/updates', {
        transports: ['websocket','polling'],
        query: { page: `link_transactions:${UNI}` }
      });
      socket.on('refresh', (msg) => {
        if (!msg || (msg.page && msg.page !== `link_transactions:${UNI}`)) return;
        safeRefresh();
      });
      window.addEventListener('beforeunload', () => { try { socket.disconnect(); } catch(e){} });
    }
  } catch(e) { console.warn('WS disabled:', e); }

  load();
})();
