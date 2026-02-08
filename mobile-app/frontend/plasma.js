
function getAddress() {
  const userData = localStorage.getItem('user');
  if (userData) {
    try {
      const user = JSON.parse(userData);
      return user.walletAddress || null;
    } catch (e) {
      console.error("Failed to parse user data:", e);
      return null;
    }
  }
  return null;
}
// -----------------------------
// Gasless send (calls backend)
// -----------------------------
// Backend origin (explicit override wins, otherwise default to API port 5050)
const BACKEND_BASE = window.BACKEND_BASE || "http://127.0.0.1:5050";
const PLASMA_RPC_URL = "https://testnet-rpc.plasma.to";
const USDT0_CONTRACT = "0x502012b361aebce43b26ec812b74d9a51db4d412";
const ERC20_ABI = [
  "function balanceOf(address) view returns (uint256)",
  "function decimals() view returns (uint8)"
];

// -------- Recipient exists check (green tick) --------
let recipientTimer = null;

async function checkRecipientExists(query) {
  const url = `${BACKEND_BASE}/api/users/exists?query=${encodeURIComponent(query)}`;
  const r = await fetch(url).catch((err) => {
    console.warn("exists lookup failed", err);
    return null;
  });
  if (!r) return false;
  const j = await r.json().catch(() => ({}));
  return !!j.exists;
}

function setRecipientTick(ok) {
  const el = document.getElementById("recipientCheck");
  if (!el) return;
  if (ok) {
    el.style.opacity = "1";
    el.style.color = "green";
  } else {
    el.style.opacity = "0";
  }
}

function wireRecipientChecker() {
  const recipientInput = document.getElementById("recipient");
  if (!recipientInput) return;

  const runCheck = async () => {
    const q = (recipientInput.value || "").trim();
    setRecipientTick(false);
    if (!q) return;
    if (recipientTimer) clearTimeout(recipientTimer);
    recipientTimer = setTimeout(async () => {
      try {
        const ok = await checkRecipientExists(q);
        setRecipientTick(ok);
      } catch (err) {
        console.warn("recipient check failed", err);
        setRecipientTick(false);
      }
    }, 300);
  };

  recipientInput.addEventListener("input", runCheck);
  recipientInput.addEventListener("blur", runCheck);

  // if prefilled (e.g., query param), check once on load
  if (recipientInput.value.trim()) {
    runCheck();
  }
}

// Balance load on dashboard
if (document.readyState === "loading") {
  window.addEventListener("DOMContentLoaded", fetchAndRenderWalletBalance);
} else {
  fetchAndRenderWalletBalance();
}


function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function getUserId() {
  // allow: send.html?userId=...
  const qs = new URLSearchParams(window.location.search);
  const qid = (qs.get("userId") || "").trim();
  if (qid) {
    localStorage.setItem("userId", qid);
    return qid;
  }
  const stored = (localStorage.getItem("userId") || "").trim();
  if (stored) return stored;

  // Fallback: derive from stored user object (set by login/register flow)
  try {
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    if (user.id) {
      localStorage.setItem("userId", user.id);
      return String(user.id);
    }
  } catch (_) {}
  return "";
}

async function getPublicIp() {
  try {
    const r = await fetch("https://api.ipify.org?format=json");
    const j = await r.json();
    return (j.ip || "").trim();
  } catch (_) {
    return "";
  }
}

function extractAuthorizationId(respJson) {
  if (respJson.authorizationId) return respJson.authorizationId;

  const rr = respJson.relayer_response;
  if (!rr) return "";

  if (typeof rr === "object" && rr.authorizationId) return rr.authorizationId;

  const raw = (typeof rr === "object" && rr.raw) ? rr.raw : "";
  if (raw) {
    try {
      const j = JSON.parse(raw);
      return j.authorizationId || "";
    } catch (_) {
      const m = raw.match(/"authorizationId"\s*:\s*"([^"]+)"/);
      return m ? m[1] : "";
    }
  }
  return "";
}

