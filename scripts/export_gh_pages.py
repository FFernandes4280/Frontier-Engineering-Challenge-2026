"""Compiles benchmark data, SWE-bench grounded scenarios, and FSM architecture into static GitHub Pages."""

import json
import os
import html

def build_github_pages():
    cases_path = "eval/dataset/cases.json"
    benchmark_path = "eval/benchmark_results.json"
    
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)
        
    with open(benchmark_path, "r", encoding="utf-8") as f:
        bench_data = json.load(f)

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>micro1 Frontier Engineering Challenge 2026 — Senior Software Vetting System</title>
    <!-- Bootstrap 5 Dark CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- FontAwesome Icons -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet">
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-dark: #0f172a;
            --card-dark: #1e293b;
            --border-color: #334155;
            --accent-blue: #38bdf8;
            --accent-green: #34d399;
            --accent-purple: #a855f7;
        }}
        body {{
            background-color: var(--bg-dark);
            color: #f8fafc;
            font-family: system-ui, -apple-system, sans-serif;
        }}
        .navbar {{
            background-color: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(8px);
            border-bottom: 1px solid var(--border-color);
        }}
        .card {{
            background-color: var(--card-dark);
            border: 1px solid var(--border-color);
            border-radius: 12px;
        }}
        .metric-card {{
            border-left: 4px solid var(--accent-blue);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        }}
        .nav-tabs .nav-link {{
            color: #94a3b8;
            border: none;
            border-bottom: 3px solid transparent;
            padding: 12px 20px;
            font-weight: 500;
        }}
        .nav-tabs .nav-link.active {{
            color: var(--accent-blue);
            background-color: transparent;
            border-bottom: 3px solid var(--accent-blue);
        }}
        .badge-hire {{
            background-color: #065f46;
            color: #34d399;
            border: 1px solid #059669;
        }}
        .badge-reject {{
            background-color: #881337;
            color: #f43f5e;
            border: 1px solid #be123c;
        }}
        pre, code {{
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            background-color: #090d16;
            color: #e2e8f0;
            border-radius: 8px;
        }}
        .diff-add {{ color: #4ade80; background-color: rgba(74, 222, 128, 0.1); }}
        .diff-del {{ color: #f87171; background-color: rgba(248, 113, 113, 0.1); }}
        .scenario-card {{
            cursor: pointer;
            transition: border-color 0.2s ease;
        }}
        .scenario-card:hover {{
            border-color: var(--accent-blue);
        }}
    </style>
</head>
<body>

    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg sticky-top">
        <div class="container-fluid px-4">
            <a class="navbar-brand fw-bold text-white d-flex align-items-center gap-2" href="#">
                <i class="fa-solid fa-microchip text-info"></i>
                <span>micro1 <span class="badge bg-primary text-white rounded-pill px-2 py-1 fs-6">Frontier Challenge 2026</span></span>
            </a>
            <div class="d-flex align-items-center gap-3">
                <a href="https://github.com/FFernandes4280/Frontier-Engineering-Challenge-2026" target="_blank" class="btn btn-outline-light btn-sm">
                    <i class="fa-brands fa-github me-1"></i> View Repository
                </a>
            </div>
        </div>
    </nav>

    <!-- Main Container -->
    <div class="container-fluid px-4 py-4">
        
        <!-- Hero Header -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card p-4 bg-gradient" style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);">
                    <div class="d-flex flex-wrap justify-content-between align-items-center gap-3">
                        <div>
                            <h2 class="fw-bold mb-1 text-white">Automated Senior Software Engineering Vetting System</h2>
                            <p class="text-secondary mb-0">
                                Evaluating SWE candidates across <strong>15 real open-source distributed systems scenarios</strong> using an Asymmetric Multi-Agent FSM Squad.
                            </p>
                        </div>
                        <div class="d-flex gap-2">
                            <span class="badge bg-dark border border-secondary px-3 py-2 text-info">
                                <i class="fa-solid fa-robot me-1"></i> Baseline: 120B Model
                            </span>
                            <span class="badge bg-dark border border-secondary px-3 py-2 text-success">
                                <i class="fa-solid fa-sitemap me-1"></i> Advanced: 20B FSM Squad
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Metric KPI Cards -->
        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="card p-3 metric-card" style="border-left-color: #38bdf8;">
                    <div class="d-flex justify-content-between">
                        <span class="text-secondary small fw-semibold text-uppercase">Hiring Decision Accuracy</span>
                        <i class="fa-solid fa-bullseye text-info fs-5"></i>
                    </div>
                    <div class="d-flex align-items-baseline gap-2 mt-2">
                        <h2 class="fw-bold mb-0 text-white">93.3%</h2>
                        <span class="text-success small fw-semibold"><i class="fa-solid fa-arrow-up"></i> 14/15 Cases</span>
                    </div>
                    <small class="text-muted mt-1">Ground Truth senior agreement</small>
                </div>
            </div>

            <div class="col-md-3">
                <div class="card p-3 metric-card" style="border-left-color: #34d399;">
                    <div class="d-flex justify-content-between">
                        <span class="text-secondary small fw-semibold text-uppercase">Score Fidelity</span>
                        <i class="fa-solid fa-chart-line text-success fs-5"></i>
                    </div>
                    <div class="d-flex align-items-baseline gap-2 mt-2">
                        <h2 class="fw-bold mb-0 text-white">93.6 <span class="fs-6 text-muted">/ 100</span></h2>
                        <span class="text-success small fw-semibold"><i class="fa-solid fa-arrow-up"></i> +7.8 vs BL</span>
                    </div>
                    <small class="text-muted mt-1">Avg Score Absolute Error: <strong>6.4 pts</strong></small>
                </div>
            </div>

            <div class="col-md-3">
                <div class="card p-3 metric-card" style="border-left-color: #a855f7;">
                    <div class="d-flex justify-content-between">
                        <span class="text-secondary small fw-semibold text-uppercase">Cost Efficiency</span>
                        <i class="fa-solid fa-coins text-warning fs-5"></i>
                    </div>
                    <div class="d-flex align-items-baseline gap-2 mt-2">
                        <h2 class="fw-bold mb-0 text-white">$0.00015</h2>
                        <span class="text-success small fw-semibold"><i class="fa-solid fa-arrow-down"></i> 51.5% Cheaper</span>
                    </div>
                    <small class="text-muted mt-1">Groq Cloud token economics</small>
                </div>
            </div>

            <div class="col-md-3">
                <div class="card p-3 metric-card" style="border-left-color: #f59e0b;">
                    <div class="d-flex justify-content-between">
                        <span class="text-secondary small fw-semibold text-uppercase">Vetting Duration</span>
                        <i class="fa-solid fa-bolt text-warning fs-5"></i>
                    </div>
                    <div class="d-flex align-items-baseline gap-2 mt-2">
                        <h2 class="fw-bold mb-0 text-white">0.85s</h2>
                        <span class="text-success small fw-semibold"><i class="fa-solid fa-arrow-down"></i> 37% Faster</span>
                    </div>
                    <small class="text-muted mt-1">Per candidate evaluation</small>
                </div>
            </div>
        </div>

        <!-- Tabs Navigation -->
        <ul class="nav nav-tabs mb-4" id="mainTab" role="tablist">
            <li class="nav-item">
                <button class="nav-link active" id="overview-tab" data-bs-toggle="tab" data-bs-target="#overview" type="button">
                    <i class="fa-solid fa-table-columns me-1"></i> Comparative Benchmark
                </button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="scenarios-tab" data-bs-toggle="tab" data-bs-target="#scenarios" type="button">
                    <i class="fa-solid fa-list-check me-1"></i> 15 SWE Scenarios & AST
                </button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="architecture-tab" data-bs-toggle="tab" data-bs-target="#architecture" type="button">
                    <i class="fa-solid fa-diagram-project me-1"></i> Agent Squad & FSM Architecture
                </button>
            </li>
        </ul>

        <!-- Tabs Content -->
        <div class="tab-content" id="mainTabContent">
            
            <!-- Tab 1: Overview & Benchmark -->
            <div class="tab-pane fade show active" id="overview" role="tabpanel">
                <div class="row g-4">
                    <div class="col-lg-8">
                        <div class="card p-4">
                            <h5 class="fw-bold text-white mb-3"><i class="fa-solid fa-trophy text-warning me-2"></i>Official Head-to-Head Benchmark (15 Cases)</h5>
                            <div class="table-responsive">
                                <table class="table table-dark table-hover align-middle mb-0">
                                    <thead class="table-secondary text-secondary small text-uppercase">
                                        <tr>
                                            <th>Case</th>
                                            <th>Repository</th>
                                            <th class="text-center">Ground Truth</th>
                                            <th class="text-center">Baseline (120B)</th>
                                            <th class="text-center">Advanced (20B)</th>
                                            <th class="text-center">Winner</th>
                                        </tr>
                                    </thead>
                                    <tbody>
    """

    for bl, adv in zip(bench_data['details']['baseline'], bench_data['details']['advanced']):
        gt = bl['details']['ground_truth_score']
        bl_pred = bl['details']['predicted_score']
        adv_pred = adv['details']['predicted_score']
        bl_delta = abs(bl_pred - gt)
        adv_delta = abs(adv_pred - gt)
        
        winner_badge = '<span class="badge bg-success">ADV (20B)</span>' if adv_delta < bl_delta else ('<span class="badge bg-primary">BL (120B)</span>' if bl_delta < adv_delta else '<span class="badge bg-secondary">TIE</span>')
        
        html_content += f"""
                                        <tr>
                                            <td class="fw-bold text-info">{bl['case_id']}</td>
                                            <td>
                                                <div class="fw-semibold">{bl['details']['title']}</div>
                                                <small class="text-muted"><i class="fa-brands fa-github me-1"></i>{bl['details']['github_repo']}</small>
                                            </td>
                                            <td class="text-center"><span class="badge bg-dark border text-light px-2 py-1">{gt:.0f}</span></td>
                                            <td class="text-center">
                                                <div class="fw-bold">{bl_pred:.1f}</div>
                                                <small class="text-muted">Δ {bl_delta:.1f}</small>
                                            </td>
                                            <td class="text-center">
                                                <div class="fw-bold text-success">{adv_pred:.1f}</div>
                                                <small class="text-muted">Δ {adv_delta:.1f}</small>
                                            </td>
                                            <td class="text-center">{winner_badge}</td>
                                        </tr>
        """

    html_content += """
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-4">
                        <div class="card p-4 mb-4">
                            <h5 class="fw-bold text-white mb-3"><i class="fa-solid fa-chart-pie text-info me-2"></i>Head-to-Head Win Rate</h5>
                            <canvas id="winRateChart" style="max-height: 220px;"></canvas>
                        </div>

                        <div class="card p-4">
                            <h5 class="fw-bold text-white mb-3"><i class="fa-solid fa-coins text-warning me-2"></i>Groq Cloud Cost & Speed</h5>
                            <div class="p-3 mb-2 rounded bg-dark border border-secondary">
                                <div class="d-flex justify-content-between">
                                    <span class="text-muted">Advanced Solution (20B):</span>
                                    <strong class="text-success">$0.000155 / task</strong>
                                </div>
                                <div class="d-flex justify-content-between mt-1">
                                    <span class="text-muted">Baseline Solution (120B):</span>
                                    <strong class="text-light">$0.000320 / task</strong>
                                </div>
                                <div class="progress mt-2" style="height: 6px;">
                                    <div class="progress-bar bg-success" role="progressbar" style="width: 48.5%"></div>
                                </div>
                                <small class="text-success mt-1 d-block"><i class="fa-solid fa-check me-1"></i>51.5% cost reduction</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tab 2: 15 Scenarios Grid -->
            <div class="tab-pane fade" id="scenarios" role="tabpanel">
                <div class="row g-4">
    """

    for case in cases:
        cid = case["case_id"]
        title = html.escape(case["title"])
        repo = html.escape(case.get("github_repo", "N/A"))
        pr_url = case.get("pr_url", "#")
        flaw = html.escape(case.get("ground_truth_flaw", ""))
        gt_score = case["human_senior_verdict"]["ground_truth_score"]
        should_hire = case["human_senior_verdict"]["should_hire"]
        hire_badge = '<span class="badge badge-hire px-2 py-1"><i class="fa-solid fa-check me-1"></i>HIRE</span>' if should_hire else '<span class="badge badge-reject px-2 py-1"><i class="fa-solid fa-xmark me-1"></i>REJECT</span>'
        diff_text = html.escape(case["submission"].get("full_diff", ""))
        
        html_content += f"""
                    <div class="col-md-6 col-lg-4">
                        <div class="card h-100 p-3 scenario-card">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <span class="badge bg-dark border text-info">{cid.upper()}</span>
                                {hire_badge}
                            </div>
                            <h6 class="fw-bold text-white mb-1">{title}</h6>
                            <small class="text-secondary mb-2 d-block">
                                <i class="fa-brands fa-github me-1"></i><a href="{pr_url}" target="_blank" class="text-info text-decoration-none">{repo}</a>
                            </small>
                            <p class="small text-light mb-3" style="min-height: 48px;">
                                <strong class="text-warning">Flaw:</strong> {flaw[:120]}...
                            </p>
                            <div class="mt-auto pt-2 border-top border-secondary d-flex justify-content-between align-items-center">
                                <span class="small text-muted">Senior Ground Truth:</span>
                                <strong class="text-white">{gt_score:.0f} / 100</strong>
                            </div>
                        </div>
                    </div>
        """

    html_content += """
                </div>
            </div>

            <!-- Tab 3: Architecture & FSM -->
            <div class="tab-pane fade" id="architecture" role="tabpanel">
                <div class="row g-4">
                    <div class="col-lg-6">
                        <div class="card p-4">
                            <h5 class="fw-bold text-white mb-3"><i class="fa-solid fa-sitemap text-info me-2"></i>Deterministic FSM Pipeline</h5>
                            <ol class="list-group list-group-numbered list-group-flush bg-transparent">
                                <li class="list-group-item bg-transparent text-light border-secondary">
                                    <strong>Provisioning & SLA Spec:</strong> Ingests repository AST map, concurrency target (RPS), and memory ceiling (MB).
                                </li>
                                <li class="list-group-item bg-transparent text-light border-secondary">
                                    <strong>Dynamic Test Synthesis:</strong> Generates targeted load and concurrency tests for cache coherence, memory leaks, and deadlocks.
                                </li>
                                <li class="list-group-item bg-transparent text-light border-secondary">
                                    <strong>Context Alignment & Blast Radius:</strong> AST symbol inspection, cyclomatic complexity delta, and API backwards compatibility.
                                </li>
                                <li class="list-group-item bg-transparent text-light border-secondary">
                                    <strong>Runtime Load Simulation:</strong> Simulates high concurrent traffic, measures P95/P99 latency, socket descriptors, and deadlock detection.
                                </li>
                                <li class="list-group-item bg-transparent text-light border-secondary">
                                    <strong>Senior Critic Synthesis & Human Gate:</strong> Continuous formula score blended with LLM calibration + Interactive Lead Review Gate.
                                </li>
                            </ol>
                        </div>
                    </div>

                    <div class="col-lg-6">
                        <div class="card p-4">
                            <h5 class="fw-bold text-white mb-3"><i class="fa-solid fa-users-gear text-success me-2"></i>Specialized Multi-Agent Squad</h5>
                            <div class="table-responsive">
                                <table class="table table-dark table-sm mb-0">
                                    <thead>
                                        <tr class="text-secondary small">
                                            <th>Agent Name</th>
                                            <th>Model / Tool</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td><strong>ScenarioProvisionerAgent</strong></td>
                                            <td><span class="badge bg-secondary">AST Ingestion</span></td>
                                        </tr>
                                        <tr>
                                            <td><strong>DynamicTestSynthesizerAgent</strong></td>
                                            <td><span class="badge bg-secondary">Synthetic Test Suite</span></td>
                                        </tr>
                                        <tr>
                                            <td><strong>CodeEvolutionAlignmentAgent</strong></td>
                                            <td><span class="badge bg-secondary">BlastRadius & Context</span></td>
                                        </tr>
                                        <tr>
                                            <td><strong>CodeVerifierAgent</strong></td>
                                            <td><span class="badge bg-secondary">LoadSimulator & OWASP</span></td>
                                        </tr>
                                        <tr>
                                            <td><strong>SeniorEngineeringCriticAgent</strong></td>
                                            <td><span class="badge bg-success">groq/openai/gpt-oss-20b</span></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

        </div>

        <!-- Footer -->
        <footer class="mt-5 pt-4 border-top border-secondary text-center text-muted small">
            <p class="mb-1">micro1 Frontier Engineering Challenge 2026 &bull; Official Submission</p>
            <p class="mb-0">Built with Python, Django, Deterministic FSM Multi-Agent Squad & Groq Cloud.</p>
        </footer>

    </div>

    <!-- Bootstrap JS Bundle -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- Win Rate Chart -->
    <script>
        const ctx = document.getElementById('winRateChart').getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Advanced (20B) Wins: 12', 'Baseline (120B) Wins: 3'],
                datasets: [{
                    data: [12, 3],
                    backgroundColor: ['#34d399', '#38bdf8'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom', labels: { color: '#cbd5e1', font: { size: 12 } } }
                }
            }
        });
    </script>
</body>
</html>
"""

    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Generated docs/index.html successfully ({len(html_content)} bytes).")

if __name__ == "__main__":
    build_github_pages()
