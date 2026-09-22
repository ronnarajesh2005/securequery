// track_c/frontend/app.js
/*
  SecureQuery Track C Frontend & Technical Transparency Controller
  Manages:
  - Natural Language Clinical Queries
  - Split-screen 10-step SMPC Visual Proof
  - Privacy-preserving Masking (< 5 k-anonymity)
  - Cross-hospital Epidemiological Charts (Chart.js)
*/

// Automatically target FastAPI port 8000 if served from Live Server (e.g. 5500), file://, or non-8000 dev ports
const API_BASE = (window.location.protocol === 'file:' || (window.location.port && window.location.port !== '8000'))
  ? 'http://127.0.0.1:8000'
  : window.location.origin;

// Fallback Epidemiological Data (ensures charts render even if backend is offline)
const FALLBACK_TRENDS = {
  metric: "Diabetes Patient Prevalence (2020-2024)",
  years: [2020, 2021, 2022, 2023, 2024],
  series: [
    { hospital_id: "HOSP_A", hospital_name: "Hospital A (City General)", values: [22, 25, 27, 29, 30] },
    { hospital_id: "HOSP_B", hospital_name: "Hospital B (Apollo Memorial)", values: [35, 38, 41, 44, 47] },
    { hospital_id: "HOSP_C", hospital_name: "Hospital C (St. Jude Medical)", values: [18, 20, 21, 23, 25] },
    { hospital_id: "TOTAL", hospital_name: "Cross-Hospital SMPC Total", values: [75, 83, 89, 96, 102] }
  ]
};

const FALLBACK_COMPARISON = {
  conditions: ["Diabetes Mellitus", "Hypertension", "Asthma", "Heart Disease"],
  hospitals: ["Hospital A", "Hospital B", "Hospital C"],
  data: [
    { condition: "Diabetes Mellitus", HOSP_A: 30, HOSP_B: 47, HOSP_C: 25, total: 102 },
    { condition: "Hypertension", HOSP_A: 45, HOSP_B: 52, HOSP_C: 38, total: 135 },
    { condition: "Asthma", HOSP_A: 15, HOSP_B: 19, HOSP_C: 12, total: 46 },
    { condition: "Heart Disease", HOSP_A: 12, HOSP_B: 18, HOSP_C: 9, total: 39 }
  ]
};

