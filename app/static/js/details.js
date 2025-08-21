// === Helper: DOM ===
const $ = (sel, root=document) => root.querySelector(sel);
const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

let userId = null;
let originalMAC = "";
let currentUser = null;

// === Theme / profile / back ===
function applyTheme(mode){
  const path = $('#themeIconPath');
  if(mode==='dark'){
    document.documentElement.classList.add('dark');
    localStorage.setItem('theme','dark');
    path && path.setAttribute('d','M21 12.79A9 9 0 1111.21 3a7 7 0 109.79 9.79z');
  }else{
    document.documentElement.classList.remove('dark');
    localStorage.setItem('theme','light');
    path && path.setAttribute('d','M12 3v1m0 16v1m8.66-13.66l-.71.71M4.05 19.95l-.71.71M21 12h-1M4 12H3m16.66 4.95l-.71-.71M4.05 4.05l-.71-.71M12 7a5 5 0 100 10 5 5 0 000-10z');
  }
}
function initShell(){
  // theme
  const saved = localStorage.getItem('theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(saved);
  $('#themeToggle').addEventListener('click', ()=> applyTheme(document.documentElement.classList.contains('dark') ? 'light' : 'dark'));

  // profile
  $('#profileBtn').addEventListener('click', ()=> $('#profileMenu').classList.toggle('hidden'));
  $('#logoutBtn').addEventListener('click', ()=>{
    localStorage.clear();
    location.href = '/admin_panel_login';
  });

  // back
  $('#backBtn').addEventListener('click', ()=>{
    const page = new URLSearchParams(location.search).get('page') || localStorage.getItem('admin_users_currentPage') || 1;
    location.href = `/admin_panel_users`;
  });
  $('#exitBtn').addEventListener('click', ()=> $('#backBtn').click());
}

// === Toast ===
function toast(msg, isError=false){
  const el = $('#toast');
  el.textContent = msg;
  el.classList.remove('hidden');
  el.classList.toggle('text-red-300', isError);
  setTimeout(()=> el.classList.add('hidden'), 2000);
}

// === Confirm modal ===
function confirmModal(message){
  return new Promise(resolve=>{
    $('#confirmMessage').textContent = message;
    $('#confirmBackdrop').classList.remove('hidden');
    $('#confirmModal').classList.remove('hidden');
    const cleanup = ()=>{ $('#confirmBackdrop').classList.add('hidden'); $('#confirmModal').classList.add('hidden'); };
    $('#confirmNo').onclick = ()=>{ cleanup(); resolve(false); };
    $('#confirmYes').onclick = ()=>{ cleanup(); resolve(true); };
  });
}

// === Add time modal ===
function addTimeModal(){
  return new Promise(resolve=>{
    $('#timeMinutes').value = '';
    $('#timeBackdrop').classList.remove('hidden');
    $('#timeModal').classList.remove('hidden');
    const cleanup = ()=>{ $('#timeBackdrop').classList.add('hidden'); $('#timeModal').classList.add('hidden'); };
    $('#timeCancelBtn').onclick = ()=>{ cleanup(); resolve(null); };
    $('#timeSaveBtn').onclick = ()=>{ const v = parseInt($('#timeMinutes').value,10); cleanup(); resolve(isNaN(v)?null:v); };
  });
}

// === Data binding ===
function setField(name, value){
  const el = $(`[data-field="${name}"]`);
  if(el) el.value = value ?? '';
}
function fillUser(u){
  currentUser = u;

  $('#titleId').textContent = `User ${u.id}`;
  $('#totalSessions').textContent = u.total_sessions ?? '0';
  $('#totalPaid').textContent = u.overall_payed_sum ?? '0';

  // status badge + short date
  const act = u.authorization_activeness || '-';
  const badge = $('#statusBadge');
  badge.textContent = act;
  badge.classList.remove('badge-green','badge-red');
  if (act === 'AKTIV') badge.classList.add('badge-green');
  else if (act === 'NOAKTIV' || act === 'BLOCKED') badge.classList.add('badge-red');

  $('#lastAuthShort').textContent = (act==='NOINTERNET'||act==='NOINTERNETPAY'||!u.last_authorization) ? '—' : u.last_authorization;

  // left
  setField('last_ip_address', u.last_ip_address);
  setField('MAC', u.MAC);
  setField('first_authorization', u.first_authorization);
  setField('fio', u.fio);
  setField('phone_number', u.phone_number);
  setField('confirmation_code', u.confirmation_code);
  setField('authorization_activeness', u.authorization_activeness);
  setField('last_authorization',
    (u.authorization_activeness==='NOINTERNET'||u.authorization_activeness==='NOINTERNETPAY') ? '' : u.last_authorization
  );
  setField('tariff_limit', u.remaining_time ?? u.tariff_limit ?? '0');

  // right
  setField('role', u.role);
  setField('total_sessions', u.total_sessions ?? '0');
  setField('overall_authorizations', u.overall_authorizations ?? '0');
  setField('overall_payed_sum', u.overall_payed_sum ?? '0');
  setField('selectedTariff', u.selectedTariff ?? '');
  setField('comment', u.comment ?? u.comments ?? '');

  // block button
  $('#blockBtn').textContent = u.block ? 'Bloklangan' : 'Bloklanmagan';

  // MAC save toggle
  const mac = $('#macInput');
  originalMAC = u.MAC || '';
  mac.addEventListener('input', ()=>{
    const changed = mac.value.trim() !== originalMAC;
    $('#saveBtn').classList.toggle('hidden-el', !changed);
  });
}

// === API calls ===
async function getUser(id){
  const r = await fetch(`/api/users/${id}`);
  if(!r.ok) throw new Error('User not found');
  return r.json();
}
async function postJSON(url, body, method='POST'){
  const r = await fetch(url,{
    method,
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });
  return r.json();
}

// === Actions ===
async function handleBlock(){
  const stateNow = $('#blockBtn').textContent.trim();
  const action = stateNow === 'Bloklanmagan' ? 'bloklash' : 'blokdan chiqarish';
  const ok = await confirmModal(`Haqiqatan ham ${action}ni xohlaysizmi?`);
  if(!ok) return;

  const newStatusText = stateNow === 'Bloklanmagan' ? 'Bloklangan' : 'Bloklanmagan';
  $('#blockBtn').textContent = newStatusText;

  try{
    await postJSON('/api/updateStatus', {
      phone_number: $('[data-field="phone_number"]').value,
      status: newStatusText
    });
    toast('Holat yangilandi');
  }catch(e){
    toast('Holatni yangilashda xatolik', true);
  }
}

async function handleDelete(){
  const ok = await confirmModal("Haqiqatan ham foydalanuvchini o'chirmoqchimisiz?");
  if(!ok) return;

  const payload = collectUserPayload();
  try{
    const res = await postJSON('/api/deleteUser', payload, 'DELETE');
    if(res && res.success){
      const page = new URLSearchParams(location.search).get('page') || localStorage.getItem('admin_users_currentPage') || 1;
      location.href = `/admin_panel_users?page=${page}`;
    }else{
      toast('O‘chirishda xato', true);
    }
  }catch(e){ toast('O‘chirishda xato', true); }
}

async function handleUnauthorize(){
  const ok = await confirmModal("Haqiqatan ham foydalanuvchi avtorizatsiyasini o'chirmoqchimisiz?");
  if(!ok) return;

  const payload = collectUserPayload();
  try{
    const res = await postJSON('/api/unauthorization', payload);
    if(res && res.success){
      const page = new URLSearchParams(location.search).get('page') || localStorage.getItem('admin_users_currentPage') || 1;
      location.href = `/admin_panel_users?page=${page}`;
    }else{
      toast('Amalda xato', true);
    }
  }catch(e){ toast('Amalda xato', true); }
}

async function handleSaveMac(){
  const newMAC = $('#macInput').value.trim();
  const phone = $('[data-field="phone_number"]').value;

  try{
    const res = await postJSON('/api/updateMacAddress', {
      phone_number: phone,
      newMAC,
      oldMAC: originalMAC
    });
    if(res && res.success){
      originalMAC = newMAC;
      $('#saveBtn').classList.add('hidden-el');
      toast('MAC saqlandi');
    }else{
      toast('MAC saqlanmadi', true);
    }
  }catch(e){ toast('MAC saqlashda xatolik', true); }
}

async function handleAddTime(){
  const minutes = await addTimeModal();
  if(minutes==null) return;

  // ⚠️ Endpointni loyihangizga moslang! Misol uchun:
  //  POST /api/add_time  -> { phone_number, minutes }
  try{
    const res = await postJSON('/api/add_time', {
      phone_number: $('[data-field="phone_number"]').value,
      minutes
    });
    if(res && (res.success || res.ok)){
      toast('Vaqt qo‘shildi');
      // qayta yuklab olish
      const u = await getUser(userId);
      fillUser(u);
    }else{
      toast('Vaqt qo‘shishda xatolik', true);
    }
  }catch(e){ toast('Vaqt qo‘shishda xatolik', true); }
}

function collectUserPayload(){
  // Eski sahifadagi payload tuzilmasiga mos
  const act = $('[data-field="authorization_activeness"]').value;
  const lastAuth = (act==='NOINTERNET' || act==='NOINTERNETPAY') ? "" : ($('[data-field="last_authorization"]').value || '');

  return {
    id: String(userId),
    last_ip_address: $('[data-field="last_ip_address"]').value,
    role: $('[data-field="role"]').value,
    MAC: $('#macInput').value.trim(),
    overall_authorizations: $('[data-field="overall_authorizations"]').value,
    last_authorization: lastAuth,
    fio: $('[data-field="fio"]').value,
    overall_payed_sum: $('[data-field="overall_payed_sum"]').value,
    phone_number: $('[data-field="phone_number"]').value,
    selectedTariff: $('[data-field="selectedTariff"]').value,
    confirmation_code: $('[data-field="confirmation_code"]').value,
    authorization_activeness: act,
    first_authorization: $('[data-field="first_authorization"]').value,
    tariff_limit: $('[data-field="tariff_limit"]').value
  };
}

// === Init ===
document.addEventListener('DOMContentLoaded', async ()=>{
  initShell();

  // session check (xohlasangiz olib tashlashingiz mumkin)
  const logged = localStorage.getItem('loggedInUser');
  const exp = localStorage.getItem('loginExpiration');
  if(!logged || !exp || Date.now() > +exp){
    localStorage.clear();
    alert("Your session has expired. Please log in again.");
    return location.href='/admin_panel_login';
  }

  // id
  userId = new URLSearchParams(location.search).get('id');
  if(!userId){ toast('ID topilmadi', true); return; }

  // fetch & fill
  try{
    const u = await getUser(userId);
    fillUser(u);
  }catch(e){
    console.error(e);
    toast('Maʼlumotni yuklashda xato', true);
  }

  // actions
  $('#sessionsBtn').addEventListener('click', ()=> location.href = `/admin_panel_user_info?id=${userId}`);
  $('#deleteBtn').addEventListener('click', handleDelete);
  $('#unauthBtn').addEventListener('click', handleUnauthorize);
  $('#blockBtn').addEventListener('click', handleBlock);
  $('#saveBtn').addEventListener('click', handleSaveMac);
  $('#addTimeBtn').addEventListener('click', handleAddTime);
});