async function submitGaslessTransfer({ userId, recipient, amount, clientIp }) {
  const headers = { "Content-Type": "application/json" };

  const r = await fetch(`${BACKEND_BASE}/api/usdt/transfer`, {
    method: "POST",
    headers,
    body: JSON.stringify({ userId, recipient, amount })
  });

  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || j.message || `Transfer failed (${r.status})`);

  const authId = extractAuthorizationId(j);
  if (!authId) throw new Error("Backend did not return authorizationId.");
  return authId;
}

async function getTransferStatus(authId, clientIp) {
  const headers = {};

  const r = await fetch(`${BACKEND_BASE}/api/usdt/status?authorizationId=${encodeURIComponent(authId)}`, { headers });
  const j = await r.json().catch(() => ({}));
  return j;
}

async function waitForFinal(authId, clientIp) {
  for (let i = 0; i < 30; i++) { // ~60s
    const s = await getTransferStatus(authId, clientIp);
    if (s.status === "confirmed" || s.status === "failed") return s;
    await sleep(2000);
  }
  return { status: "timeout", error: "Timed out waiting for confirmation" };
}

async function fetchAndRenderWalletBalance() {
  const balanceEl = document.querySelector("#totalBalance");
  const sendBalanceEl = document.querySelector("#sendBalance");
  if (!balanceEl && !sendBalanceEl) return; // nowhere to render

  try {
    const userId = getUserId();
    if (!userId) throw new Error("Missing userId");

    const walletRes = await fetch(`${BACKEND_BASE}/api/wallet?userId=${encodeURIComponent(userId)}`);
    const walletJson = await walletRes.json().catch(() => ({}));
    if (!walletRes.ok || !walletJson.address) {
      throw new Error(walletJson.error || "Wallet not found");
    }

    const provider = new ethers.JsonRpcProvider(PLASMA_RPC_URL);
    const contract = new ethers.Contract(USDT0_CONTRACT, ERC20_ABI, provider);

    const [rawBalance, decimals] = await Promise.all([
      contract.balanceOf(walletJson.address),
      contract.decimals().catch(() => 6) // fallback to known decimals
    ]);

    const balanceNumber = Number(ethers.formatUnits(rawBalance, decimals));
    const formatted = balanceNumber.toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 6,
    });
    if (balanceEl) balanceEl.textContent = formatted;
    if (sendBalanceEl) sendBalanceEl.textContent = formatted;
  } catch (err) {
    console.error("Failed to load wallet balance", err);
  }
}

// Hook send button (Send page)
const sendBtn = document.getElementById("sendBtn");
if (sendBtn) {
  sendBtn.addEventListener("click", async () => {
    const txStatus = document.getElementById("txStatus");

    try {
      const userId = getUserId();
      if (!userId) throw new Error("Missing userId. Open send.html?userId=YOUR_USER_ID");

      const recipient = (document.getElementById("recipient")?.value || "").trim();
      if (!recipient) throw new Error("Enter recipient username or email.");

      const amountRaw = (document.getElementById("amountInput")?.value || "").trim();
      const amount = amountRaw.replace(/[^\d.]/g, "");
      if (!amount || Number(amount) <= 0) throw new Error("Enter a valid amount (e.g. 1.00).");

      txStatus.textContent = "Submitting…";
      const ip = await getPublicIp();

      const authId = await submitGaslessTransfer({ userId, recipient, amount, clientIp: ip });
      txStatus.textContent = `Queued...`;

      const final = await waitForFinal(authId, ip);

      if (final.status === "confirmed") {
        txStatus.textContent = `Confirmed.`;
      } else if (final.status === "failed") {
        txStatus.textContent = `Failed.${final.error || "Unknown revert"}`;
      } else {
        txStatus.textContent = `Pending… (${final.error || "unknown"})`;
      }
    } catch (e) {
      console.error(e);
      txStatus.textContent = `Error: ${e.message || e}`;
      alert(txStatus.textContent);
    }
  });
}
