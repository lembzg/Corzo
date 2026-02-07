window.checkWallet = function checkWallet() {
  if (window.ethereum) {
    alert("Wallet detected");
  } else {
    alert("No wallet found. Install MetaMask.");
  }
};

window.checkAddress = async function checkAddress() {
  if (!window.ethereum) {
    alert("No wallet found. Install MetaMask.");
    return null;
  }
  try {
    const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
    const addr = accounts?.[0];
    alert("Connected address:\n" + addr);
    return addr;
  } catch (err) {
    console.error(err);
    alert("Could not connect: " + (err?.message || err));
    return null;
  }
};

window.switchPlasma = async function switchPlasma() {
  if (!window.ethereum) {
    alert("No wallet found. Install MetaMask.");
    return;
  }

  try {
    await window.ethereum.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: "0x2612" }],
    });

  } catch (switchError) {
    if (switchError?.code === 4902) {
      try {
        await window.ethereum.request({
          method: "wallet_addEthereumChain",
          params: [
            {
              chainId: "0x2612",
              chainName: "Plasma Testnet",
              nativeCurrency: { name: "XPL", symbol: "XPL", decimals: 18 },
              rpcUrls: ["https://testnet-rpc.plasma.to"],
              blockExplorerUrls: ["https://testnet.plasmascan.to"],
            },
          ],
        });
        alert("Plasma Testnet added. Try connecting again.");
        window.testChainStatus();

      } catch (addError) {
        console.error(addError);
        alert("Could not add Plasma chain: " + (addError?.message || addError));
      }
    } else {
      console.error(switchError);
      alert("Could not switch network: " + (switchError?.message || switchError));
    }
  }
};

window.testChainStatus = async function () {
  const el = document.getElementById("chainStatus");
  if (!el) return;
  if (!window.ethereum) {
    el.textContent = "No wallet detected";
    return;
  }
  try {
    const chainID = await window.ethereum.request({ method: "eth_chainId" });
    el.textContent = `Chain ID: ${chainID}`;
  } catch (error) {
    console.error("Error fetching chain ID:", error);
    el.textContent = "Could not read chain";
  }
};

// initialize and keep in sync
if (document.readyState === "loading") {
  window.addEventListener("DOMContentLoaded", () => window.testChainStatus());
} else {
  window.testChainStatus();
}

if (window.ethereum && window.ethereum.on) {
  window.ethereum.on("chainChanged", () => window.testChainStatus());
}

const sendBtn = document.getElementById("sendBtn");
if (sendBtn) {
  sendBtn.addEventListener("click", async () => {

    const txStatus = document.getElementById("txStatus");
    const addr = await checkAddress(); // returns address or null
    if (!addr) return;
//     const tx = { from: addr, to: addr, value: "0x0" };
//     try {
//       const transactionHash = await window.ethereum.request({
//         method: "eth_sendTransaction",
//         params: [tx],
//       });
//       console.log("Transaction hash:", transactionHash);
//       alert("Tx sent! Hash: " + transactionHash);
//     } catch (err) {
//       console.error(err);
//       alert("Tx failed: " + (err?.message || err));
//     }

    const provider = new ethers.BrowserProvider(window.ethereum);
    txStatus.textContent = "Opening wallet..."
    const net = await provider.getNetwork();
    const signer = await provider.getSigner();
    const resp = await signer.sendTransaction({ to: addr, value: 0n });
    console.log(resp.hash); //basically the id of the transaction
    txStatus.textContent = `Submitted: ${resp.hash} (waiting...)`;
    const receipt = await resp.wait();
    txStatus.textContent = "Confirmed.";
   });
   
}



