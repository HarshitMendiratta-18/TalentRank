// API Endpoint config
const API_BASE_URL = window.location.origin;

// State management
let rankedCandidates = [];
let currentCandidate = null;

// DOM Elements
const jdInput = document.getElementById("jd-input");
const rankBtn = document.getElementById("rank-btn");
const loader = document.getElementById("loader");
const placeholder = document.getElementById("placeholder");
const tableContainer = document.getElementById("table-container");
const tbody = document.getElementById("candidates-tbody");
const searchInput = document.getElementById("candidate-search");
const filterLocation = document.getElementById("filter-location");
const filterNotice = document.getElementById("filter-notice");
const filtersRow = document.getElementById("filters-row");

const resultsMeta = document.getElementById("results-meta");
const metaScanned = document.getElementById("meta-scanned");
const metaFiltered = document.getElementById("meta-filtered");

const detailModal = document.getElementById("detail-modal");
const modalClose = document.getElementById("modal-close");

// Slider DOM bindings
const sliders = {
    semantic: document.getElementById("weight-semantic"),
    skills: document.getElementById("weight-skills"),
    experience: document.getElementById("weight-experience"),
    growth: document.getElementById("weight-growth"),
    behavioral: document.getElementById("weight-behavioral"),
    logistics: document.getElementById("weight-logistics")
};

const valueLabels = {
    semantic: document.getElementById("val-semantic"),
    skills: document.getElementById("val-skills"),
    experience: document.getElementById("val-experience"),
    growth: document.getElementById("val-growth"),
    behavioral: document.getElementById("val-behavioral"),
    logistics: document.getElementById("val-logistics")
};

// Initialize sliders events
Object.keys(sliders).forEach(key => {
    sliders[key].addEventListener("input", (e) => {
        valueLabels[key].textContent = `${e.target.value}%`;
    });
});

// Event Listeners
rankBtn.addEventListener("click", performRanking);
modalClose.addEventListener("click", () => detailModal.style.display = "none");
searchInput.addEventListener("input", applyFilters);
filterLocation.addEventListener("change", applyFilters);
filterNotice.addEventListener("change", applyFilters);

// Dynamic Close Modal on click outside
window.addEventListener("click", (e) => {
    if (e.target === detailModal) {
        detailModal.style.display = "none";
    }
});