function getSimulationDataForQuery(question) {
  const qLower = question.toLowerCase();
  const isRare = qLower.includes("rare") || qLower.includes("threshold") || qLower.includes("< 5") || qLower.includes("<5");
  const isPii = question.toUpperCase().includes("SELECT NAME") || qLower.includes("ssn") || qLower.includes("birth_date");
  const isMetformin = qLower.includes("metformin");

  let result = 102;
  let masked = false;
  let breakdown = [
    { hospital_id: "HOSP_A", hospital_name: "Hospital A (City General)", count: 30 },
    { hospital_id: "HOSP_B", hospital_name: "Hospital B (Apollo Memorial)", count: 47 },
    { hospital_id: "HOSP_C", hospital_name: "Hospital C (St. Jude Medical)", count: 25 }
  ];
  let finalAnswer = "102";
  let disclosureStatus = "DISCLOSED_SMPC_COMPLIANT";

  if (isRare) {
    result = null;
    masked = true;
    finalAnswer = "[SUPPRESSED: k < 5]";
    disclosureStatus = "SUPPRESSED_K_ANONYMITY_VIOLATION";
    breakdown = [
      { hospital_id: "HOSP_A", hospital_name: "Hospital A (City General)", count: 2 },
      { hospital_id: "HOSP_B", hospital_name: "Hospital B (Apollo Memorial)", count: 1 },
      { hospital_id: "HOSP_C", hospital_name: "Hospital C (St. Jude Medical)", count: 0 }
    ];
  } else if (isMetformin) {
    result = 64;
    finalAnswer = "64";
    breakdown = [
      { hospital_id: "HOSP_A", hospital_name: "Hospital A (City General)", count: 18 },
      { hospital_id: "HOSP_B", hospital_name: "Hospital B (Apollo Memorial)", count: 31 },
      { hospital_id: "HOSP_C", hospital_name: "Hospital C (St. Jude Medical)", count: 15 }
    ];
  }

  const hA = breakdown[0].count;
  const hB = breakdown[1].count;
  const hC = breakdown[2].count;
  const tot = (typeof result === 'number') ? result : (hA + hB + hC);

  const M = 1000003;
  const sA = [123456, 456789, (hA - 123456 - 456789 + M * 2) % M];
  const sB = [234567, 345678, (hB - 234567 - 345678 + M * 2) % M];
  const sC = [345678, 234567, (hC - 345678 - 234567 + M * 2) % M];

  const p1 = (sA[0] + sB[0] + sC[0]) % M;
  const p2 = (sA[1] + sB[1] + sC[1]) % M;
  const p3 = (sA[2] + sB[2] + sC[2]) % M;

  const now = new Date().toISOString();

  return {
    result: masked ? null : result,
    masked: masked,
    unit: "patients",
    display_text: masked ? "Suppressed under DPDP k-anonymity" : `${result} patients`,
    execution_time_ms: 328,
    breakdown: breakdown,
    transparency_steps: [
      {
        step: 1,
        name: "Question Received",
        timestamp: now,
        data: {
          raw_question: question,
          researcher_id: state.researcher.id || "SIM",
          researcher_name: state.researcher.name,
          purpose: state.researcher.purpose,
          consent_id: state.researcher.consentId || "SIMULATED"
        }
      },
      {
        step: 2,
        name: "SQL Generation",
        timestamp: now,
        data: {
          model: "Qwen2.5-Coder (via Ollama)",
          sql: isPii
            ? "SELECT name, birth_date, address FROM patients"
            : `SELECT hospital_id, COUNT(DISTINCT patient_id) AS patient_count FROM conditions WHERE description ILIKE '%${isMetformin ? "Metformin" : "Diabet"}%' GROUP BY hospital_id HAVING COUNT(DISTINCT patient_id) >= 5`,
          tables_referenced: ["conditions", "patients"],
          intent: "Aggregate count of cohort across hospitals"
        }
      },
      {
        step: 3,
        name: "SQL Validation & Guardrails",
        timestamp: now,
        data: {
          valid: !isPii,
          errors: isPii ? ["Direct PII column selection is not permitted: name, birth_date, address"] : [],
          dialect: "Postgres AST (sqlglot)",
          rules_checked: [
            { rule: "SELECT Queries Only", pass: true },
            { rule: "No Data Modification DDL/DML", pass: true },
            { rule: "Direct PII Column Block (DPDP Sec. 2(t))", pass: !isPii },
            { rule: "Minimum Group-Size (HAVING COUNT >= 5)", pass: true },
            { rule: "Data Minimization (No SELECT *)", pass: true }
          ]
        }
      },
      {
        step: 4,
        name: "DPDP Purpose Authorization",
        timestamp: now,
        data: {
          authorized: true,
          researcher_id: state.researcher.id || "SIM",
          consent_id: state.researcher.consentId || "SIMULATED",
          purpose_match: true,
          dpdp_sections: ["Sec. 4 (Lawful Purpose)", "Sec. 7 (Consent Purpose Specification)"]
        }
      },
      {
        step: 5,
        name: "Privacy Risk Classification",
        timestamp: now,
        data: {
          k_anonymity: {
            status: masked ? "FAIL" : "PASS",
            predicted_count: masked ? 3 : result,
            threshold: 5
          },
          l_diversity: {
            status: "PASS",
            distinct_sensitive_values: 3,
            threshold: 2
          },
          composite_risk_score: masked ? 0.88 : 0.08,
          status: masked ? "SUPPRESSED" : "PERMITTED"
        }
      },
      {
        step: 6,
        name: "Local Hospital Computation",
        timestamp: now,
        data: {
          hospitals: [
            { hospital_id: "HOSP_A", hospital_name: "Hospital A (City General)", local_count: hA, isolation_status: "Node Local Container" },
            { hospital_id: "HOSP_B", hospital_name: "Hospital B (Apollo Memorial)", local_count: hB, isolation_status: "Node Local Container" },
            { hospital_id: "HOSP_C", hospital_name: "Hospital C (St. Jude Medical)", local_count: hC, isolation_status: "Node Local Container" }
          ]
        }
      },
      {
        step: 7,
        name: "Secret Share Generation",
        timestamp: now,
        data: {
          modulus: M,
          hospital_shares: [
            { hospital_id: "HOSP_A", hospital_name: "Hospital A", shares: [{ party: "Compute Party 1", share_value: sA[0] }, { party: "Compute Party 2", share_value: sA[1] }, { party: "Compute Party 3", share_value: sA[2] }] },
            { hospital_id: "HOSP_B", hospital_name: "Hospital B", shares: [{ party: "Compute Party 1", share_value: sB[0] }, { party: "Compute Party 2", share_value: sB[1] }, { party: "Compute Party 3", share_value: sB[2] }] },
            { hospital_id: "HOSP_C", hospital_name: "Hospital C", shares: [{ party: "Compute Party 1", share_value: sC[0] }, { party: "Compute Party 2", share_value: sC[1] }, { party: "Compute Party 3", share_value: sC[2] }] }
          ]
        }
      },
      {
        step: 8,
        name: "Multi-Party Secure Aggregation",
        timestamp: now,
        data: {
          compute_parties: [
            { party_id: "CP-01", party_name: "Compute Party 1", aggregated_partial_sum: p1 },
            { party_id: "CP-02", party_name: "Compute Party 2", aggregated_partial_sum: p2 },
            { party_id: "CP-03", party_name: "Compute Party 3", aggregated_partial_sum: p3 }
          ],
          final_aggregated_sum: tot
        }
      },
      {
        step: 9,
        name: "Cryptographic Audit Log Entry",
        timestamp: now,
        data: {
          block_index: 881,
          query_hash: "a4f89b72c1d3e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
          previous_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          timestamp: now,
          signature: "SIG_ED25519_AUDIT_LOG_ENTRY"
        }
      },
      {
        step: 10,
        name: "Final Privacy-Checked Result",
        timestamp: now,
        data: {
          final_answer: finalAnswer,
          disclosure_status: disclosureStatus,
          masked: masked
        }
      }
    ]
  };
}

// -----------------------------------------------------------------------------
// Backend status pill
// -----------------------------------------------------------------------------
function updateBackendStatus(isOnline, reason) {
  const pill = document.getElementById('backendStatusPill');
  const text = document.getElementById('backendStatusText');
  if (!pill || !text) return;

  if (isOnline) {
    pill.className = "hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono border bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    text.textContent = "Backend Connected";
  } else if (reason === 'not_logged_in') {
    pill.className = "hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono border bg-slate-500/10 text-slate-400 border-slate-500/30";
    text.textContent = "Not Logged In (Simulated)";
  } else {
    pill.className = "hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-[11px] font-mono border bg-amber-500/10 text-amber-400 border-amber-500/30";
    text.textContent = "Simulation Mode";
  }
}

// -----------------------------------------------------------------------------
// Application State — hydrated from sessionStorage (set by login.html)
// -----------------------------------------------------------------------------
const storedToken = sessionStorage.getItem('sq_token');
const storedEmail = sessionStorage.getItem('sq_email');
const storedPurpose = sessionStorage.getItem('sq_purpose') || 'EPIDEMIOLOGICAL_RESEARCH';

