const apiBase = "http://127.0.0.1:8000";  // Backend base URL
let currentSessionId = null;

// User Registration
document.getElementById("registerBtn").addEventListener("click", async () => {
  const data = {
    name: document.getElementById("name").value,
    phone: document.getElementById("phone").value,
    age: parseInt(document.getElementById("age").value),
    gender: document.getElementById("gender").value,
    email: document.getElementById("email").value
  };

  let res = await fetch(`${apiBase}/register-user`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
  });

  let result = await res.json();
  document.getElementById("result").innerText = JSON.stringify(result, null, 2);
  if (result.session_id) {
    currentSessionId = result.session_id;
    document.getElementById("sessionId").value = currentSessionId;
  }
});

// OTP Verification
document.getElementById("verifyOtpBtn").addEventListener("click", async () => {
  const data = {
    session_id: document.getElementById("sessionId").value,
    otp: document.getElementById("otp").value
  };

  let res = await fetch(`${apiBase}/verify-otp`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
  });

  let result = await res.json();
  document.getElementById("result").innerText = JSON.stringify(result, null, 2);
});

// Start Liveness
document.getElementById("startLivenessBtn").addEventListener("click", async () => {
  const data = { user_session_id: currentSessionId };

  let res = await fetch(`${apiBase}/liveness/start`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
  });

  let result = await res.json();
  document.getElementById("livenessStatus").innerText = JSON.stringify(result, null, 2);
});

// Aadhaar Upload + Final Verification
document.getElementById("verifyBtn").addEventListener("click", async () => {
  const formData = new FormData();
  formData.append("session_id", currentSessionId);
  formData.append("aadhaar_image", document.getElementById("aadhaarFile").files[0]);

  let res = await fetch(`${apiBase}/verify-single-stage`, {
    method: "POST",
    body: formData
  });

  let result = await res.json();
  document.getElementById("result").innerText = JSON.stringify(result, null, 2);
});