async function performRanking() {
    const jdText = jdInput.value.trim();
    if (!jdText) {
        alert("Please enter a job description first.");
        return;
    }

    // Toggle loader
    placeholder.style.display = "none";
    tableContainer.style.display = "none";
    filtersRow.style.display = "none";
    resultsMeta.style.display = "none";
    loader.style.display = "flex";

    // Gather weights
    const rawWeights = {
        semantic: parseInt(sliders.semantic.value),
        skills: parseInt(sliders.skills.value),
        experience: parseInt(sliders.experience.value),
        growth: parseInt(sliders.growth.value),
        behavioral: parseInt(sliders.behavioral.value),
        logistics: parseInt(sliders.logistics.value)
    };

    // Normalize weights so they sum to 1.0
    const total = Object.values(rawWeights).reduce((a, b) => a + b, 0);
    const normalizedWeights = {};
    if (total > 0) {
        Object.keys(rawWeights).forEach(key => {
            normalizedWeights[key] = rawWeights[key] / total;
        });
    } else {
        // Fallback default weights
        Object.keys(rawWeights).forEach(key => {
            normalizedWeights[key] = 1.0 / Object.keys(rawWeights).length;
        });
    }

    const loadAllToggle = document.getElementById("full-dataset-toggle").checked;

    try {
        const response = await fetch(`${API_BASE_URL}/api/rank`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                jd: jdText,
                weights: normalizedWeights,
                load_all: loadAllToggle
            })
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.statusText}`);
        }

        const data = await response.json();
        rankedCandidates = data.ranked_candidates || [];
        
        // Update stats
        metaScanned.textContent = data.total_evaluated || 0;
        metaFiltered.textContent = data.total_filtered || 0;

        renderTable(rankedCandidates);

        loader.style.display = "none";
        tableContainer.style.display = "block";
        filtersRow.style.display = "flex";
        resultsMeta.style.display = "block";

    } catch (error) {
        console.error("Error ranking candidates:", error);
        alert(`An error occurred while shortlisting: ${error.message}`);
        loader.style.display = "none";
        placeholder.style.display = "flex";
    }
}

function renderTable(candidates) {
    tbody.innerHTML = "";
    if (candidates.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 2rem; color: var(--text-muted);">No candidates matching the criteria were found. Try modifying filters or weights.</td></tr>`;
        return;
    }

    candidates.forEach(c => {
        const tr = document.createElement("tr");
        tr.addEventListener("click", () => openDetailModal(c));

        // Score formatting
        const scoreVal = c.score; // 0-100
        const isTop3 = c.rank <= 3;
        const scoreClass = scoreVal >= 75 ? "score-high" : (scoreVal >= 60 ? "score-mid" : "score-muted");
        
        const noticeDays = c.redrob_signals.notice_period_days;
        const noticeText = noticeDays === 0 ? "Immediate" : `${noticeDays} days`;

        tr.innerHTML = `
            <td class="rank-column ${isTop3 ? 'top-3' : ''}">#${c.rank}</td>
            <td>
                <div class="c-name">${c.profile.anonymized_name} <span style="font-size:0.75rem; color:var(--text-muted);">(${c.candidate_id})</span></div>
                <div class="c-headline">${c.profile.headline}</div>
                <div class="c-details-box">
                    <span><i class="fa-solid fa-briefcase"></i> ${c.profile.years_of_experience} yrs exp</span>
                    <span>&bull;</span>
                    <span><i class="fa-solid fa-location-dot"></i> ${c.profile.location}, ${c.profile.country}</span>
                </div>
            </td>
            <td>
                <span class="score-badge ${scoreClass}">${scoreVal}%</span>
            </td>
            <td>
                <span style="font-size:0.85rem; font-weight:500;">${noticeText}</span>
            </td>
            <td>
                <div class="c-reasoning">${c.reasoning}</div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function applyFilters() {
    const query = searchInput.value.toLowerCase().trim();
    const locFilter = filterLocation.value;
    const noticeFilter = filterNotice.value;

    const filtered = rankedCandidates.filter(c => {
        // Search text matching
        const matchText = (c.profile.anonymized_name + " " + c.candidate_id + " " + c.profile.headline).toLowerCase();
        if (query && !matchText.includes(query)) return false;

        // Location matching
        const loc = c.profile.location.toLowerCase();
        const willing = c.redrob_signals.willing_to_relocate;
        if (locFilter === "pune") {
            if (!loc.includes("pune") && !loc.includes("noida") && !loc.includes("delhi") && !loc.includes("ncr")) return false;
        } else if (locFilter === "willing") {
            if (!willing && !loc.includes("pune") && !loc.includes("noida")) return false;
        }

        // Notice period matching
        const notice = c.redrob_signals.notice_period_days;
        if (noticeFilter === "30" && notice > 30) return false;
        if (noticeFilter === "60" && notice > 60) return false;

        return true;
    });

    renderTable(filtered);
}

function openDetailModal(candidate) {
    currentCandidate = candidate;
    
    // Header
    document.getElementById("modal-rank").textContent = `#${candidate.rank}`;
    document.getElementById("modal-name").textContent = candidate.profile.anonymized_name;
    document.getElementById("modal-headline").textContent = candidate.profile.headline;
    document.getElementById("modal-reasoning").textContent = candidate.reasoning;

    // Subscores
    const subscoresContainer = document.getElementById("modal-subscores");
    subscoresContainer.innerHTML = "";
    
    const sub = candidate.sub_scores;
    const scoresToShow = [
        { name: "Semantic Fit", val: `${sub.semantic}%` },
        { name: "Skill Match", val: `${sub.skills}%` },
        { name: "Experience Fit", val: `${sub.experience}%` },
        { name: "Career Growth", val: `${sub.growth}%` },
        { name: "Behavioral Cues", val: `${sub.behavioral}%` },
        { name: "Logistics Score", val: `${sub.logistics}%` }
    ];
    
    scoresToShow.forEach(s => {
        subscoresContainer.innerHTML += `
            <div class="score-metric">
                <div class="metric-title">${s.name}</div>
                <div class="metric-value">${s.val}</div>
            </div>
        `;
    });

    // Add Disqualifier metric
    const disqMult = sub.disq_multiplier;
    const disqClass = disqMult < 1.0 ? "penalty" : "";
    subscoresContainer.innerHTML += `
        <div class="score-metric">
            <div class="metric-title">Trust Multiplier</div>
            <div class="metric-value ${disqClass}">${disqMult}x</div>
        </div>
    `;

    // Timeline
    const timeline = document.getElementById("modal-timeline");
    timeline.innerHTML = "";
    if (candidate.career_history.length === 0) {
        timeline.innerHTML = "<p style='color:var(--text-muted); font-size:0.85rem;'>No career history recorded.</p>";
    } else {
        candidate.career_history.forEach(job => {
            const isCurrent = job.is_current;
            const endText = isCurrent ? "Present" : job.end_date;
            timeline.innerHTML += `
                <div class="timeline-item ${isCurrent ? 'current' : ''}">
                    <div class="timeline-marker"></div>
                    <div class="timeline-info">
                        <span class="t-company">${job.company} (${job.company_size} employees)</span>
                        <span>${job.start_date} &rarr; ${endText} (${job.duration_months} months)</span>
                    </div>
                    <div class="t-title">${job.title} // ${job.industry}</div>
                    <p class="t-desc">${job.description}</p>
                </div>
            `;
        });
    }

    // Signals
    const signals = document.getElementById("modal-signals");
    signals.innerHTML = "";
    const sig = candidate.redrob_signals;
    
    const signalsToShow = [
        { name: "Connection Count", val: sig.connection_count },
        { name: "Profile Completeness", val: `${sig.profile_completeness_score}%` },
        { name: "GitHub Activity", val: sig.github_activity_score === -1 ? "Not Connected" : `${sig.github_activity_score}/100` },
        { name: "Saved by Recruiters (30d)", val: sig.saved_by_recruiters_30d },
        { name: "Recruiter Response Rate", val: `${Math.round(sig.recruiter_response_rate * 100)}%` },
        { name: "Avg Response Time", val: `${sig.avg_response_time_hours} hrs` },
        { name: "Notice Period", val: `${sig.notice_period_days} days` },
        { name: "Expected Salary (LPA)", val: `${sig.expected_salary_range_inr_lpa.min} - ${sig.expected_salary_range_inr_lpa.max} INR` },
        { name: "Willing to Relocate", val: sig.willing_to_relocate ? "Yes" : "No" }
    ];

    signalsToShow.forEach(s => {
        signals.innerHTML += `
            <div class="signal-row">
                <span class="sig-name">${s.name}</span>
                <span class="sig-value">${s.val}</span>
            </div>
        `;
    });

    // Education
    const edu = document.getElementById("modal-edu");
    edu.innerHTML = "";
    if (candidate.education.length === 0) {
        edu.innerHTML = "<p style='color:var(--text-muted); font-size:0.85rem;'>No education history recorded.</p>";
    } else {
        candidate.education.forEach(school => {
            const tierBadge = school.tier !== 'unknown' ? ` <span class="badge" style="font-size:0.6rem; border-color:var(--text-muted); color:var(--text-muted); background:transparent; padding:0 0.3rem;">${school.tier.toUpperCase().replace('_', ' ')}</span>` : '';
            edu.innerHTML += `
                <div class="edu-item">
                    <div class="edu-title">${school.degree} in ${school.field_of_study}${tierBadge}</div>
                    <div class="edu-meta">${school.institution} // ${school.start_year} - ${school.end_year} // Grade: ${school.grade || 'N/A'}</div>
                </div>
            `;
        });
    }

    // Skill tags
    const tags = document.getElementById("modal-skills-tags");
    tags.innerHTML = "";
    candidate.skills.forEach(s => {
        const isExp = s.proficiency === 'expert';
        const isAdv = s.proficiency === 'advanced';
        const tagClass = isExp ? 'expert' : (isAdv ? 'advanced' : '');
        
        tags.innerHTML += `
            <div class="skill-tag ${tagClass}">
                <span>${s.name}</span>
                <span style="font-size:0.65rem; color:var(--text-muted); font-weight:500;">(${s.duration_months} mo)</span>
            </div>
        `;
    });

    detailModal.style.display = "flex";
}
