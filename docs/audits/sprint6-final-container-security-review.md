# Final Container Security Review

Latest follow-up: [Final release gate assessment](sprint6-final-release-gate-assessment.md).
Independent scanning expands the HIGH union to 15 OS CVEs; deployment remains
blocked. The dated results below are historical evidence, not release approval.

Review date: 2026-10-18 Asia/Manila. **Blocked: required security policy still fails.**
Implementation: `3b5a355f0ea7de0a332809235dd8cf1e0433fbbe`.
No merge, deployment, cloud provisioning, model transfer, or graph import authorized or performed.

## Baseline and Failure Causes

Started clean on `fix/pre-deployment-security-and-cloud` at
`414329b58520ba5df31e71a3820670b75377f3ec`. PR #58 remains open, targeting
`integration/pre-deployment-main-sync` at `d0a8df3b50d460ef5fd7cb59851338172e9c15ee`.
PR #57 remains open against main `2edcc39bfe83296b00020e9d7894aa3d95889754`.
Both were mergeable, without new reviews or commits at task start.

[Baseline hosted run](https://github.com/AshenDary/PolyMerge/actions/runs/39054164664):
regression passed; dependency security failed solely on scikit-learn 1.4.0
PYSEC-2024-110 in runtime and development locks. Each container built and passed
liveness, then failed the HIGH/CRITICAL Trivy policy. No build, missing-package,
startup, or scanner execution error caused those baseline job failures.
Complete downloaded log: `/tmp/polymerge-final-security/baseline-ci.log`.

## Image Remediation

- Official Node 22 Bookworm -> official Node 22 Trixie slim, pinned index
  `sha256:154ba2f4d6fec323d28e4f4bb86bba4677f1223391a1979cf521304e03a98dfa`.
- Official Python 3.11 Bookworm -> official Python 3.11 Trixie slim, pinned index
  `sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce`.
  Python remains 3.11.17 in Linux; NumPy 1.26.4 and all scientific pins unchanged.
- Install the available Debian security update `liblzma5=5.8.1-1+deb13u2`.
  No third-party package repositories or unstable Debian packages introduced.
- Remove all setuid/setgid file bits. Existing non-root users and package-manager
  removal retained. No RDKit, Neo4j, feature-builder or model dependency removed.
- Test read-only rootfs, writable bounded `/tmp`, no external network, all Linux
  capabilities dropped, and no-new-privileges. These are local/CI test flags, not
  a claim that Render has been configured to enforce equivalent flags.
- CI now retains JSON package inventories and findings for every image even when
  its scan gate fails. No advisory ignores, severity reductions, or ignore-unfixed flags.

## Before and After

Local ARM64 images, same downloaded Trivy DB for comparison:

| Image | Before | After | Remaining Critical | Remaining High | Unique remaining CVEs |
| --- | ---: | ---: | ---: | ---: | ---: |
| Backend | 57 | 43 | 0 | 43 | 8 |
| ML | 63 | 44 | 0 | 44 | 8 |
| Streamlit | 63 | 44 | 0 | 44 | 8 |

Counts are package/advisory occurrences, not independently exploitable defects.
All remaining HIGH findings in these reports are OS packages. The moderate
scikit-learn finding is separately retained by pip-audit, not hidden by the
container scanner's existing HIGH/CRITICAL threshold.

Exact before/after IDs, binary packages, installed versions, fixed-version fields,
severity and status: [machine-readable evidence](security-evidence/container-findings.csv).
Blank fixed-version fields mean the scanner did not offer a fix in that distro;
they do not mean no fix exists upstream. Full inventories and image IDs are in
`/tmp/polymerge-final-security/{backend,ml,streamlit}-{before,after}.json`.
After inventories contain 79 backend OS packages, 87 per Python image; language
packages are included in the same JSON. Hosted equivalents are retained as
`security-backend`, `security-ml`, `security-streamlit` CI artifacts for 30 days.

Scanner: Trivy 0.76.0, pinned image
`sha256:2416d1f74045b57274df1a340eee6b510cacd73c66a6ccb8da092b117eb7d222`.
The default mirror downloaded DB metadata with UpdatedAt `2026-10-16T01:13:54Z`,
NextUpdate `2026-10-17T01:13:54Z`, DownloadedAt `2026-10-17T17:59:53Z`.
Thus the supplied DB was about 41 hours old and past its advertised refresh time.
A fresh-cache direct GHCR attempt was denied by the registry. This freshness
limitation is unresolved; these counts are evidence against that DB, not a claim
of a completely current vulnerability inventory. Debian tracker checks supplement
the scan but do not replace it. Refresh and rescan before release acceptance.

### Findings Removed by the Base Change

All packages below were runtime-present, not merely build dependencies.

| CVE | Baseline package/version | Severity | Updated package/version and assessment |
| --- | --- | --- | --- |
| CVE-2023-45853 | zlib1g 1:1.2.13.dfsg-1, all images | Critical | 1:1.3.dfsg+really1.3.1-1+b1; no longer reported. Vulnerable MiniZip path is distinct from general zlib use. |
| CVE-2025-7458 | libsqlite3-0 3.40.1-2+deb12u2, Python images | Critical | 3.46.1-7+deb13u2; requires crafted SQL execution, no public SQL endpoint. |
| CVE-2026-11822, CVE-2026-11824 | same SQLite package | High | Same update; FTS5 crafted data paths, no public SQLite input. |
| CVE-2026-84782 | libssl3 / openssl 3.0.22-1~deb12u1, Python images | High | libssl3t64 / openssl 3.5.7-1~deb13u3; DTLS retransmission issue; serving uses HTTP and outbound TLS, not DTLS. |
| CVE-2026-53613, CVE-2026-53615 | util-linux source packages 2.38.1-5+deb12u3, all images | High | 2.41.5-0+deb13u1; privilege-bearing mount/partition parser paths. Other util-linux advisories remain below. |
| CVE-2026-41992 | gzip 1.12-1, all images | High | Trixie gzip 1.13 package no longer reported. No request path invokes the gzip executable. |

Debian confirms distro fixes rather than assuming upstream version numbers:
[SQLite](https://security-tracker.debian.org/tracker/CVE-2025-7458),
[OpenSSL backport](https://security-tracker.debian.org/tracker/CVE-2026-84782),
[util-linux backport](https://security-tracker.debian.org/tracker/CVE-2026-53613),
[zlib/MiniZip](https://security-tracker.debian.org/tracker/CVE-2023-45853).

### Remaining Findings and Reachability

All eight are still HIGH in the scanner, present in all images, and **not waived**.
All have no fixed-version field in the Trixie scan. Runtime presence alone does
not establish a remotely reachable path. Conversely, this review is not a proof
that all indirect/native paths are unreachable.

| CVE | Installed package family | Prerequisite and concrete evidence | Required next step |
| --- | --- | --- | --- |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | util-linux 2.41.5-0+deb13u1 | Privileged post-mount hooks after failed helper; service has no mount endpoint, binaries have no setuid/setgid bits. CI drops capabilities. | Await stable backport or review narrow applicability evidence; upstream 2.42.3 fix is not a Trixie package. |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | same | Privileged operator invokes nsenter --join-cgroup on attacker target. No application invocation; no privileged operator workflow in image. | Review operator/infrastructure assumptions; stable backport required or approved exception. |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | same | Authorized fstab X-mount.subdir and attacker-controlled path; not exposed by API. | Same; upstream 2.42.3 fix not installed. |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | same | Privileged restricted bind mount and writable source ancestor; privilege bits removed. | Same; no blanket util-linux waiver. |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | libacl1 2.3.2-2+b1 | Privileged ACL caller follows attacker-controlled path. No ACL API or uploaded filesystem paths; unprivileged serving. | ABI-changing fix in 2.4.0; wait for supported distro update or reviewed minimal runtime. |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | ncurses 6.5+20250216-2 | Crafted terminal data passed to infocmp CLI. Tool remains installed; no request-to-shell/infocmp path found. | Distro backport/minimal-runtime review; do not assume unused package equals approved non-applicability. |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | libsystemd0/libudev1 257.13-1~deb13u1 | Requires systemd-homed and homed-managed user. Only libraries installed; systemd-homed executable absent in inspected ML image. | Reviewer verify absence across final images and accept applicability or obtain backport. |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | perl-base 5.40.1-6+deb13u1 | Crafted tar parsed by Archive::Tar. No tar uploads; Archive/Tar.pm absent in inspected ML runtime. | Verify all final images; review component-level applicability or supported fix. |

The util-linux scan expands each CVE across bsdutils, libblkid1, liblastlog2-2,
libmount1, libsmartcols1, libuuid1, login, mount and util-linux. Epochs/package
revisions are retained per binary in the CSV. ncurses expands across libtinfo6,
ncurses-base, ncurses-bin, plus libncursesw6 in Python images. Do not install
unstable system libraries into a stable base just to reduce counts. Essential
OS package metadata was not deleted to mislead the scanner.

## Frozen Runtime Investigation

[PYSEC-2024-110 / CVE-2024-5206](https://github.com/advisories/GHSA-jw8x-6495-233v)
concerns TfidfVectorizer retaining discarded training tokens. Patched upstream
version is 1.5.0; severity is moderate. The actual frozen pipeline contains numeric
imputation/scaling and RandomForestClassifier, not a text vectorizer. The serving
feature builder creates numeric graph/molecular features. Serving paths contain
no fit call, text training, user-supplied pickle/model upload, or estimator exposure.
The vulnerable functionality remains installed with sklearn; this is an
applicability assessment requiring reviewer approval, not a fixed-package claim.

Trusted joblib loading is a separate deserialization risk: checksum, size,
metadata and feature contract are verified before loading. A malicious artifact
or compromised trusted metadata would still be dangerous; private storage and
restricted repository/deployment access remain required.

The new offline `--experimental-runtime` probe does not modify the production
version guard. It records warnings, tests inference, and returns exit 2 when
compatibility is not established. It never trains, reserializes, changes golden
fixtures, or evaluates the held-out test set.

| Runtime | Numerical result | Compatibility decision |
| --- | --- | --- |
| Python 3.11.16 / sklearn 1.4.0 / NumPy 1.26.4, local | 313 probe rows from original saved simulation fixtures plus numeric edge cases | Baseline retained in a new evidence file; original fixtures untouched |
| Python 3.11.16 / sklearn 1.5.2 / NumPy 1.26.4, isolated | Exact classes and probabilities, tolerance zero; all Major/Moderate/Minor represented | FAIL: six distinct estimator-version warnings and ColumnTransformer.get_params missing force_int_remainder_cols |
| Python 3.11.17 / sklearn 1.4.0 / NumPy 1.26.4, Trixie ARM64 | Exact 313-row classes/probabilities; same 55 ordered features | PASS; no estimator-version warnings |

311 distinct fixture drug pairs: 306 build features, five retain unavailable
reasons. Five initial mapping probes plus two numeric edge cases yield 313 rows.
Isolated 1.5.2 deserialization and predict/predict_proba worked, but estimator API
compatibility did not. This is not a claim of changed predictions or proof of
universal parity. Upstream explicitly does not support cross-version model
loading: [persistence guidance](https://scikit-learn.org/stable/model_persistence.html).
Production sklearn stays 1.4.0; locks and original model metadata remain unchanged.

Artifact SHA-256 remains
`2b9ed9ca9a57a3eed256eb28d369df89403666a1c5ea1231c47ebe1e053ccc6d`.
Linux probe peak RSS: 645644 KiB (about 631 MiB). No cloud memory/load SLA inferred.

## Independent Verification

- Backend 122 tests pass, including new forwarded-IP quota bypass and restart
  isolation tests. ML 127 pass locally; 13 script tests pass. Contract, metadata,
  frontend syntax, shell syntax and diff checks pass. Dependency warnings retained.
- Five current local scenarios exactly match original candidateSets and optimizer
  metadata: single disease, two diseases, coronary disease, four diseases, no treatments.
- All three updated Docker builds pass. Non-root, rootfs read-only, no setuid/setgid,
  no-new-privileges and restart checks pass. CI runs the same script.
- Backend history/explanation/legacy routes remain 404; unavailable readiness is
  503. ML rejects browser origins, oversized input and documentation routes.
  Checks run before and after restart. No cookies or browser API key introduced.
- Existing tests cover invalid inputs, explicit origins/framing, bounded analysis,
  error redaction, Research Takeaway and frontend navigation. No frontend code changed.
- npm ci and production audit pass. Python hashed builds succeed on Linux; runtime
  RDKit molecular parsing, Neo4j, NumPy and sklearn imports pass. pip/setuptools/wheel/
  pytest are absent from Python runtime distributions. Node package managers removed.
- Runtime/development pip-audit each retain the single sklearn advisory; wrapper
  audit remains clean. No requirement or lockfile regenerated for this base change.
- ML infrastructure is still only a disabled Render `pserv` template. Origin checks
  are not authentication. Actual private ingress, trusted-proxy behavior and browser
  iframe acceptance cannot be verified without approved infrastructure/browser access.

Evidence directory: `/tmp/polymerge-final-security`, including raw scans, build and
runtime logs, pip-audit logs, compatibility reports and local live scenario payloads.
Latest hosted run and exact PR head are recorded in the PR #58 verification comment
after push; local results must not be substituted for hosted check outcomes.

## Handoff

No finding is accepted as non-applicable without reviewer approval. Security CI
must remain red while its required policy fails. Refresh scanner data, obtain
supported fixes or narrowly reviewed applicability decisions, and verify private
ingress/proxy and browser acceptance before release.

After those gates: review #58, obtain approval to merge it into integration,
verify #57 incorporates it and rerun CI, obtain separate approval for #57 -> main,
record exact main SHA, complete browser/iframe acceptance, approve cloud budgets
and transfer destinations, deploy, then execute live acceptance. This task
performs none of those merges or cloud operations.
