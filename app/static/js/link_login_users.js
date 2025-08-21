(function(){
  const root = document.getElementById('pageRoot');
  if(!root) return;
  const UNI = root.dataset.university;

  const tbody = document.getElementById('userTableBody');
  const userCount = document.getElementById('userCount');
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
    const res = await fetch(`/api/link_login/${encodeURIComponent(UNI)}/users?`+params.toString());
    const data = await res.json();
    userCount.textContent = data.total;
    pageInfo.textContent = `${data.page} / ${data.pages || 1}`;
    tbody.innerHTML = (data.items || []).map(u=>`
      <tr>
        <td class="px-3 py-2">${u.id ?? ''}</td>
        <td class="px-3 py-2">${u.mac ?? ''}</td>
        <td class="px-3 py-2">${u.fio ?? ''}</td>
        <td class="px-3 py-2">${u.phone_number ?? ''}</td>
        <td class="px-3 py-2">${u.role ?? ''}</td>
        <td class="px-3 py-2">${u.last_authorization ?? ''}</td>
      </tr>
    `).join('');
    prevBtn.disabled = (page<=1);
    nextBtn.disabled = (page>=(data.pages||1));
  }

  // sort header clicks
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
  const tp = document.getElementById('themeToggle');
  const sunWrap = document.getElementById('themeIconSun');
  const moonWrap = document.getElementById('themeIconMoon');

  function setTheme(mode){ 
    if(mode==='dark'){ 
      document.documentElement.classList.add('dark'); 
      localStorage.setItem('theme','dark'); 
      sunWrap && sunWrap.classList.remove('hidden');
      moonWrap && moonWrap.classList.add('hidden');
    } else { 
      document.documentElement.classList.remove('dark'); 
      localStorage.setItem('theme','light'); 
      sunWrap && sunWrap.classList.add('hidden');
      moonWrap && moonWrap.classList.remove('hidden');
    } 
  }

  setTheme(localStorage.getItem('theme') || 
          (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

  if (tp) {
    tp.onclick = ()=> setTheme(
      document.documentElement.classList.contains('dark') ? 'light' : 'dark'
    );
  }

  // WebSocket for this page (room: link_users:<UNI>)
  try {
    if (typeof io !== 'undefined') {
      let debounceId;
      const safeRefresh = () => {
        clearTimeout(debounceId);
        debounceId = setTimeout(()=>{ if(!document.hidden) load(); }, 250);
      };
      const socket = io('/updates', {
        transports: ['websocket','polling'],
        query: { page: `link_users:${UNI}` }
      });
      socket.on('refresh', (msg) => {
        if (!msg || (msg.page && msg.page !== `link_users:${UNI}`)) return;
        safeRefresh();
      });
      window.addEventListener('beforeunload', () => { try { socket.disconnect(); } catch(e){} });
    }
  } catch(e) { console.warn('WS disabled:', e); }

  load();
})();