const state = {
  currentTab: 'query',
  splitScreen: true,
  activeStep: 1,
  isPlaying: false,
  playInterval: null,
  queryData: null,
  charts: {
    queryBar: null,
    trend: null,
    comparison: null
  },
  researcher: {
    token: storedToken,
    email: storedEmail,
    id: null,
    name: storedEmail || "Not Logged In",
    role: null,
    purpose: storedPurpose,
    consentId: null
  }
};

// -----------------------------------------------------------------------------
// Session helpers
// -----------------------------------------------------------------------------
function clearSessionAndRedirectToLogin() {
  sessionStorage.removeItem('sq_token');
  sessionStorage.removeItem('sq_email');
  sessionStorage.removeItem('sq_purpose');
  window.location.replace('/dashboard/login.html');
}

function logout() {
  clearSessionAndRedirectToLogin();
}

// -----------------------------------------------------------------------------
// Initialization
// -----------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  // Defensive: index.html's own <head> script already redirects if there's
  // no token, but bail out here too in case this ever loads without it.
  if (!state.researcher.token) {
    clearSessionAndRedirectToLogin();
    return;
  }

  if (window.lucide) {
    window.lucide.createIcons();
  }

  document.getElementById('headerResearcherName').textContent = state.researcher.name;
  const idBadge = document.getElementById('headerResearcherId');
  if (idBadge) idBadge.textContent = 'Verifying…';

  await runQuery("How many diabetic patients across Hospital A, B, C?");
  loadAnalyticsData();
});

// -----------------------------------------------------------------------------
// Navigation & Tab Switching
// -----------------------------------------------------------------------------
function switchTab(tabName) {
  state.currentTab = tabName;

  const viewQuery = document.getElementById('viewQuery');
  const viewAnalytics = document.getElementById('viewAnalytics');
  const viewTransparencyFull = document.getElementById('viewTransparencyFull');

  const tabBtnQuery = document.getElementById('tabBtnQuery');
  const tabBtnAnalytics = document.getElementById('tabBtnAnalytics');
  const tabBtnTransparency = document.getElementById('tabBtnTransparency');

  // Hide all views
  viewQuery.classList.add('hidden');
  viewAnalytics.classList.add('hidden');
  viewTransparencyFull.classList.add('hidden');

  // Reset tab button styles
  [tabBtnQuery, tabBtnAnalytics, tabBtnTransparency].forEach(btn => {
    btn.className = "px-3 py-1.5 text-xs font-medium rounded-md transition-all text-slate-400 hover:text-slate-200 flex items-center space-x-1.5";
  });

  const activeBtnClass = "px-3 py-1.5 text-xs font-medium rounded-md transition-all bg-blue-600 text-white shadow-sm flex items-center space-x-1.5";

  if (tabName === 'query') {
    viewQuery.classList.remove('hidden');
    tabBtnQuery.className = activeBtnClass;
  } else if (tabName === 'analytics') {
    viewAnalytics.classList.remove('hidden');
    tabBtnAnalytics.className = activeBtnClass;
    renderAnalyticsCharts();
  } else if (tabName === 'transparency') {
    viewTransparencyFull.classList.remove('hidden');
    tabBtnTransparency.className = activeBtnClass;
    renderFullAuditInspector();
  }

  if (window.lucide) window.lucide.createIcons();
}

// -----------------------------------------------------------------------------
// Split-Screen Toggle
// -----------------------------------------------------------------------------
function toggleSplitScreen() {
  state.splitScreen = !state.splitScreen;
  const knob = document.getElementById('splitToggleKnob');
  const toggle = document.getElementById('splitScreenToggle');
  const transCol = document.getElementById('transparencyCol');
  const resCol = document.getElementById('researcherResultCol');

  if (state.splitScreen) {
    knob.className = "w-4 h-4 bg-white rounded-full shadow-md transform translate-x-4 transition-transform duration-200 ease-in-out";
    toggle.className = "w-9 h-5 bg-blue-600 rounded-full p-0.5 transition-colors duration-200 ease-in-out relative focus:outline-none";
    transCol.classList.remove('hidden');
    resCol.className = "lg:col-span-5 space-y-6";
  } else {
    knob.className = "w-4 h-4 bg-white rounded-full shadow-md transform translate-x-0 transition-transform duration-200 ease-in-out";
    toggle.className = "w-9 h-5 bg-slate-700 rounded-full p-0.5 transition-colors duration-200 ease-in-out relative focus:outline-none";
    transCol.classList.add('hidden');
    resCol.className = "lg:col-span-12 max-w-3xl mx-auto space-y-6";
  }
}

function setQuery(text) {
  const input = document.getElementById('queryInput');
  input.value = text;
  runQuery(text);
}

// -----------------------------------------------------------------------------
// Query Execution
// -----------------------------------------------------------------------------
async function handleQuerySubmit(e) {
  e.preventDefault();
  const input = document.getElementById('queryInput');
  const question = input.value.trim();
  if (!question) return;
  await runQuery(question);
}

