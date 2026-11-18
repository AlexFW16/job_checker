'use strict';

let config;
let allJobs = [];
let currentFilter = 'all';

function byId(id) {
    return document.getElementById(id);
}

function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function safeJobUrl(value) {
    try {
        const url = new URL(value);
        return ['http:', 'https:'].includes(url.protocol) ? url.href : '#';
    } catch {
        return '#';
    }
}

function parseTimestamp(value) {
    if (!value) return null;
    const text = String(value);
    // Older CI artifacts used naive UTC timestamps; new artifacts carry an offset.
    const hasZone = /(?:z|[+-]\d{2}:?\d{2})$/i.test(text);
    const date = new Date(hasZone ? text : `${text}Z`);
    return Number.isNaN(date.getTime()) ? null : date;
}

function annualSalary(job) {
    const value = Number(job.salary_min);
    if (!Number.isFinite(value) || value <= 0) return null;
    const text = String(job.salary_text || '').toLowerCase();
    if (/(?:\b(?:per\s+year|yearly|annual(?:ly)?|per\s+annum|j[aä]hr)|\/\s*year\b)/.test(text)) {
        return value;
    }
    if (/(?:\b(?:per\s+month|monthly|monat)|\/\s*month\b)/.test(text)) {
        return value * 12;
    }
    return null;
}

function matchesFilter(job, filter) {
    const details = job.match_details || {};
    if (filter === 'all') return true;
    if (filter === 'new') return !!job.is_new;
    if (filter === 'remote') return String(job.location_match || '').startsWith('remote');
    if (filter === 'junior') return !!details.is_junior_level;
    if (filter === 'software') return !!details.is_software_dev;
    if (filter === 'math') return !!details.is_math_related;
    return job.location_match === filter;
}

function matchesSearch(job, query) {
    const terms = query.split(/\s+/).filter(Boolean);
    const haystack = [
        job.title,
        job.company,
        job.location,
        job.country,
        job.category,
        job.experience_level,
        ...(job.match_details?.matched_keywords || []),
    ].filter(Boolean).join(' ').toLowerCase();
    return terms.every(term => haystack.includes(term));
}

function renderFilters() {
    const container = byId('filters');
    container.innerHTML = Object.entries(config.filters).map(([key, label]) =>
        `<button class="filter-btn${key === currentFilter ? ' active' : ''}" type="button" ` +
        `data-filter="${escapeHtml(key)}" data-label="${escapeHtml(label)}">${escapeHtml(label)}</button>`
    ).join('');
}

function updateFilterCounts() {
    document.querySelectorAll('#filters [data-filter]').forEach(button => {
        const count = allJobs.filter(job => matchesFilter(job, button.dataset.filter)).length;
        button.textContent = `${button.dataset.label} (${count})`;
    });
}

function render(data) {
    const date = parseTimestamp(data.check_date);
    byId('last-check').textContent = date
        ? `Last checked: ${date.toLocaleString()} · new = first seen by this checker`
        : 'Last checked: unknown · new = first seen by this checker';
    byId('stat-total').textContent = data.total_jobs_found ?? 0;
    byId('stat-matching').textContent = data.matching_jobs ?? allJobs.length;
    byId('stat-new').textContent = allJobs.filter(job => job.is_new).length;

    const sources = [...new Set(allJobs.map(job => job.source).filter(Boolean))].sort();
    byId('stat-sources').textContent = sources.length;
    const sourceSelect = byId('source-filter');
    sourceSelect.replaceChildren(new Option('All sources', ''));
    sources.forEach(source => sourceSelect.add(new Option(source, source)));
    updateFilterCounts();
    applyFilter();
}

