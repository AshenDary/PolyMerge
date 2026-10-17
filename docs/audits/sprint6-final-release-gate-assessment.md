# Final Release Gate Assessment

Review: 2026-10-18 Asia/Manila. **DEPLOYMENT BLOCKED - UNRESOLVED SECURITY RISK**.
Starting branch: `fix/pre-deployment-security-and-cloud`, SHA
`a9b20099b7a3c4b9ea086acbb6779d84cdc44aee`. Implementation: `ac5cea4`.
PR [58](https://github.com/AshenDary/PolyMerge/pull/58) targets
`integration/pre-deployment-main-sync`; PR [57](https://github.com/AshenDary/PolyMerge/pull/57)
targets main. Neither merge nor deployment is authorized or performed.
Main baseline: `2edcc39bfe83296b00020e9d7894aa3d95889754`;
integration baseline: `d0a8df3b50d460ef5fd7cb59851338172e9c15ee`.

## Reproducible Scanner Evidence

All three official digest-pinned Trixie images were rebuilt and scanned locally.
Node and Python upstream tags still resolve to the committed digests; no new base
update was available. Fresh Debian package indexes offered no fixes for the
remaining findings. The available liblzma5 security update is already installed.
No unstable repositories, deleted runtime libraries, scanner suppressions, or
policy threshold changes were introduced. Existing multistage builds remain.

| Image | Previous HIGH | Trivy HIGH | Grype HIGH | CRITICAL, both |
|---|---:|---:|---:|---:|
| Backend | 43 | 43 | 54 | 0 |
| ML | 44 | 44 | 55 | 0 |
| Streamlit | 44 | 44 | 55 | 0 |

Trivy 0.76.0: 8 unique HIGH IDs per image. Grype 0.120.1: 14 unique HIGH IDs
per image; union: 15. Counts are package/advisory occurrences, not distinct
exploits. Grype total matches across all severities: 157/167/166 respectively.
No remaining OS CVE was fixed this round; no stable-repository fix was found.
No reviewer exception has been approved.

Trivy DB updated `2026-10-16T01:13:54.947090392Z`, next update advertised
`2026-10-17T01:13:54.947090202Z`, downloaded into a new cache
`2026-10-17T18:29:36.478798762Z`. The mirror supplied an older-than-advertised
snapshot. Grype DB v6.1.10 built `2026-10-17T06:27:09Z`, validity true;
Debian provider captured `2026-10-17T00:30:08Z`.

The count difference is **not just database age**: the seven extra Grype HIGH
IDs are present in Trivy's all-severity inventory (six MEDIUM, one UNKNOWN).
Grype also rates systemd CVE-2026-16742 MEDIUM versus Trivy HIGH. Thus backend
43 - 2 systemd occurrences + 13 additional occurrences = 54.
Default scanner classifications are preserved; Debian no-DSA/Grype wont-fix
does not constitute acceptance or proof of safety.

Local full JSON and probe logs: `/tmp/polymerge-release-gates/` (ephemeral).
The committed [current scanner inventory](security-evidence/release-gate-scanner-inventory.json)
retains every local HIGH/CRITICAL package occurrence from both scanners.
CI retains both scanner reports, package inventories and Trivy DB metadata for
30 days. Original inventory remains in
[container-findings.csv](security-evidence/container-findings.csv).

## Original Eight CVEs

All affected package families exist in **all three** images. All eight remain
open for Trixie in the [Debian tracker](https://security-tracker.debian.org/tracker/).
Versions below are installed versions; upstream fixes are not automatically
available as supported Debian Trixie packages.

| CVE | Package/version | Severity | Fix availability | Runtime applicability and disposition |
|---|---|---|---|---|
| CVE-2026-76642 | util-linux family 2.41.5-0+deb13u1 | Trivy/Grype HIGH; CNA 7.8 | Upstream 2.41.6/2.42.3; no Trixie candidate | Privileged failed-mount helper hooks; no application mount invocation found. Non-root, removed setuid bits: mitigated, requires reviewer acceptance. |
| CVE-2026-78408 | util-linux family, same | HIGH; CNA 7.9 | Upstream 2.42.4; no Trixie candidate | Privileged nsenter --join-cgroup/open descriptor prerequisites; mitigated, requires reviewer acceptance. |
| CVE-2026-78409 | util-linux family, same | HIGH; CNA 7.0 | Upstream 2.42.3; no Trixie candidate | X-mount.subdir, authorized fstab entry, symlink/kernel prerequisites; mitigated, requires reviewer acceptance. |
| CVE-2026-78410 | util-linux family, same | HIGH; CNA 7.8 | Upstream 2.42.3; no Trixie candidate | Privileged restricted bind mount with attacker path; mitigated, requires reviewer acceptance. |
| CVE-2026-54369 | libacl1 2.3.2-2+b1 | HIGH; CNA 7.1 | Upstream 2.4.0 ABI change; no Trixie candidate | Privileged ACL path-following prerequisites; mitigated, requires reviewer acceptance. |
| CVE-2025-69720 | ncurses 6.5+20250216-2 | HIGH; NVD 7.8 | Upstream 6.5-20251213; no Trixie candidate | Crafted terminfo passed to infocmp; CLI exists but no serving invocation found. Mitigated, requires reviewer acceptance. |
| CVE-2026-16742 | libsystemd0/libudev1 257.13-1~deb13u1 | Trivy HIGH; Grype/CNA MEDIUM 6.7 | No Trixie candidate | systemd-homed executable absent; evidence-backed acceptance candidate, not an approved exemption. |
| CVE-2026-9538 | perl-base 5.40.1-6+deb13u1 | HIGH; NVD 7.5 | Archive::Tar 3.10; newer Debian perl, not Trixie | Archive::Tar module absent; evidence-backed acceptance candidate, not an approved exemption. |

Util-linux occurrences: bsdutils (`1:` epoch), libblkid1, liblastlog2-2,
libmount1, libsmartcols1, libuuid1, mount, util-linux, and
login `1:4.16.0-2+really2.41.5-0+deb13u1`. Ncurses occurrences:
libtinfo6, ncurses-base, ncurses-bin; Python images also libncursesw6.
Exact per-image versions are retained in the original CSV and current JSON.

NVD API records were retrieved individually from
`https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=<CVE>`.
The util-linux and systemd records await NVD analysis, so their cited scores
are CNA scores, not independent NVD assessments; ACL is deferred.
For ncurses, MITRE reports 7.3 and a secondary CISA score is 9.8, versus
NVD 7.8. Zero scanner CRITICAL findings does not erase that disagreement.
Upstream corroboration includes
[util-linux advisory](https://github.com/util-linux/util-linux/security/advisories/GHSA-m25x-3hj9-m26f)
and [systemd advisory](https://github.com/systemd/systemd/security/advisories/GHSA-jm29-p7hh-vjhv).

## Additional Independent-Scanner HIGH Findings

All below affect package inventories in all three images, remain open in
Debian Trixie, and have no patched stable candidate in the inspected repository.
These are new release-review inputs, not findings silently excluded from policy.

| CVE | Installed package/version | Trivy severity | Applicability and disposition |
|---|---|---|---|
| CVE-2026-82560 | perl-base 5.40.1-6+deb13u1 | UNKNOWN | Pod::Text DoS; module absent at standard Perl installation paths in all three images. Requires reviewer acceptance; upstream fix Pod::Text 6.1.1. |
| CVE-2026-5435 | libc-bin/libc6 2.41-12+deb13u4 | MEDIUM | Deprecated DNS TSIG printing buffer write; indirect native reachability unresolved blocker. |
| CVE-2026-85091 | zlib1g 1:1.3.dfsg+really1.3.1-1+b1 | MEDIUM | Nonblocking gzwrite/gzprintf stale buffer. Upstream affected range appears newer than installed 1.3.1; Debian still open. Disputed applicability, unresolved blocker, not a false-positive exemption. |
| CVE-2026-95619 | gcc-14-base/libgcc-s1/libstdc++6 14.2.0-19 | MEDIUM | Aligned operator new overflow; native-library reachability unresolved blocker. |
| CVE-2026-19499 | libc-bin/libc6 2.41-12+deb13u4 | MEDIUM | strfmon width buffer overflow; native-library reachability unresolved blocker. |
| CVE-2026-102010 | gcc-14-base/libgcc-s1/libstdc++6 14.2.0-19 | MEDIUM | PBDS binary heap erase_if use-after-free; native-library reachability unresolved blocker. |
| CVE-2026-54370 | libacl1 2.3.2-2+b1 | MEDIUM | Privileged ACL command TOCTOU; getfacl/setfacl/chacl absent from PATH in all three images. Mitigated, requires reviewer acceptance; upstream fix ACL 2.4.0. |

Official [zlib tracker](https://security-tracker.debian.org/tracker/CVE-2026-85091)
and [glibc tracker](https://security-tracker.debian.org/tracker/CVE-2026-5435)
illustrate why scanner presence alone is insufficient to determine exploitability.
The complete Debian tracker JSON is saved with local evidence. NVD API records
for all seven additional IDs were also checked: 82560 deferred (secondary CVSS
3.1 7.5); 5435 modified (secondary 7.3); 85091 awaiting analysis (CNA 7.4,
CVSS 4.0 8.3); 95619 awaiting analysis (CNA 7.7); 19499 awaiting analysis
(CNA 7.7); 102010 awaiting analysis (CNA 7.0); 54370 deferred (CNA CVSS 3.1
6.3 versus CVSS 4.0 7.2). These are not independent NVD scores.

NVD describes 19499 as requiring strfmon/strfmon_l with right-justified padding
and a susceptible destination size; no network-facing application impact was
known at publication. The [GCC vendor advisory](https://access.redhat.com/security/cve/cve-2026-102010)
requires the non-default PBDS binary_heap_tag plus erase_if; it rates impact
moderate despite CVSS 7.0. Neither observation proves PolyMerge's transitive
native dependencies are unaffected. The [Pod::Text changelog](https://metacpan.org/release/RRA/podlators-v6.1.1/changes)
corroborates its upstream fix. Further native call-path and upstream patch
applicability review remains required; no blanket acceptance is recommended.

## Frozen Model and Patched Runtime Experiments

Model `RandomForestClassifier-sprint5-v1-65e9834666ad19c5` remains byte-identical:
`2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.
No retraining, retuning, reserialization, held-out reevaluation, data-source
changes, research-paper edits, or presentation edits occurred. The original
130,422-pair source, 55 features and three-class contract are unchanged.

Reviewed `ml_engine/app/services/model_serving.py`, `ddi_feature_builder.py`
and `ml_engine/main.py`: fixed numeric feature construction, checksum/provenance
guard before trusted local joblib loading; no TF-IDF/count vectorizer, text fit,
user-controlled model upload or dynamic pipeline construction found on serving
paths. [PYSEC-2024-110](https://github.com/advisories/GHSA-jw8x-6495-233v)
concerns TF-IDF token retention. This supports narrow applicability review,
not an automatic waiver of the dependency gate or of unsafe pickle loading.

| Runtime | Numerical probes | Full compatibility |
|---|---|---|
| 1.4.0 production | 313 rows exactly match classes/probabilities in rebuilt Linux image | Original runtime and provenance preserved |
| 1.5.0 isolated, full pinned runtime otherwise | 313 rows exactly match | Version warnings; ColumnTransformer.force_int_remainder_cols missing; probe exits 2 |
| 1.5.2 prior experiment | 313 rows exactly match | Same ColumnTransformer incompatibility; unsupported cross-version loading |
| 1.6.1 isolated, full pinned runtime otherwise | 313 rows exactly match, including reload | Version warnings; Pipeline.transform_input missing; probe exits 2 |

Probes exercise original feature builder, feature order, all classes, supported
and unsupported pairs (311 saved fixture pairs: 306 available, 5 unavailable,
plus two edge cases). Full candidate endpoint was exercised twice across
lifespans in patched 1.5.0: HTTP 200, model unavailable, ML not applied,
zero candidates in that harness. This is **not successful candidate parity**.
The service's provenance guard rejects the patched runtime; direct 1.6.1
service loads likewise fail. No guard or preprocessing check was bypassed.
Numerical parity does not establish supported object/API compatibility.
[scikit-learn persistence guidance](https://scikit-learn.org/stable/model_persistence.html)
does not support cross-version loading. Keep 1.4.0 pending authorized narrow
risk review or a separately validated compatible migration.

## Implemented Controls and Verification

- Explicit proxy IP/CIDR validation rejects aliases, malformed entries and
  universal IPv4/IPv6/mapped ranges. Unset trust remains false.
- Real local HTTP reverse-proxy test: forged leftmost X-Forwarded-For cannot
  reset one client's quota; a second client has a separate quota. Untrusted
  direct peer ignores the forwarded value. Unconfigured trust aggregates
  traffic conservatively. Three new tests pass.
- GraphService now shares one thread-safe Neo4j driver instead of allocating
  a driver per request. Each query owns a session; shutdown closes the driver.
  Pool maximum 10 per process, acquisition/connect timeout 5 seconds, lifetime
  300 seconds, query timeout 30 seconds. Six new tests cover concurrency,
  lifecycle, bound parameters and TLS rejection cases.
- Disabled deployment blueprint opts into certificate-verified `neo4j+s` only;
  plaintext, self-signed mode and embedded credentials are rejected.
- Existing adverse API tests pass: isolated explanation/history state, rate
  and concurrency bounds, validation/body limits, CORS/CSP/frame ancestors,
  disabled production legacy/mock routes and sanitized upstream errors.
- All three images built and passed non-root/read-only/capability-drop,
  no-new-privileges, no-network health/negative checks and restart tests.
  Hosted container checks also passed on the final implementation revision,
  including the last backend-only proxy parser refinement.
- Secrets were not printed, committed or embedded in images. Frozen model
  remains private and separately provisioned; no cloud transfer occurred.

Local results: backend **125 passed**, ML **133 passed** (two dependency
deprecation/future warnings), script tests **13 passed**. Contract, metadata,
frontend JavaScript syntax and whitespace checks pass. npm production audit
has zero findings. Runtime/dev pip audits each fail on the one sklearn
advisory; Streamlit lock audit passes. Isolated patched environment resolves
and pip check passes, but artifact API compatibility does not.

All five existing live simulation snapshots match complete candidateSets and
optimization metadata exactly: hypertension; hypertension/type 2 diabetes;
coronary disease/atherosclerosis; existing four-disease fixture; no represented
coverage. This preserves drugs, order, coverage, rules, pair availability,
ranking and Research Takeaway. Graph migration manifest remains 3,415 nodes,
16,230 relationships with unchanged source hashes. Golden fixtures unchanged.

## Provider Boundaries and Release Gates

Architecture remains Streamlit Community Cloud -> public Render Fastify ->
private Render FastAPI -> AuraDB. The iframe is not authentication. Public
anonymous API abuse controls do not establish user authorization.
[Render terminates HTTPS](https://render.com/docs/web-services) before forwarding
HTTP. Local proxy tests do not verify Render's actual source ranges, forwarding
chain, client-IP selection or spoof stripping. Operator must establish these
before populating TRUST_PROXY_CIDRS; never guess broad ranges to recover quotas.

[Render private networking](https://render.com/docs/private-network) is reachable
by other eligible same-workspace/region services, not exclusively Fastify.
Private-service configuration must be validated live; additional workspace
isolation/authentication is an explicit review decision. Aura certificate/TLS,
connection limits across workers/replicas (10 per process), actual latency,
timeouts, iframe cookies/CSP and browser acceptance remain unverified gates.
The disabled blueprint remains disabled; auto-deploy remains off.

Required next steps: finish upstream patch and native-path analysis for the
newly surfaced IDs; resolve native-library uncertainty; obtain narrowly scoped,
time-bounded reviewer decisions for demonstrated absent/mitigated components
and sklearn; preserve failing policies until an authorized change; verify
actual hosted CI; then review PR58 into integration and PR57 into main only
with explicit approval. Separately authorize provider provisioning and live
security/browser acceptance before any public launch.

## Hosted CI

Baseline run [39056838946](https://github.com/AshenDary/PolyMerge/actions/runs/39056838946):
regression passed; dependency policy failed on sklearn; all image builds and
hardened runtime checks passed, Trivy failed on the original eight CVEs.
Implementation run [39059146756](https://github.com/AshenDary/PolyMerge/actions/runs/39059146756)
completed on `ac5cea44bbdafca05fd0d620c075feae8e181a7e`:

- Regression PASS: backend 125; ML 131 passed, 2 skipped (private-artifact
  tests unavailable in hosted CI), 2 warnings; scripts 13. Hash-locked
  dependency install, contract, metadata, JS syntax and tracked-secret checks pass.
- Security FAIL: runtime and development audits each report only
  scikit-learn 1.4.0 PYSEC-2024-110, patched version 1.5.0. npm and Streamlit pass.
- All three container builds and hardened startup/restart checks PASS.
- Trivy FAIL: 43/44/44 HIGH, zero CRITICAL. Grype FAIL: 54/55/55 HIGH,
  zero CRITICAL. Grype exits 2 explicitly for findings above policy threshold,
  not scanner execution failure. Both reports and DB metadata uploaded for
  each image, downloaded and checked against local results.
- Hosted Trivy fetched the same older DB snapshot as local. Scanner policies
  are unchanged; independent Grype runs even after Trivy failure.

Documentation-only follow-up commit/run is identified in PR58's final update;
the implementation results above are not represented as a green release.