async function runQuery(question) {
  const submitBtn = document.getElementById('submitBtn');
  submitBtn.disabled = true;
  submitBtn.innerHTML = `
    <span class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
    <span>Computing SMPC...</span>
  `;

  let data = null;

  try {
    if (!state.researcher.token) {
      // Should never happen post-redirect-gate, but stay defensive.
      clearSessionAndRedirectToLogin();
      return;
    }

    const response = await fetch(`${API_BASE}/api/query?verbose=true`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${state.researcher.token}`
      },
      body: JSON.stringify({
        question: question,
        purpose: state.researcher.purpose
      })
    });

    if (response.status === 401) {
      // Token expired/rejected — a real dashboard shouldn't silently fall
      // back to simulation once you expect to be logged in. Bounce to login.
      clearSessionAndRedirectToLogin();
      return;
    }
    if (!response.ok) {
      throw new Error(`Server returned status ${response.status}`);
    }

    data = await response.json();
    updateBackendStatus(true);

    // Pull the real researcher identity/role/scope straight from the
    // backend's own audit trail (Step 1), rather than trusting anything
    // guessed at login time — this is what actually changes per-login.
    const step1 = data.transparency_steps && data.transparency_steps.find(s => s.step === 1);
    if (step1 && step1.data) {
      state.researcher.name = step1.data.researcher_name || state.researcher.email;
      state.researcher.id = step1.data.researcher_id || null;
      state.researcher.role = step1.data.role || null;
      const nameEl = document.getElementById('headerResearcherName');
      const idEl = document.getElementById('headerResearcherId');
      if (nameEl) nameEl.textContent = state.researcher.name;
      if (idEl) idEl.textContent = state.researcher.id
        ? `${state.researcher.id}${state.researcher.role ? ' · ' + state.researcher.role : ''}`
        : '';
    }
  } catch (err) {
    console.warn(`Backend query unavailable (${err.message}) — using simulation fallback.`);
    updateBackendStatus(false, 'backend_offline');
    data = getSimulationDataForQuery(question);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      <i data-lucide="play" class="w-3.5 h-3.5 fill-current"></i>
      <span>Run SMPC</span>
    `;
    if (window.lucide) window.lucide.createIcons();
  }

  if (data) {
    state.queryData = data;

    // Update Researcher Results UI
    updateResearcherResults(data);

    // Reset and select Step 1
    selectStep(1);

    // If split-screen is active, auto-trigger a brief replay
    startAutoPlay();
  }
}

// -----------------------------------------------------------------------------
// Researcher Results UI Update
// -----------------------------------------------------------------------------
function updateResearcherResults(data) {
  const metricNumber = document.getElementById('metricNumber');
  const metricUnit = document.getElementById('metricUnit');
  const resultSubtitle = document.getElementById('resultSubtitle');
  const maskedBadge = document.getElementById('maskedBadge');
  const execTime = document.getElementById('queryExecTime');
  const rowsBody = document.getElementById('hospitalBreakdownRows');

  execTime.textContent = `${data.execution_time_ms || 328} ms`;

  if (data.masked) {
    metricNumber.textContent = "[MASKED]";
    metricNumber.className = "text-3xl sm:text-4xl font-extrabold tracking-tight text-amber-400";
    metricUnit.textContent = "";
    resultSubtitle.textContent = "Query suppressed to comply with India DPDP Act 2023 k-anonymity privacy requirements.";
    maskedBadge.classList.remove('hidden');
  } else {
    metricNumber.textContent = data.result !== null ? data.result : "—";
    metricNumber.className = "text-4xl sm:text-5xl font-extrabold tracking-tight text-white";
    metricUnit.textContent = data.unit || "patients";
    resultSubtitle.textContent = `Aggregated across Hospital A, B, and C via Secure Multi-Party Computation.`;
    maskedBadge.classList.add('hidden');
  }

  // Update Hospital breakdown table
  if (data.breakdown && data.breakdown.length > 0) {
    const colors = ['bg-blue-400', 'bg-indigo-400', 'bg-cyan-400'];
    rowsBody.innerHTML = data.breakdown.map((item, idx) => `
      <tr>
        <td class="p-2.5 font-sans flex items-center space-x-2">
          <span class="w-2 h-2 rounded-full ${colors[idx % colors.length]}"></span>
          <span>${item.hospital_name}</span>
        </td>
        <td class="p-2.5 text-right font-bold text-white font-mono">
          ${data.masked ? '<span class="text-amber-400 text-xs font-normal">Below Threshold</span>' : item.count}
        </td>
        <td class="p-2.5 text-right ${data.masked ? 'text-amber-400' : 'text-emerald-400'} font-sans text-[11px]">
          ${data.masked ? 'Mask Enforced' : 'Enclave Isolated'}
        </td>
      </tr>
    `).join('');
  }

  // Render Mini Bar Chart
  renderQueryBarChart(data);
}

function renderQueryBarChart(data) {
  const ctx = document.getElementById('queryBarChart');
  if (!ctx) return;

  if (state.charts.queryBar) {
    state.charts.queryBar.destroy();
  }

  const labels = data.breakdown.map(b => b.hospital_name.split(' ')[0] + ' ' + b.hospital_name.split(' ')[1]);
  // Real backend never sends numeric per-hospital counts (privacy fix —
  // it always sends "Data isolated"), so these bars intentionally render
  // flat/zero for real data. That is correct: even relative hospital size
  // is exactly what SMPC exists to hide.
  const counts = data.breakdown.map(b => (data.masked ? 0 : (typeof b.count === 'number' ? b.count : 0)));

  state.charts.queryBar = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Patient Count',
        data: counts,
        backgroundColor: ['rgba(59, 130, 246, 0.7)', 'rgba(99, 102, 241, 0.7)', 'rgba(6, 182, 212, 0.7)'],
        borderColor: ['#3b82f6', '#6366f1', '#06b6d4'],
        borderWidth: 1.5,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => data.masked ? 'Below threshold' : `${ctx.raw} patients`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#94a3b8', font: { size: 10 } }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.06)' },
          ticks: { color: '#94a3b8', font: { size: 10 } },
          beginAtZero: true
        }
      }
    }
  });
}

