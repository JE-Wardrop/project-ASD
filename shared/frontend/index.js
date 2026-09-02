//  Get data from backend services and update the dashboard UI.

const DEMO_ACCOUNT = 1; // Demo customer

const API = {
  transactions: "http://localhost:8205",
  accounts: "http://localhost:8202",
  notifications: "http://localhost:8203",
};

const TIMEOUT_MS = 2500;

// Format money
const money = (n) =>
  "$" +
  Number(n || 0).toLocaleString("en-AU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

// Fetch JSON with timeout
async function getJSON(url, ms = TIMEOUT_MS) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    const resp = await fetch(url, { signal: ctrl.signal });
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

// ---------------- Greeting ----------------
function setGreeting() {
  const h = new Date().getHours();
  const part =
    h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
  document.getElementById("greeting").textContent = `${part}, Alex`;
}

// ---------------- Load balance ----------------
async function loadBalance() {
  const el = document.querySelector('[data-tile="balance"]');
  const note = document.querySelector('[data-note="balance"]');

  const data = await getJSON(
    `${API.accounts}/accounts/${DEMO_ACCOUNT}/balance`
  );
  if (data === null) {
    el.textContent = "—";
    note.textContent = "Account service unavailable";
    return;
  }
  el.textContent = money(data.balance ?? data.amount ?? 0);
  note.textContent = "Across all accounts";
}

// ---------------- Load transactions ----------------
async function loadTransactions() {
  const list = document.getElementById("recent-transactions");
  const data = await getJSON(`${API.transactions}/transactions?limit=50`);

  if (data === null) {
    list.innerHTML = '<p class="muted">Transaction service unavailable.</p>';
    return;
  }

  const rows = data.transactions || [];

  //  Calculate money in, money out, and pending transactions
  let moneyIn = 0,
    moneyOut = 0,
    pending = 0;

  for (const t of rows) {
    if (t.status === "PENDING") {
      pending += 1;
      continue;
    }
    if (t.status !== "COMPLETED") continue;

    const amt = Number(t.amount) || 0;
    const isIn =
      t.transaction_type === "DEPOSIT" ||
      (t.transaction_type === "TRANSFER" &&
        t.receiver_account_id === DEMO_ACCOUNT);
    const isOut =
      t.transaction_type === "WITHDRAWAL" ||
      (t.transaction_type === "TRANSFER" &&
        t.sender_account_id === DEMO_ACCOUNT);

    if (isIn) moneyIn += amt;
    if (isOut) moneyOut += amt;
  }

  document.querySelector('[data-tile="in"]').textContent = money(moneyIn);
  document.querySelector('[data-tile="out"]').textContent = money(moneyOut);
  document.querySelector('[data-tile="pending"]').textContent = String(pending);

  //  Render recent transactions
  if (!rows.length) {
    list.innerHTML = '<p class="muted">No transactions yet.</p>';
    return;
  }

  list.innerHTML = rows
    .slice(0, 6)
    .map((t) => {
      const isIn =
        t.transaction_type === "DEPOSIT" ||
        (t.transaction_type === "TRANSFER" &&
          t.receiver_account_id === DEMO_ACCOUNT);

      const dir = isIn ? "in" : "out";
      const sign = isIn ? "+" : "−";
      const label = t.description || t.transaction_type;
      const when = (t.created_at || "").slice(0, 16).replace("T", " ");

      return `
      <div class="entry">
        <span class="entry-icon ${dir}">${isIn ? "↓" : "↑"}</span>
        <span class="entry-main">
          <span class="entry-title">${escapeHTML(label)}</span>
          <span class="entry-sub">${escapeHTML(
            t.transaction_type
          )} &middot; ${escapeHTML(when)} &middot; ${escapeHTML(
        t.status
      )}</span>
        </span>
        <span class="entry-amount ${dir}">${sign}${money(t.amount)}</span>
      </div>`;
    })
    .join("");
}

// ---------------- Load notifications ----------------
async function loadNotifications() {
  const list = document.getElementById("recent-notifications");
  const data = await getJSON(`${API.notifications}/notifications?limit=6`);

  if (data === null) {
    list.innerHTML = '<p class="muted">Notification service unavailable.</p>';
    return;
  }

  const rows = data.notifications || data || [];
  if (!rows.length) {
    list.innerHTML = '<p class="muted">You are all caught up.</p>';
    return;
  }

  list.innerHTML = rows
    .slice(0, 6)
    .map(
      (n) => `
    <div class="entry">
      <span class="entry-icon">!</span>
      <span class="entry-main">
        <span class="entry-title">${escapeHTML(n.message || "")}</span>
        <span class="entry-sub">${escapeHTML(
          n.notification_type || ""
        )} &middot; ${escapeHTML(n.status || "")}</span>
      </span>
    </div>`
    )
    .join("");
}

// ---------------- Load service status ----------------
async function loadStatus() {
  const chips = document.querySelectorAll(".svc[data-health]");
  await Promise.all(
    [...chips].map(async (chip) => {
      const ok = (await getJSON(chip.dataset.health)) !== null;
      chip.classList.toggle("is-up", ok);
      chip.classList.toggle("is-down", !ok);
    })
  );
}

function escapeHTML(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[
        c
      ])
  );
}

// ---------------- Refresh all ----------------
function refreshAll() {
  loadBalance();
  loadTransactions();
  loadNotifications();
  loadStatus();
}

document.addEventListener("DOMContentLoaded", () => {
  setGreeting();
  refreshAll();
  document.getElementById("refreshBtn").addEventListener("click", refreshAll);
  setInterval(refreshAll, 20000);
});
