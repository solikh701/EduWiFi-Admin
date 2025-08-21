/*********************************************
 * Helper Functions
 *********************************************/

// (Optional) If you want to keep a function stub, just return the same rate
function convertRateLimit(rate) {
  // No conversion: just return exactly what the user typed.
  return rate;
}

// Convert a session unit to numeric seconds (for storing in DB)
function sessionUnitToSeconds(num, unit) {
  const n = parseInt(num, 10) || 0;
  switch (unit) {
    case 'minutes': return n * 60;
    case 'hours':   return n * 3600;
    case 'days':    return n * 86400;
    case 'weeks':   return n * 604800;
    case 'months':  return n * 2592000; // ~30 days
    default:       return n * 60;
  }
}

// Convert numeric seconds -> an approximate (number, unit)
function parseTimeout(seconds) {
  const MIN = 60;
  const HOUR = 3600;
  const DAY = 86400;
  const WEEK = 604800;
  const MONTH = 2592000; // 30 kun

  if (seconds % MONTH === 0) {
    return { num: seconds / MONTH, unit: 'months' };
  }
  if (seconds % WEEK === 0) {
    return { num: seconds / WEEK, unit: 'weeks' };
  }
  if (seconds % DAY === 0) {
    return { num: seconds / DAY, unit: 'days' };
  }
  if (seconds % HOUR === 0) {
    return { num: seconds / HOUR, unit: 'hours' };
  }
  if (seconds % MIN === 0) {
    return { num: seconds / MIN, unit: 'minutes' };
  }

  // agar hech qaysi toza bo‘linmasa, yaqinlashtirib minutda ko‘rsatamiz
  return { num: Math.floor(seconds / MIN), unit: 'minutes' };
}

/*********************************************
 * On Page Load
 *********************************************/
window.onload = function() {
  const loggedInUser = localStorage.getItem('loggedInUser');
  const expirationTime = localStorage.getItem('loginExpiration');

  // Basic session check
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

  // Fetch existing tariffs (local + radius)
  fetch('/api/tarif_plans')
    .then(response => {
      if (!response.ok) {
        return response.text().then(text => { throw new Error(text); });
      }
      // The server returns { local_plans: [...], radius_plans: [...] }
      return response.json();
    })
    .then(data => {
      console.log('Fetched tariff data:', data);

      const localPlans  = data.local_plans  || [];
      const radiusPlans = data.radius_plans || [];

      // 1) Build a map from groupname => row ID
      // Example: tariff_bepul => 1, tariff_kun => 2, etc.
      const groupToId = {
        'tariff_bepul': 1,
        'tariff_kun':   2,
        'tariff_hafta': 3,
        'tariff_oy':    4
      };

      // 2) Prepare an object to hold radius values for each row
      const radiusData = {
        1: { sessionTimeout: null, totalLimit: null, rateLimit: null },
        2: { sessionTimeout: null, totalLimit: null, rateLimit: null },
        3: { sessionTimeout: null, totalLimit: null, rateLimit: null },
        4: { sessionTimeout: null, totalLimit: null, rateLimit: null }
      };

      // 3) Parse radiusPlans, fill radiusData
      radiusPlans.forEach(item => {
        const grp = item.groupname;          // e.g. "tariff_bepul"
        const attr = item.attribute;         // e.g. "Session-Timeout"
        const val  = item.value;             // e.g. "86400"
        const rowId = groupToId[grp];
        if (!rowId) return; // skip if not recognized

        if (attr === 'Session-Timeout') {
          radiusData[rowId].sessionTimeout = parseInt(val, 10);
        } else if (attr === 'Mikrotik-Total-Limit') {
          radiusData[rowId].totalLimit = parseInt(val, 10);
        } else if (attr === 'Mikrotik-Rate-Limit') {
          radiusData[rowId].rateLimit = val; // e.g. "5M/5M"
        }
      });
      
      console.log(radiusData);

      // 4) Fill the radius-based fields in the UI: #sessionNumberX, #sessionUnitX, #sessionTotalLimitX, #rateLimitX
      for (let i = 1; i <= 4; i++) {
        const row = radiusData[i];

        // session timeout
        if (row.sessionTimeout !== null) {
          const parsed = parseTimeout(row.sessionTimeout);
          document.getElementById(`sessionNumber${i}`).value = parsed.num;
          document.getElementById(`sessionUnit${i}`).value   = parsed.unit;
        }

        // session total limit
        if (row.totalLimit !== null) {
          const inMB = Math.floor(row.totalLimit / 1048576);
          document.getElementById(`sessionTotalLimit${i}`).value = inMB;
        }

        // rate limit
        if (row.rateLimit !== null) {
          document.getElementById(`rateLimit${i}`).value = row.rateLimit;
        }
      }

      // 5) Fill local DB fields: price, is_active, duration_days, etc.
      //   localPlans is presumably an array of up to 4 items
      localPlans.forEach((item, index) => {
        let i = index + 1;  // row ID

        // Price
        if (item.price) {
          document.getElementById(`price${i}`).value = item.price;
        }

        // is_active
        if (typeof item.is_active === 'boolean') {
          document.getElementById(`tarif${i}`).checked = item.is_active;
        }

        // If your local DB has a "duration_days" that you want to display as "name"
        if (item.duration_days) {
          document.getElementById(`name${i}`).value = item.duration_days;
        }

        // If you store a "rate_limit" in local DB, you can also fill it here
        if (item.rate_limit) {
          document.getElementById(`rateLimit${i}`).value = item.rate_limit;
        }
      });
    })
    .catch(error => {
      console.error('Error fetching tariffs:', error);
    });
};