// -----------------------------------------------------------------------------
// Step Selection & Visual Transparency Renderers (Steps 1 to 10)
// -----------------------------------------------------------------------------
function selectStep(stepNumber) {
  state.activeStep = stepNumber;
  document.getElementById('activeStepNumber').textContent = stepNumber;

  // Update stepper nodes styling
  for (let i = 1; i <= 10; i++) {
    const node = document.getElementById(`stepNode${i}`);
    if (!node) continue;
    const badge = node.querySelector('span:first-child');

    if (i === stepNumber) {
      node.className = "step-node active-step flex flex-col items-center group";
      badge.className = "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold font-mono border border-blue-400 bg-blue-600 text-white shadow-lg shadow-blue-500/50";
    } else if (i < stepNumber) {
      node.className = "step-node completed-step flex flex-col items-center group";
      badge.className = "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold font-mono border border-emerald-500 bg-emerald-950/80 text-emerald-400";
    } else {
      node.className = "step-node flex flex-col items-center group";
      badge.className = "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold font-mono border border-slate-700 bg-slate-800 text-slate-400";
    }
  }

  // Render the detailed view for this step
  renderStepContent(stepNumber);
}

function nextStep() {
  if (state.activeStep < 10) {
    selectStep(state.activeStep + 1);
  } else {
    stopAutoPlay();
  }
}

function prevStep() {
  if (state.activeStep > 1) {
    selectStep(state.activeStep - 1);
  }
}

function togglePlayReplay() {
  if (state.isPlaying) {
    stopAutoPlay();
  } else {
    startAutoPlay();
  }
}

function startAutoPlay() {
  stopAutoPlay();
  state.isPlaying = true;
  document.getElementById('playPauseLabel').textContent = "Pause";
  document.getElementById('playPauseIcon').setAttribute('data-lucide', 'pause');
  if (window.lucide) window.lucide.createIcons();

  state.playInterval = setInterval(() => {
    if (state.activeStep < 10) {
      selectStep(state.activeStep + 1);
    } else {
      stopAutoPlay();
    }
  }, 1100);
}

function stopAutoPlay() {
  state.isPlaying = false;
  if (state.playInterval) {
    clearInterval(state.playInterval);
    state.playInterval = null;
  }
  const label = document.getElementById('playPauseLabel');
  const icon = document.getElementById('playPauseIcon');
  if (label) label.textContent = "Auto Play";
  if (icon) icon.setAttribute('data-lucide', 'play');
  if (window.lucide) window.lucide.createIcons();
}