function applyFilter() {
    const query = byId('search').value.trim().toLowerCase();
    const source = byId('source-filter').value;
    const salaryInput = byId('salary-min').value.trim();
    const minSalary = Number(salaryInput);
    const sort = byId('sort').value;

    let filtered = allJobs.filter(job => {
        if (!matchesFilter(job, currentFilter) || !matchesSearch(job, query)) return false;
        if (source && job.source !== source) return false;
        if (salaryInput && Number.isFinite(minSalary)) {
            const annual = annualSalary(job);
            return annual !== null && annual >= minSalary;
        }
        return true;
    });

    if (sort === 'newest') {
        filtered = filtered.slice().sort((a, b) => {
            const newDifference = (b.is_new ? 1 : 0) - (a.is_new ? 1 : 0);
            if (newDifference) return newDifference;
            const aTime = parseTimestamp(a.first_seen)?.getTime() || 0;
            const bTime = parseTimestamp(b.first_seen)?.getTime() || 0;
            return bTime - aTime;
        });
    } else if (sort === 'salary') {
        filtered = filtered.slice().sort((a, b) =>
            (annualSalary(b) ?? -1) - (annualSalary(a) ?? -1));
    }

    document.querySelectorAll('#filters [data-filter]').forEach(button => {
        button.classList.toggle('active', button.dataset.filter === currentFilter);
    });
    byId('results-info').textContent = `Showing ${filtered.length} of ${allJobs.length} matching jobs`;
    const list = byId('job-list');
    if (!filtered.length) {
        list.innerHTML = `<div class="empty-state">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <p>No matching jobs found for this filter. <button type="button" class="nav-link" id="empty-reset">Reset filters</button></p>
        </div>`;
        byId('empty-reset').addEventListener('click', resetFilters);
        return;
    }

    list.innerHTML = filtered.map(job => {
        const details = job.match_details || {};
        const tags = [];
        if (job.is_new) tags.push('<span class="tag new">NEW</span>');
        if (details.is_junior_level) tags.push('<span class="tag junior">Junior</span>');
        if (details.is_software_dev) tags.push('<span class="tag software">Software/IT</span>');
        if (details.is_math_related) tags.push('<span class="tag math">Math/Data</span>');
        if (job.salary_text) tags.push(`<span class="tag salary">${escapeHtml(job.salary_text)}</span>`);
        if (job.location_match) {
            tags.push(`<span class="tag source">${escapeHtml(config.filters[job.location_match] || job.location_match)}</span>`);
        }
        tags.push(`<span class="tag source">${escapeHtml(job.source)}</span>`);

        const seen = parseTimestamp(job.first_seen);
        const place = [job.location, job.country].filter(Boolean).join(', ');
        const meta = [job.company ? `${place} · ${job.company}` : place];
        if (job.category) meta.push(job.category);
        if (job.experience_level) meta.push(job.experience_level);
        if (seen) meta.push(`First seen ${seen.toLocaleDateString()}`);

        return `<article class="job-card${job.is_new ? ' is-new' : ''}">
            <div class="job-title"><a href="${escapeHtml(safeJobUrl(job.url))}" target="_blank" rel="noopener noreferrer">${escapeHtml(job.title)}</a></div>
            <div class="job-meta">${meta.map(value => `<span>${escapeHtml(value)}</span>`).join('')}</div>
            <div class="tags">${tags.join('')}</div>
        </article>`;
    }).join('');
}

function resetFilters() {
    currentFilter = 'all';
    byId('search').value = '';
    byId('salary-min').value = '';
    byId('source-filter').value = '';
    byId('sort').value = 'relevance';
    applyFilter();
}

async function loadData() {
    try {
        const response = await fetch(`${config.dataUrl}?${Date.now()}`);
        if (!response.ok) throw new Error(`Failed to load ${config.dataUrl} (HTTP ${response.status})`);
        const data = await response.json();
        if (!data || !Array.isArray(data.results)) throw new Error(`Invalid data in ${config.dataUrl}`);
        allJobs = data.results;
        render(data);
    } catch (error) {
        byId('results-info').textContent = '';
        byId('job-list').innerHTML = `<div class="error">Could not load results. The weekly GitHub Action needs to generate ${escapeHtml(config.dataUrl)}.<br><small>${escapeHtml(error.message)}</small></div>`;
    }
}

if (typeof window !== 'undefined' && window.JOB_DASHBOARD_CONFIG) {
    config = window.JOB_DASHBOARD_CONFIG;
    byId('filters').addEventListener('click', event => {
        const button = event.target.closest('[data-filter]');
        if (!button) return;
        currentFilter = button.dataset.filter;
        applyFilter();
    });
    byId('reset-filters').addEventListener('click', resetFilters);
    ['search', 'salary-min'].forEach(id => byId(id).addEventListener('input', applyFilter));
    ['source-filter', 'sort'].forEach(id => byId(id).addEventListener('change', applyFilter));
    renderFilters();
    byId('salary-min').placeholder = `Min annual salary (${config.currency})`;
    loadData();
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { annualSalary, matchesFilter, matchesSearch, parseTimestamp, safeJobUrl };
}