/*********************************************
 * Handle the SAQLASH (Save) button
 *********************************************/
document.getElementById('saveButton').addEventListener('click', function() {
  const tarifData = [];

  for (let i = 1; i <= 4; i++) {
    // Gather each field
    const nameValue       = document.getElementById(`name${i}`).value;
    const priceValue      = document.getElementById(`price${i}`).value;
    const rateLimitValue  = document.getElementById(`rateLimit${i}`).value;

    // Session Timeout
    const sessionNum      = document.getElementById(`sessionNumber${i}`);
    const sessionSelect   = document.getElementById(`sessionUnit${i}`);
    let sessionNumber     = sessionNum ? sessionNum.value : '0';
    let sessionUnit       = sessionSelect ? sessionSelect.value : 'minute';
    const sessionTimeoutSeconds = sessionUnitToSeconds(sessionNumber, sessionUnit);
    const sessionTimeoutString  = `${sessionNumber} ${sessionUnit}`;

    // Session Total Limit in MB
    const totalLimitMB    = document.getElementById(`sessionTotalLimit${i}`).value || '0';
    const totalLimitBytes = parseInt(totalLimitMB, 10) * 1048576;

    // is_active
    const isActive = document.getElementById(`tarif${i}`).checked;

    // Here we simply store the rateLimitValue as-is
    const rateLimitDB = rateLimitValue; // no more conversion

    // Build object for this row
    tarifData.push({
      id: i,
      name: nameValue,
      price: priceValue,

      rate_limit_ui: rateLimitValue,
      rate_limit_db: rateLimitDB,

      session_timeout_string:  sessionTimeoutString,
      session_timeout_seconds: sessionTimeoutSeconds,

      session_total_mb:    totalLimitMB,
      session_total_bytes: totalLimitBytes,

      is_active: isActive
    });
  }

  console.log('Tarif data to send:', tarifData);

  // Post to your backend
  fetch('/api/tarif_plans', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ tarifData })
  })
  .then(response => response.json())
  .then(data => {
    console.log('Response data:', data);
    if (data.message === 'Tarif plans updated successfully') {
      // Notification chiqishi
      const notif = document.getElementById('notifSuccess');
      notif.textContent = "Tariflar muvaffaqiyatli saqlandi!";
      notif.classList.remove('hidden');
      notif.classList.add('flex');
      setTimeout(() => {
        notif.classList.add('hidden');
        notif.classList.remove('flex');
      }, 2000);
      // window.location.reload(); // Endi avtomatik reload emas
    } else {
      alert('Error saving tarif plans: ' + data.error);
    }
  })
  .catch((error) => {
    console.error('Error:', error);
  });
});