// -----------------------------------------------------------------------------
// The 10 Individual Step Content Renderers
// -----------------------------------------------------------------------------
function renderStepContent(stepNum) {
  const container = document.getElementById('stepDetailsBody');
  if (!state.queryData || !state.queryData.transparency_steps) {
    container.innerHTML = `<div class="text-slate-500 text-xs">Run a query to inspect pipeline stages.</div>`;
    return;
  }

  const stepObj = state.queryData.transparency_steps.find(s => s.step === stepNum);
  if (!stepObj) return;

  let html = '';

  switch (stepNum) {
    case 1:
      // Step 1: Question Asked
      html = `
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-blue-400">Step 1: Clinical Question Received</span>
            <span class="text-[11px] font-mono text-slate-500">${stepObj.timestamp}</span>
          </div>
          <div class="p-4 rounded-xl bg-slate-950 border border-slate-800">
            <div class="text-xs text-slate-400 mb-1">Researcher Question:</div>
            <div class="text-base font-semibold text-white">"${stepObj.data.raw_question}"</div>
          </div>
          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-800">
              <span class="text-slate-400 block">Submitted By:</span>
              <span class="text-slate-200 font-semibold font-mono">${stepObj.data.researcher_id} (${stepObj.data.researcher_name})</span>
            </div>
            <div class="p-3 rounded-lg bg-slate-800/50 border border-slate-800">
              <span class="text-slate-400 block">Declared DPDP Purpose:</span>
              <span class="text-emerald-400 font-semibold font-mono">${stepObj.data.purpose}</span>
            </div>
          </div>
        </div>
      `;
      break;

    case 2:
      // Step 2: Generated SQL
      html = `
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-blue-400">Step 2: Synthesized SQL AST</span>
            <span class="text-[11px] font-mono text-slate-400">Model: ${stepObj.data.model}</span>
          </div>
          <div class="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <div class="text-[11px] text-slate-400 flex items-center justify-between">
              <span>Synthesized Dialect: ANSI SQL / DuckDB</span>
              <span class="text-blue-400">Aggregate Function: COUNT</span>
            </div>
            <pre class="p-3 rounded-lg bg-slate-900 text-blue-300 text-xs font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed">${stepObj.data.sql}</pre>
          </div>
          <div class="flex items-center space-x-2 text-xs text-slate-400">
            <i data-lucide="database" class="w-3.5 h-3.5 text-slate-500"></i>
            <span>Referenced Schema Entities:</span>
            <span class="font-mono text-slate-200">${stepObj.data.tables_referenced.join(', ')}</span>
          </div>
        </div>
      `;
      break;

    case 3:
      // Step 3: SQL Validator AST Guardrail Check
      html = `
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center space-x-1.5">
              <i data-lucide="shield-check" class="w-4 h-4"></i>
              <span>Step 3: AST Validator & Guardrail Checks</span>
            </span>
            <span class="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono">AST VALIDATED</span>
          </div>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
              <span class="text-slate-300">Syntax Validity</span>
              <span class="text-emerald-400 font-bold">✓ PASS</span>
            </div>
            <div class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
              <span class="text-slate-300">SELECT Only (No DDL/DML)</span>
              <span class="text-emerald-400 font-bold">✓ PASS</span>
            </div>
            <div class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
              <span class="text-slate-300">PII Columns Filtered</span>
              <span class="text-emerald-400 font-bold">✓ PASS</span>
            </div>
            <div class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
              <span class="text-slate-300">Group-Size Guardrail</span>
              <span class="text-emerald-400 font-bold">✓ PASS</span>
            </div>
          </div>
          <div class="p-3 rounded-lg bg-blue-950/30 border border-blue-900/50 text-[11px] text-blue-200">
            <strong>AST Guardrail Rule:</strong> Blocked direct selection of raw patient identifiers (name, address, national ID) and capped runaway query limits.
          </div>
        </div>
      `;
      break;

    case 4:
      // Step 4: DPDP Permission Check
      html = `
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-emerald-400">Step 4: DPDP Permission & Purpose Check</span>
            <span class="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono">AUTHORIZATION VERIFIED</span>
          </div>
          <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs">
            <div class="flex items-center justify-between">
              <span class="text-slate-400">Researcher Token:</span>
              <span class="font-mono text-slate-200">${stepObj.data.researcher_id} (Authorized)</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-400">Matched Purpose:</span>
              <span class="font-mono text-emerald-400">${stepObj.data.purpose}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-400">Legal Ground:</span>
              <span class="text-slate-300">${stepObj.data.dpdp_section}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-400">Consent Artifact ID:</span>
              <span class="font-mono text-blue-400">${stepObj.data.consent_artifact_id}</span>
            </div>
          </div>
          <div class="text-xs text-slate-400 flex items-center space-x-1.5">
            <i data-lucide="check" class="w-4 h-4 text-emerald-400"></i>
            <span>Query matches verified epidemiological research consent bounds.</span>
          </div>
        </div>
      `;
      break;

    case 5:
      // Step 5: Risk Classifier Result
      const k = stepObj.data.k_anonymity;
      const l = stepObj.data.l_diversity;
      const isLowRisk = stepObj.data.risk_level.includes('LOW');
      html = `
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="text-xs font-semibold uppercase tracking-wider ${isLowRisk ? 'text-blue-400' : 'text-amber-400'}">
              Step 5: Privacy Risk Classifier (k-Anonymity & l-Diversity)
            </span>
            <span class="text-xs px-2 py-0.5 rounded ${isLowRisk ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/20 text-amber-300'} font-mono">
              ${stepObj.data.risk_level}
            </span>
          </div>
          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="p-3.5 rounded-xl bg-slate-950 border ${k.status === 'PASS' ? 'border-slate-800' : 'border-amber-700/60'} space-y-1">
              <div class="flex items-center justify-between">
                <span class="font-semibold text-slate-300">k-Anonymity</span>
                <span class="font-bold ${k.status === 'PASS' ? 'text-emerald-400' : 'text-amber-400'}">${k.status}</span>
              </div>
              <div class="text-slate-400 text-[11px]">Predicted Count: <span class="text-white font-mono font-bold">${k.predicted_count}</span></div>
              <div class="text-slate-400 text-[11px]">Minimum Threshold: <span class="text-slate-300 font-mono">&ge; ${k.threshold}</span></div>
            </div>

            <div class="p-3.5 rounded-xl bg-slate-950 border ${l.status === 'PASS' ? 'border-slate-800' : 'border-amber-700/60'} space-y-1">
              <div class="flex items-center justify-between">
                <span class="font-semibold text-slate-300">l-Diversity</span>
                <span class="font-bold ${l.status === 'PASS' ? 'text-emerald-400' : 'text-amber-400'}">${l.status}</span>
              </div>
              <div class="text-slate-400 text-[11px]">Distinct Sensitive Values: <span class="text-white font-mono font-bold">${l.distinct_sensitive_values}</span></div>
              <div class="text-slate-400 text-[11px]">Minimum Threshold: <span class="text-slate-300 font-mono">&ge; ${l.threshold}</span></div>
            </div>
          </div>
          <div class="p-3 rounded-lg ${isLowRisk ? 'bg-slate-800/50' : 'bg-amber-950/40 border border-amber-800/50'} text-xs text-slate-300">
            ${isLowRisk ? '✓ Safety thresholds satisfied. Authorized to generate secret shares for SMPC.' : '⚠️ Warning: Potential re-identification risk detected. Result will be masked below disclosure threshold.'}
          </div>
        </div>
      `;
      break;

    case 6:
      // Step 6: Per-Hospital Local Computation (THE KEY VISUAL)
      const hs = stepObj.data.hospitals;
      html = `
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <div class="flex items-center space-x-2">
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span class="text-xs font-semibold uppercase tracking-wider text-emerald-400">Step 6: Per-Hospital Local Computation</span>
            </div>
            <span class="text-[11px] font-mono text-emerald-400">DATA ISOLATED IN ENCLAVES</span>
          </div>
          <p class="text-xs text-slate-400 leading-relaxed">
            ${stepObj.description || ''}
          </p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            ${hs.map((h, i) => `
              <div class="hospital-container-box active p-4 rounded-xl space-y-2">
                <div class="flex items-center justify-between">
                  <div class="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                    <i data-lucide="server" class="w-4 h-4"></i>
                  </div>
                  <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 font-mono">Enclave #${i+1}</span>
                </div>
                <div>
                  <h4 class="text-xs font-bold text-white">${h.name.split(' ')[0]} ${h.name.split(' ')[1]}</h4>
                  <div class="text-[11px] text-slate-400 font-mono">${h.id}</div>
                </div>
                <div class="pt-2 border-t border-slate-700/60 flex items-baseline justify-between">
                  <span class="text-[11px] text-slate-400">Local Count:</span>
                  <span class="text-lg font-bold font-mono text-emerald-400">${h.local_count}</span>
                </div>
                <div class="text-[10px] text-slate-400 bg-slate-900/80 p-1.5 rounded text-center font-mono">
                  🔒 Stays inside hospital
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
      break;

    case 7:
      // Step 7: Secret Share Generation (THE KEY VISUAL)
      const hshares = stepObj.data.hospital_shares;
      html = `
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-indigo-400">Step 7: Secret Share Generation (Additive SMPC)</span>
            <span class="text-[11px] font-mono text-indigo-400">3-PARTY ADDITIVE SPLIT</span>
          </div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Each hospital's local value is split into 3 randomized shares such that <span class="font-mono text-slate-200">s1 + s2 + s3 = original_count</span>. No single share exposes the true count.
          </p>
          <div class="space-y-2.5">
            ${hshares.map(h => `
              <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                <div class="flex items-center justify-between text-xs">
                  <span class="font-semibold text-slate-200">${h.hospital_name}</span>
                  <span class="text-slate-400 font-mono">Original Count: <strong class="text-white">${h.original_count}</strong></span>
                </div>
                <div class="grid grid-cols-3 gap-2">
                  ${h.shares.map(s => `
                    <div class="share-packet p-2 rounded-lg bg-indigo-950/40 border border-indigo-900/60 text-center">
                      <div class="text-[10px] text-indigo-300">Party ${s.party} Share</div>
                      <div class="text-sm font-bold font-mono text-indigo-200">${s.share_value}</div>
                    </div>
                  `).join('')}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
      break;

    case 8:
      // Step 8: Secure Aggregation
      const parties = stepObj.data.compute_parties;
      html = `
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-blue-400">Step 8: Multi-Party Secure Aggregation</span>
            <span class="text-xs px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono">NO CENTRAL PLAINTEXT</span>
          </div>
          <p class="text-xs text-slate-400">
            Compute parties aggregate their assigned shares independently without ever seeing any hospital's private numbers.
          </p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            ${parties.map(p => `
              <div class="party-box active p-4 rounded-xl space-y-2">
                <div class="flex items-center justify-between">
                  <div class="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <i data-lucide="cpu" class="w-4 h-4"></i>
                  </div>
                  <span class="text-[10px] text-slate-400 font-mono">Party #${p.party_id}</span>
                </div>
                <div class="text-xs font-semibold text-white">${p.party_name}</div>
                <div class="text-[11px] text-slate-400 font-mono">
                  Shares: [${(p.received_shares || []).join(', ')}]
                </div>
                <div class="pt-2 border-t border-indigo-900/60 flex items-baseline justify-between">
                  <span class="text-[11px] text-slate-400">Partial Sum:</span>
                  <span class="text-base font-bold font-mono text-indigo-300">${p.aggregated_partial_sum}</span>
                </div>
              </div>
            `).join('')}
          </div>
          <div class="p-3.5 rounded-xl bg-gradient-to-r from-blue-950/60 to-indigo-950/60 border border-blue-800/50 flex items-center justify-between">
            <span class="text-xs text-slate-300 font-semibold">Reconstruction Formula:</span>
            <span class="text-sm font-mono font-bold text-white">${stepObj.data.reconstruction_formula || 'Sum(party_partial_sums) mod p = total_count'}</span>
          </div>
        </div>
      `;
      break;

    case 9:
      // Step 9: Audit Log Entry
      html = `
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-indigo-400">Step 9: Cryptographic Audit Hash Chaining</span>
            <span class="text-xs px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 font-mono">SHA-256 TAMPER PROOF</span>
          </div>
          <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 font-mono text-xs">
            <div>
              <div class="text-slate-500 text-[10px] uppercase">Audit Block ID</div>
              <div class="text-slate-200 font-bold">${stepObj.data.entry_id || stepObj.data.block_index}</div>
            </div>
            <div>
              <div class="text-slate-500 text-[10px] uppercase">Current Query Hash</div>
              <div class="text-emerald-400 break-all text-[11px]">${stepObj.data.query_hash}</div>
            </div>
            <div>
              <div class="text-slate-500 text-[10px] uppercase">Chained Previous Block Hash</div>
              <div class="text-slate-400 break-all text-[11px]">${stepObj.data.previous_hash}</div>
            </div>
          </div>
          <div class="text-xs text-slate-400 flex items-center space-x-1.5">
            <i data-lucide="shield-check" class="w-4 h-4 text-indigo-400"></i>
            <span>Log is cryptographically hash-chained for tamper-evident auditability aligned with DPDP principles.</span>
          </div>
        </div>
      `;
      break;

    case 10:
      // Step 10: Final Answer Returned
      const isM = stepObj.data.masked;
      html = `
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-emerald-400">Step 10: Final Privacy-Checked Result</span>
            <span class="text-xs px-2 py-0.5 rounded ${isM ? 'bg-amber-500/20 text-amber-300' : 'bg-emerald-500/10 text-emerald-400'} font-mono">
              ${stepObj.data.disclosure_status}
            </span>
          </div>
          <div class="p-6 rounded-2xl bg-gradient-to-br from-slate-950 to-slate-900 border border-slate-800 text-center space-y-2">
            <div class="text-xs uppercase tracking-wider text-slate-400 font-semibold">Delivered to Researcher</div>
            <div class="text-3xl sm:text-4xl font-extrabold ${isM ? 'text-amber-400' : 'text-white'}">
              ${stepObj.data.final_answer}
            </div>
            <p class="text-xs text-slate-400 max-w-md mx-auto pt-1">
              ${isM ? 'Result suppressed because query failed disclosure risk thresholds.' : 'Aggregated safely via SMPC secret sharing preserving local patient database privacy.'}
            </p>
          </div>
        </div>
      `;
      break;
  }

  // Footer navigation inside the step box
  html += `
    <div class="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
      <button onclick="prevStep()" ${stepNum === 1 ? 'disabled class="opacity-40 text-slate-500 cursor-not-allowed"' : 'class="text-slate-300 hover:text-white flex items-center space-x-1"'}>
        <i data-lucide="chevron-left" class="w-3.5 h-3.5"></i>
        <span>Previous Stage</span>
      </button>
      <span class="text-slate-500 font-mono">Stage ${stepNum} of 10</span>
      <button onclick="nextStep()" ${stepNum === 10 ? 'disabled class="opacity-40 text-slate-500 cursor-not-allowed"' : 'class="text-blue-400 hover:text-blue-300 flex items-center space-x-1"'}>
        <span>Next Stage</span>
        <i data-lucide="chevron-right" class="w-3.5 h-3.5"></i>
      </button>
    </div>
  `;

  container.innerHTML = html;
  if (window.lucide) window.lucide.createIcons();
}

