// HouseParty — main.js
// Global utilities used across all pages

// CSRF token helper for AJAX requests
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const csrfToken = getCookie('csrftoken');

// Generic AJAX POST helper
async function postJSON(url, data) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify(data),
  });
  return response.json();
}

// Generic AJAX GET helper
async function getJSON(url) {
  const response = await fetch(url);
  return response.json();
}


// ── Slot polling ──────────────────────────────────────────────────
function updateSlotUI(tierId, data) {
  const countEl = document.getElementById(`slot-count-${tierId}`);
  if (!countEl) return;

  if (data.sold_out) {
    countEl.textContent = 'Sold out';
    countEl.classList.remove('text-gold');
    countEl.classList.add('text-muted');

    // Disable register button for this tier if present
    const btn = document.querySelector(`[data-tier-id="${tierId}"]`);
    if (btn) {
      btn.textContent = 'Sold Out';
      btn.classList.remove('btn-gold');
      btn.classList.add('btn-outline');
      btn.style.opacity = '0.4';
      btn.style.pointerEvents = 'none';
    }
  } else {
    countEl.textContent = `${data.available} left`;
    countEl.classList.remove('text-muted');
    countEl.classList.add('text-gold');
  }
}

async function pollSlot(tierId) {
  try {
    const data = await getJSON(`/api/slots/${tierId}/`);
    updateSlotUI(tierId, data);
  } catch (err) {
    console.warn(`Slot poll failed for tier ${tierId}:`, err);
  }
}

function initSlotPolling(tierIds) {
  if (!tierIds || tierIds.length === 0) return;

  // Poll immediately on load
  tierIds.forEach(id => pollSlot(id));

  // Then poll every 30 seconds
  setInterval(() => {
    tierIds.forEach(id => pollSlot(id));
  }, 30000);
}