'use strict';

const assert = require('node:assert/strict');
const {
    annualSalary,
    matchesFilter,
    matchesSearch,
    parseTimestamp,
    safeJobUrl,
} = require('../docs/dashboard.js');

assert.equal(annualSalary({ salary_min: 4000, salary_text: 'EUR 4.000 brutto pro Monat' }), 48000);
assert.equal(annualSalary({ salary_min: 45000, salary_text: 'EUR 45,000 per year' }), 45000);
assert.equal(annualSalary({ salary_min: 60000, salary_text: 'TWD 60,000 / month' }), 720000);
assert.equal(annualSalary({ salary_min: 5000, salary_text: 'Competitive salary' }), null);

const job = {
    title: 'Backend Engineer',
    company: 'Example GmbH',
    location: 'Wien',
    category: 'Python',
    match_details: { is_software_dev: true, is_junior_level: false, matched_keywords: ['python'] },
};
assert.equal(matchesSearch(job, 'backend python'), true);
assert.equal(matchesSearch(job, 'backend ruby'), false);
assert.equal(matchesFilter(job, 'software'), true);
assert.equal(matchesFilter(job, 'junior'), false);
assert.equal(matchesFilter(job, 'vienna_area'), false);

assert.equal(safeJobUrl('javascript:alert(1)'), '#');
assert.equal(safeJobUrl('https://jobs.example/1'), 'https://jobs.example/1');
assert.equal(safeJobUrl('not a URL'), '#');
assert.equal(parseTimestamp('2026-01-01T00:00:00Z')?.getTime(), Date.UTC(2026, 0, 1));
assert.equal(parseTimestamp('2026-01-01T00:00:00')?.getTime(), Date.UTC(2026, 0, 1));
assert.equal(parseTimestamp('not a timestamp'), null);

console.log('Dashboard helper smoke tests passed.');