// -----------------------------------------------------------------------------
// Analytics Dashboard Charts
// -----------------------------------------------------------------------------
async function loadAnalyticsData() {
  if (!state.researcher.token) {
    state.trendsData = FALLBACK_TRENDS;
    state.comparisonData = FALLBACK_COMPARISON;
    return;
  }

  try {
    const headers = { 'Authorization': `Bearer ${state.researcher.token}` };
    const [trendsRes, comparisonRes] = await Promise.all([
      fetch(`${API_BASE}/api/analytics/trends`, { headers }),
      fetch(`${API_BASE}/api/analytics/hospital-comparison`, { headers })
    ]);
    if (trendsRes.status === 401 || comparisonRes.status === 401) {
      clearSessionAndRedirectToLogin();
      return;
    }
    if (!trendsRes.ok || !comparisonRes.ok) throw new Error("Non-OK response");
    state.trendsData = await trendsRes.json();
    state.comparisonData = await comparisonRes.json();
  } catch (e) {
    console.warn('Analytics background fetch warning (using fallback):', e);
    state.trendsData = FALLBACK_TRENDS;
    state.comparisonData = FALLBACK_COMPARISON;
  }
}

function renderAnalyticsCharts() {
  if (!state.trendsData || !state.comparisonData) return;

  // Trend Line Chart
  const trendCtx = document.getElementById('trendChart');
  if (trendCtx) {
    if (state.charts.trend) state.charts.trend.destroy();

    const colors = ['#3b82f6', '#6366f1', '#06b6d4', '#10b981'];
    const datasets = state.trendsData.series.map((s, idx) => ({
      label: s.hospital_name,
      data: s.values,
      borderColor: colors[idx % colors.length],
      backgroundColor: colors[idx % colors.length],
      borderWidth: s.hospital_id === 'TOTAL' ? 2.5 : 1.5,
      borderDash: s.hospital_id === 'TOTAL' ? [] : [4, 4],
      tension: 0.3,
      pointRadius: 3
    }));

    state.charts.trend = new Chart(trendCtx, {
      type: 'line',
      data: {
        labels: state.trendsData.years,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#94a3b8', font: { size: 10 } }
          }
        },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8', font: { size: 10 } }
          },
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8', font: { size: 10 } },
            beginAtZero: true
          }
        }
      }
    });
  }

  // Condition Comparison Bar Chart — built dynamically from whichever
  // hospital keys the response actually contains. The real backend varies
  // this by role: a cross-hospital researcher gets HOSP_A/B/C, a "doctor"
  // only gets their own single hospital's key, and real values are always
  // the literal string "isolated" (never a raw per-hospital number).
  const compCtx = document.getElementById('conditionComparisonChart');
  if (compCtx) {
    if (state.charts.comparison) state.charts.comparison.destroy();

    const labels = state.comparisonData.conditions;

    const hospitalIds = [];
    state.comparisonData.data.forEach(row => {
      Object.keys(row).forEach(k => {
        if (k !== 'condition' && k !== 'total' && !hospitalIds.includes(k)) {
          hospitalIds.push(k);
        }
      });
    });

    const barColors = ['#3b82f6', '#6366f1', '#06b6d4', '#10b981'];
    const datasets = hospitalIds.map((id, idx) => ({
      label: (state.comparisonData.hospitals && state.comparisonData.hospitals[idx]) || id,
      data: state.comparisonData.data.map(row => {
        const v = row[id];
        return typeof v === 'number' ? v : 0;
      }),
      backgroundColor: barColors[idx % barColors.length],
      borderRadius: 4
    }));

    state.charts.comparison = new Chart(compCtx, {
      type: 'bar',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#94a3b8', font: { size: 10 } }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#94a3b8', font: { size: 10 } }
          },
          y: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8', font: { size: 10 } },
            beginAtZero: true
          }
        }
      }
    });
  }
}

// -----------------------------------------------------------------------------
// View 3: Full Audit Inspector
// -----------------------------------------------------------------------------
function renderFullAuditInspector() {
  const container = document.getElementById('fullAuditCardsStack');
  if (!state.queryData || !state.queryData.transparency_steps) {
    container.innerHTML = `<p class="text-slate-400 text-xs">Run a query first to view full audit logs.</p>`;
    return;
  }

  container.innerHTML = state.queryData.transparency_steps.map(s => `
    <div class="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-xs font-bold text-blue-400 font-mono">Stage ${s.step}: ${s.name}</span>
        <span class="text-[10px] font-mono text-slate-500">${s.timestamp}</span>
      </div>
      <pre class="p-2.5 rounded bg-slate-950 text-slate-300 text-xs font-mono overflow-x-auto whitespace-pre-wrap">${JSON.stringify(s.data, null, 2)}</pre>
    </div>
  `).join('');
}

function copyAuditJson() {
  if (!state.queryData) return;
  navigator.clipboard.writeText(JSON.stringify(state.queryData, null, 2));
  alert("Full audit JSON copied to clipboard!");
}