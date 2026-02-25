#!/usr/bin/env node

import { spawnSync } from "node:child_process";

const advisoryAllowlist = new Set(
  (process.env.NPM_AUDIT_ALLOWLIST ?? "")
    .split(",")
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean)
);

function extractAdvisoryKeys(advisory) {
  const keys = new Set();
  if (typeof advisory.source === "number" || typeof advisory.source === "string") {
    keys.add(String(advisory.source).toLowerCase());
  }
  if (typeof advisory.name === "string" && advisory.name.trim()) {
    keys.add(advisory.name.trim().toLowerCase());
  }
  if (typeof advisory.url === "string" && advisory.url.trim()) {
    const normalizedUrl = advisory.url.trim().toLowerCase();
    keys.add(normalizedUrl);
    const ghsaMatch = advisory.url.match(/GHSA-[0-9A-Za-z]{4}-[0-9A-Za-z]{4}-[0-9A-Za-z]{4}/);
    if (ghsaMatch) {
      keys.add(ghsaMatch[0].toLowerCase());
    }
  }
  return keys;
}

function formatAdvisory(advisory) {
  if (typeof advisory.url === "string" && advisory.url.trim()) {
    return advisory.url.trim();
  }
  if (typeof advisory.source === "number" || typeof advisory.source === "string") {
    return String(advisory.source);
  }
  if (typeof advisory.name === "string" && advisory.name.trim()) {
    return advisory.name.trim();
  }
  return "unknown-advisory";
}

const auditResult = spawnSync("npm", ["audit", "--json", "--omit=dev"], {
  encoding: "utf8",
});

if (auditResult.status === 0) {
  console.log("[npm_audit_gate] npm audit passed with no production vulnerabilities.");
  process.exit(0);
}

let report;
try {
  report = JSON.parse(auditResult.stdout || "{}");
} catch {
  console.error("[npm_audit_gate] Failed to parse npm audit JSON output.");
  if (auditResult.stdout) {
    console.error(auditResult.stdout);
  }
  if (auditResult.stderr) {
    console.error(auditResult.stderr);
  }
  process.exit(auditResult.status || 1);
}

const vulnerabilities = report?.vulnerabilities;
const vulnerabilityEntries =
  vulnerabilities && typeof vulnerabilities === "object"
    ? Object.entries(vulnerabilities)
    : [];

const advisoryCandidates = [];
for (const [packageName, vulnerability] of vulnerabilityEntries) {
  const via = Array.isArray(vulnerability?.via) ? vulnerability.via : [];
  for (const item of via) {
    if (item && typeof item === "object") {
      advisoryCandidates.push({
        packageName,
        severity: vulnerability?.severity ?? "unknown",
        advisory: item,
      });
    }
  }
}

if (!advisoryCandidates.length) {
  console.error(
    "[npm_audit_gate] npm audit reported vulnerabilities but no advisory metadata was available."
  );
  process.exit(auditResult.status || 1);
}

const disallowed = [];
const allowed = [];
for (const candidate of advisoryCandidates) {
  const advisoryKeys = extractAdvisoryKeys(candidate.advisory);
  const isAllowed = Array.from(advisoryKeys).some((key) => advisoryAllowlist.has(key));
  if (isAllowed) {
    allowed.push(candidate);
  } else {
    disallowed.push(candidate);
  }
}

if (disallowed.length) {
  console.error("[npm_audit_gate] Disallowed production advisories detected:");
  for (const item of disallowed) {
    console.error(
      `- ${item.packageName} (${item.severity}): ${formatAdvisory(item.advisory)}`
    );
  }
  process.exit(1);
}

const uniqueAllowed = new Set();
for (const item of allowed) {
  uniqueAllowed.add(formatAdvisory(item.advisory));
}
console.log(
  `[npm_audit_gate] Only allowlisted advisories detected (${uniqueAllowed.size}): ${Array.from(
    uniqueAllowed
  ).join(", ")}`
);
process.exit(0);
