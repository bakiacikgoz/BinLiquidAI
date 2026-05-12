# BinLiquid Yazılımsal Kapanış ve Yol Haritası

**Tarih:** 10 Mayıs 2026
**Kapsam:** Yazılım geliştirme, teknik olgunluk, release gate, qualification, güvenlik, CI/CD ve çalıştırılabilirlik
**Kapsam dışı:** Pazarlama, satış, marka konumlandırma, kullanıcı edinme, fiyatlandırma

---

## 1. Bu planın amacı

Bu dosyanın amacı BinLiquid geliştirme döngüsünü “sürekli yeni özellik ekleme” halinden çıkarıp **kanıta dayalı kapanış kapıları olan bir yazılım release hattına** dönüştürmektir.

Bu plan şunları netleştirir:

- Projenin şu anda yazılımsal olarak hangi aşamada olduğu
- Hangi parçaların olgun, hangi parçaların pilot/beta/gated olduğu
- Sıradaki teknik adımın ne olduğu
- Hangi koşullar sağlanınca mevcut geliştirme döngüsünün biteceği
- Hangi işler v1.0 / GA hattına girmemeli ve sonraya bırakılmalı

---

## 2. Tek cümlelik teknik hedef

**BinLiquid, yerel / self-hosted çalışan, güvenlik ve onay kapılarıyla yönetilen, audit/replay kanıtı üreten, Core Runtime + Team Runtime + Operator Panel + qualification-gated Computer-Use temeline sahip kontrollü bir agentic runtime olarak release-ready hale gelmelidir.**

Bu hedefin pratik karşılığı:

- Core Runtime çalışır ve regressionsız kalır.
- Team Runtime kontrollü/restricted profillerde pilot-hardened seviyeden release-ready seviyeye çıkar.
- Enterprise profile signed evidence, key management, baseline, backup/restore ve GA readiness kontrollerini geçer.
- Operator Panel beta durumundan imzalı/notarized veya gate’li release artifact durumuna taşınır.
- Computer-Use tarafı yalnızca qualification kanıtı olan dar yüzeylerde iddia edilir; varsayılan olarak fail-closed kalır.

---

## 3. Mevcut teknik konum

Projeyi şu anda şu aşamada kabul etmelisin:

> **Release Candidate / Evidence Closure aşaması**

Yani ana yazılım omurgası büyük ölçüde kurulmuş durumda; ana iş artık “yeni büyük özellik eklemek” değil, **kanıt üretmek, gate kapatmak, release koşullarını netleştirmek ve kapsamı dondurmak** olmalı.

### 3.1 Bileşen bazlı olgunluk haritası

| Bileşen | Mevcut durum | Karar | Sıradaki teknik gate |
|---|---|---|---|
| Core Runtime | En olgun temel. Planner, router, provider fallback, memory, governance ve CLI yolları mevcut. | Yeni mimari ekleme yok; regression kapatma ve sözleşme stabilitesi. | `make mainline-gate`, full pytest, ruff, doctor, benchmark smoke. |
| Team Runtime | Kontrollü/restricted profillerde pilot-hardened. Approval lifecycle, replay, bounded concurrency, memory conflict handling var. | Release öncesi güçlendirilecek ana alanlardan biri. | `make pilot-gate`, larger DAG resume, deterministic + live-provider smoke, replay verify. |
| Enterprise Profile | Constrained readiness var; fakat GA iddiası için signed qualification evidence ve key-management maturity gerekiyor. | v1.0 hedefinin merkezinde olmalı. | `make enterprise-gate`, key rotation drill, qualification run, GA readiness green/go. |
| Operator Panel | Beta desktop control surface. UI/bridge/test/build hattı var. | Release artifact üretimi dış credential gate’lerine bağlı. | macOS signing/notarization, Windows signed RC + clean VM smoke + promote gate. |
| Computer-Use Runtime | Vision-first foundation uygulanmış; fail-closed, approval-gated, qualification-gated. | Asla unrestricted automation gibi sunulmamalı. | deterministic qualification, platform doctor, macOS supervised local qualification, Windows/Linux disabled evidence. |
| Research / sLTC | Research path mevcut; product runtime’dan ayrık tutulmalı. | Release öncesi ana yol olmamalı. | Sadece calibration/telemetry işleri; release blocker değil. |

---

## 4. Bu geliştirme döngüsü nerede bitecek?

Bu döngünün bitişi “akla gelen her özellik tamamlandı” noktası değildir. Yazılım projelerinde bu nokta yoktur. Bu döngünün bitişi şu olmalıdır:

> **v1.0 Constrained Self-Hosted Release Ready**

Bu ifade şu anlama gelir:

- Kod ana hattı temizdir.
- Core + Team + Enterprise gates geçmiştir.
- Qualification evidence üretilmiş ve imzalanmıştır.
- `ga readiness` raporu green/go verir veya kalan blokları açıkça listeler.
- Desktop artifact yayınlanacaksa macOS ve/veya Windows release gate’leri geçmiştir.
- Computer-use iddiaları yalnızca kanıtlanmış dar yüzeylerle sınırlıdır.
- Release notes, README, qualification matrix ve gerçek kod davranışı birbiriyle çelişmez.

### 4.1 İki ayrı release yolu

Belirsizliği azaltmak için release’i iki hatta ayır:

| Hat | Anlamı | Ne zaman seçilmeli? | Dış bağımlılık |
|---|---|---|---|
| **A — Source / CLI / Enterprise self-hosted release** | Core, Team, Enterprise ve CLI hattı release-ready olur. | Önce bunu kapat. Projeyi teknik olarak bitirme hissini en hızlı bu verir. | Düşük. Apple/Windows signing gerektirmez. |
| **B — Desktop Operator Panel installer release** | macOS/Windows imzalı desktop artifact üretilir. | Hat A temizlendikten sonra veya paralel yürütülebilir. | Yüksek. Apple notarization ve Windows Authenticode gerekir. |

**Önerilen karar:** Önce Hat A’yı kapat. Hat B’yi “external credential blocker” olarak ayrı takip et. Böylece Apple/Windows secret beklediğin için tüm proje bitmemiş gibi hissettirmez.

---

## 5. Kapsam dondurma kararı

Bu plan yürürlüğe girdikten sonra aşağıdaki kurala uy:

> **Yeni büyük özellik yok. Önce gate, evidence, qualification ve release kapanışı.**

### 5.1 Release kapsamına alınacak işler

- Core regression fix
- Test kırıkları
- Contract/schema drift fix
- Team resume ve approval continuation olgunlaştırma
- Enterprise signing / key management / rotation drill
- Qualification runner ve signed evidence
- Operator Panel release gate fixleri
- Computer-use fail-closed / qualification / replay güvenlik fixleri
- Dokümantasyonun gerçek teknik durumla hizalanması

### 5.2 Release kapsamına alınmayacak işler

- Cloud multi-tenant control plane
- Unrestricted autonomous desktop control
- Windows/Linux live computer-use enablement without qualification
- Workflow builder
- Policy IDE/editor
- Tam IAM/SSO ürünü
- Yeni büyük research model/router mimarisi
- Yeni UI kapsam genişletmeleri
- Marketing / landing / satış / growth işleri

Bu işler `future/` veya `post-v1.0` backlog’a taşınmalı.

---

## 6. Yol haritası

Aşağıdaki fazlar sırayla kapanmalı. Bir faz kapanmadan sonraki fazda yeni özellik geliştirme yapılmamalı.

---

### Faz 0 — Durum dondurma ve kanıt klasörü

**Amaç:** Projenin bugünkü gerçek durumunu tek bir teknik snapshot’a bağlamak.

**Yapılacaklar:**

```bash
mkdir -p artifacts/readiness/2026-05-10

git status --short | tee artifacts/readiness/2026-05-10/git_status.txt
git rev-parse HEAD | tee artifacts/readiness/2026-05-10/head_commit.txt
uv run binliquid --version | tee artifacts/readiness/2026-05-10/version.txt
uv run binliquid config resolve --profile balanced --json \
  | tee artifacts/readiness/2026-05-10/config_balanced.json
uv run binliquid operator capabilities --json \
  | tee artifacts/readiness/2026-05-10/operator_capabilities.json
```

**Kapanış kriteri:**

- Repo durumu kayıt altına alındı.
- HEAD commit kayıt altına alındı.
- Config ve operator capability çıktıları artifact olarak saklandı.
- Bu dosya repo içinde `docs/PROJECT_CLOSURE_PLAN.md` veya benzer bir adla tutuldu.

**No-Ship:**

- Git worktree belirsiz / kirli ama kayıt altına alınmamışsa.
- Hangi commit’in release adayı olduğu bilinmiyorsa.

---

### Faz 1 — Mainline kalite kapısı

**Amaç:** Kodun genel ana hattını temizlemek.

**Yapılacaklar:**

```bash
make mainline-gate
```

Eğer `make mainline-gate` çok büyükse parçalara böl:

```bash
uv run --extra dev ruff check .
uv run --extra dev pytest -q
make vision-gate
make ui-gate
make rust-gate
git diff --check
```

**Kapanış kriteri:**

- Ruff geçer.
- Full pytest geçer.
- Vision gate geçer veya açık blocker olarak ayrılır.
- UI gate geçer.
- Rust bridge tests geçer.
- `git diff --check` temizdir.

**No-Ship:**

- Full test kırıkken release planına devam edilirse.
- Schema drift var ama contract güncellenmemişse.
- Fail-closed güvenlik davranışı test dışı kalmışsa.

---

### Faz 2 — Team Runtime pilot kapanışı

**Amaç:** Team Runtime’ı “pilot-hardened” seviyeden “controlled release-ready” seviyeye taşımak.

**Yapılacaklar:**

```bash
make pilot-gate
```

Ayrıca:

```bash
uv run binliquid team validate --spec examples/team/restricted_pilot.yaml --json
uv run binliquid team pilot-check \
  --spec examples/team/restricted_pilot.yaml \
  --profile restricted \
  --mode deterministic \
  --report artifacts/team_pilot_report.json \
  --json
uv run binliquid team replay \
  --job-id <job_id> \
  --root-dir .binliquid/team/jobs \
  --verify \
  --json
```

**Öncelikli fix alanları:**

1. Larger DAG cases için `team resume` semantiğini güçlendirmek.
2. Approval continuation flow’u daha büyük dependency graph’lerde test etmek.
3. Multi-role regulated workflow spec’lerini docs/examples altında çoğaltmak.
4. Team smoke benchmark + schema checks’i CI gate’e almak.
5. Replay verify ve tamper fixture testlerini kırmızı/yeşil şekilde netleştirmek.

**Kapanış kriteri:**

- `team_pilot_report.json` `overall_status=pass` verir.
- Approval lifecycle şu sırayı bozmadan çalışır: `pending -> approved -> executed -> consumed`.
- Stale approval snapshot fail-closed olur.
- Replay verify temizdir.
- Tampered replay fixture fail verir.
- Memory conflict silent overwrite üretmez.
- Bounded concurrency fallback/serialization visible artifact üretir.

**No-Ship:**

- Approval consumed, executed approval olmadan oluşabiliyorsa.
- Resume sırasında snapshot drift kabul ediliyorsa.
- Team replay nondeterministic hale geliyorsa.
- Shared memory write silent overwrite yapıyorsa.

---

### Faz 3 — Enterprise security ve key-management kapanışı

**Amaç:** Enterprise profile’ı “constrained readiness” seviyesinden release-ready kanıt seviyesine çıkarmak.

**Yapılacaklar:**

```bash
uv run python scripts/prepare_enterprise_fixture.py --root .
make enterprise-gate
```

Ayrıca key-management drill’leri:

```bash
uv run binliquid keys status --profile enterprise --json
uv run binliquid keys rotate-plan \
  --profile enterprise \
  --next-key-id enterprise-signing-next \
  --json
uv run binliquid security baseline --profile enterprise --json
uv run binliquid metrics snapshot --profile enterprise --json
uv run binliquid ga readiness \
  --profile enterprise \
  --report artifacts/ga_readiness_report.json \
  --json
uv run binliquid keys verify \
  --profile enterprise \
  --path artifacts/ga_readiness_report.json \
  --json
```

**Öncelikli fix alanları:**

1. `env_hmac` uyumluluk yolunun enterprise artifact signing için kullanılmaması.
2. `local_file` asymmetric signing’in minimum GA yolu olarak temiz çalışması.
3. Revocation manifest enforce edilmesi.
4. Rotation dry-run’ın release candidate sign-off öncesi çalışması.
5. Historical artifact verification’ın rotation sonrası geçmesi.
6. Startup abort koşullarının gerçek config üzerinde test edilmesi.

**Kapanış kriteri:**

- `security baseline` `overall_status=pass` verir.
- Enterprise startup abort koşulları test edilir.
- `ga_readiness_report.json` imzalanır ve verify edilir.
- Support bundle redacted ve signed manifest ile üretilir.
- Backup/restore verification drill geçer.
- Key rotation dry-run artifact üretir.

**No-Ship:**

- Enterprise mode’da identity disabled ise.
- HMAC compatibility signing enterprise artifact için kullanılıyorsa.
- Trusted verification keys yoksa.
- Prod/staging aynı artifact veya store root’u paylaşıyorsa.
- Privacy/debug defaults zayıflatılmışsa.

---

### Faz 4 — Qualification run ve soak kanıtı

**Amaç:** “Çalışıyor” iddiasını süreli, imzalı, tekrar edilebilir qualification evidence’a dönüştürmek.

**Aday smoke-soak:**

```bash
uv run binliquid qualification run \
  --profile enterprise \
  --mode mixed \
  --soak-hours 6 \
  --output-root artifacts/qualification \
  --json
```

**Release-candidate soak:**

```bash
uv run binliquid qualification run \
  --profile enterprise \
  --mode mixed \
  --soak-hours 24 \
  --output-root artifacts/qualification \
  --json
```

**2026-05-11 durum:** 24h release-candidate soak LaunchAgent olarak
başlatıldı. Run id: `rc24h-20260511T153314Z`. Çalışma klasörü:
`/private/tmp/binliquid_soak_rc24h-20260511T153314Z`. Supervisor status:
`artifacts/qualification/supervisor/rc24h-20260511T153314Z/status.json`.
Heartbeat `2026-05-11T15:36:09Z` itibarıyla güncel ve süreç `running`.
Beklenen bitiş yaklaşık `2026-05-12T15:34Z` / `2026-05-12 18:34 Europe/Istanbul`.

**2026-05-12 sonuç:** 24h release-candidate soak completed successfully.
Supervisor status `completed_success`, exit code `0`, final heartbeat
`2026-05-12T15:34:17Z`. Signed qualification report verification PASS:
`verified=true`, `signature_verified=true`, `signature_mode=ed25519_local_file`.
Qualification report: `qualification_status=pass`, `recommended_status=green`,
`go_no_go=go`. Post-run GA readiness: `overall_status=green`, `go_no_go=go`.
The 24h duration is recorded under the existing `soak_6h_flow` workload:
`duration_seconds=86401`, `evidence_verified=true`, `replay_verify_status=pass`,
`signing_verify_status=pass`, `blocking_findings=[]`. **2026-05-12
alignment:** reporting was fixed so future 24h runs publish the same sustained
evidence through optional `24h_soak_flow` when it meets the 24h threshold. The
completed run was re-signed as aligned evidence with `24h_soak_flow=pass`,
`duration_seconds=86401`, `evidence_verified=true`, and no
`24h soak evidence not yet published` residual risk.
Local evidence copy:
`artifacts/readiness/2026-05-12/qualification_rc24h_20260511T153314Z/`.
SHA256:
`qualification_report.json=79372fb197c2645a570882f449697ed48d6cb6d15195205b5b0cdfdc0e78ed63`,
`qualification_report_aligned_24h.json=65a61ed36f3e1ef06d61b0a38bcf44cdb86d673f84559108a576b9528ea6e3dd`,
`ga_readiness_report_after_24h.json=7c3a43218e4d861a2cb476e192981e71f79de9ac0cceebf10572f2338007354b`,
`supervisor_status.json=981bdb13a47ccc8e1d62a676a4d8526be62ca82051df758ecc382bbf63c6b237`.

**Final pre-GA soak:**

```bash
uv run binliquid qualification run \
  --profile enterprise \
  --mode mixed \
  --soak-hours 72 \
  --output-root artifacts/qualification \
  --json
```

**Kapanış kriteri:**

- `0` replay/audit integrity failure.
- `0` duplicate side effect.
- `0` restore verification failure.
- Silent shared-state overwrite yok.
- Unclassified provider/runtime failure yok.
- SQLite integrity soak öncesi ve sonrası geçer.
- Artifact growth retention forecast içinde kalır.
- Qualification report signed olur.
- `ga readiness` signed qualification artifact’ı doğrular.

**No-Ship:**

- Qualification artifact unsigned ise.
- Replay/audit integrity failure varsa.
- Provider failure unclassified kalıyorsa.
- Restore verification kırılıyorsa.
- `ga readiness` green/go vermiyorsa ve blocker açıklanmamışsa.

---

### Faz 5 — Operator Panel desktop release gate

**Amaç:** Operator Panel’i beta/implementation-ready seviyesinden imzalı ve gate’li desktop release artifact seviyesine taşımak.

Bu faz Hat B’ye aittir. Hat A release’i için blocker yapılmamalı; ayrı tutulmalı.

#### 5.1 macOS signing + notarization

**Gerekli secret’lar:**

- `MACOS_SIGNING_IDENTITY`
- `MACOS_SIGNING_CERT_P12_B64`
- `MACOS_SIGNING_CERT_PASSWORD`

Notarization için bir mod seçilmeli:

API key mode:

- `APPLE_NOTARY_KEY_ID`
- `APPLE_NOTARY_ISSUER_ID`
- `APPLE_NOTARY_KEY_P8_B64`

veya Apple ID mode:

- `APPLE_ID`
- `APPLE_TEAM_ID`
- `APPLE_APP_PASSWORD`

**Kapanış kriteri:**

- `.app` ve `.dmg` signed.
- `codesign --verify --deep --strict` PASS.
- `xcrun notarytool submit --wait` PASS.
- `xcrun stapler staple` ve `xcrun stapler validate` PASS.
- Clean macOS user/VM Gatekeeper open test PASS.

**No-Ship:**

- Notarization yoksa.
- Stapler validate yoksa.
- Gatekeeper clean-machine open test yoksa.
- Credential yokken release “PASS” gibi gösteriliyorsa.

**2026-05-12 durum:** `release-macos` environment secrets/variables rechecked;
required signing/notarization credentials are still absent. macOS release
workflow run `25751802651` was started, but both macOS jobs failed before any
workflow step ran because GitHub Actions could not allocate runners: account
payments/spending limit must be fixed. No fresh credential preflight artifact
was produced by that run. Next blocker: fix GitHub Actions billing/spending
limit, then provision macOS signing/notarization credentials and rerun
`operator-panel-release-macos.yml`.

#### 5.2 Windows signed RC + clean VM smoke + promote gate

**Sıra:**

1. Windows CI çalışır. **2026-05-10 durum:** PASS. GitHub Actions run
   `25638465677`; `windows-2022` zorunlu lane ve `windows-2025` canary lane
   success.
2. Windows signed RC workflow çalışır. **2026-05-10 durum:** workflow run
   `25638818041` completed, but signed RC remains blocked by missing
   `WINDOWS_SIGNING_CERT_PFX_B64` and `WINDOWS_SIGNING_CERT_PASSWORD` secrets.
   `windows-release-status.json` reports `status=blocked_external_credentials`,
   `signed=false`, `timestamped=false`, and `signed_rc_allowed=false`.
3. `windows-release-status.json` yalnızca signed RC kararı için okunur.
   **2026-05-10 durum:** confirmed; public release gate remained separate and
   reported `public_release_allowed=false`. Local verification PASS:
   `uv run --extra dev pytest -q tests/test_windows_release_gate.py
   tests/test_windows_release_workflows_static.py`.
4. Signed installer SHA256 ile clean Windows smoke workflow çalışır.
   **2026-05-10 durum:** blocked until signed RC exists. GitHub repo and
   `release-windows` environment secrets were rechecked; signing secrets are
   still absent. Clean smoke/promote workflow inputs are documented in
   `docs/HAT_B_DESKTOP_RELEASE_HANDOFF_2026-05-10.md`.
   **2026-05-11 durum:** still blocked. Repository-level secrets and
   `release-windows` environment secrets were rechecked and remain absent;
   only `WINDOWS_TIMESTAMP_URL` is configured. Clean smoke was not run because
   no signed RC installer exists. Preparation advanced: the Windows release
   workflow now preflights signing credentials before checkout/build and
   uploads `operator-panel-windows-credential-preflight` evidence.
   GitHub Actions run `25654446077` verified the preflight behavior:
   `Validate Windows signing credentials` failed with
   `status=blocked_external_credentials`, uploaded credential preflight
   evidence, and skipped checkout/build/signing/public-gate steps.
   **2026-05-12 durum:** `release-windows` environment secrets were rechecked
   and remain absent; only `WINDOWS_TIMESTAMP_URL` is configured. Windows
   signed-RC workflow run `25752181105` was started, but the `windows-2022` job
   failed before any workflow step ran because GitHub Actions could not
   allocate a runner: account payments/spending limit must be fixed. No fresh
   credential preflight artifact or signed-RC artifact was produced by that
   run.
5. Promote workflow çalışır.
6. `windows-public-release-gate.json` `status=pass` verir.
7. Ancak ondan sonra public/enterprise Windows artifact üretilebilir.

**Kapanış kriteri:**

- `windows-2022` CI PASS.
- Authenticode signed + timestamped + `signtool verify` PASS.
- Clean VM installer smoke PASS.
- Installed runtime/capabilities/doctor evidence PASS.
- Runtime manifest ve bundle hash evidence PASS.
- `windows-public-release-gate.json` şu çıktıyı verir:

```json
{
  "status": "pass",
  "public_release_allowed": true,
  "blocking_reasons": []
}
```

**No-Ship:**

- `windows-public-release-gate.json` yoksa.
- `public_release_allowed != true` ise.
- `blocking_reasons` boş değilse.
- Installer smoke unsigned smoke ile yapıldıysa.
- `clean_vm_claimed != true` ise.
- Signed RC installer hash mismatch varsa.
- Windows computer-use enabled görünüyorsa.

---

### Faz 6 — Computer-Use qualification ve sınır kapısı

**Amaç:** Computer-use tarafını güvenli ve doğru iddia seviyesinde tutmak.

Computer-use için ana kural:

> Uygulama yapılmış olması destek iddiası için yeterli değildir; platform support ancak qualification evidence ile söylenebilir.

**Varsayılan kontroller:**

```bash
uv run binliquid computer-use doctor --platform all --json
uv run binliquid computer-use summary \
  --root-dir .binliquid/team/jobs \
  --limit 20 \
  --json
uv run binliquid operator capabilities --json
```

**Deterministic qualification:**

```bash
uv run binliquid computer-use qualify \
  --runtime vision-first \
  --suite smoke \
  --mode deterministic \
  --json
```

**Platform matrix:**

```bash
uv run python scripts/evaluate_computer_use_platform_matrix.py \
  --profile balanced \
  --output artifacts/computer_use_platform_matrix.json \
  --markdown artifacts/COMPUTER_USE_PLATFORM_MATRIX.md
```

**macOS supervised local qualification koşulları:**

- Screen Recording manuel verilmiş olmalı.
- Accessibility manuel verilmiş olmalı.
- Local vision provider hazır olmalı.
- Raw screenshot persistence disabled kalmalı.
- Step approval required kalmalı.
- Live opt-in açıkça verilmiş olmalı.
- Replay verification geçmeli.

**Kapanış kriteri:**

- Raw screenshot persisted count `0`.
- Sensitive/risky surfaces fail-closed.
- Stale approval snapshot fail-closed.
- Replay hash-chain ve policy invariant verification PASS.
- Windows `WINDOWS_COMPUTER_USE_NOT_QUALIFIED` olarak kalır.
- Linux `LINUX_COMPUTER_USE_NOT_QUALIFIED` olarak kalır.
- macOS için yalnızca fresh supervised qualification evidence varsa dar destek iddiası yapılır.

**No-Ship:**

- Windows/Linux live computer-use enabled ise.
- Raw screenshot default persisted ise.
- Terminal control default deny değilse.
- Sensitive surface stop/deny yerine execute ediyorsa.
- Deterministic mock qualification real-world reliability kanıtı gibi gösteriliyorsa.
- Replay business correctness kanıtı gibi gösteriliyorsa.

---

### Faz 7 — Release cut ve kapanış

**Amaç:** Geliştirme döngüsünü kapatıp release artifact / evidence pack üretmek.

**2026-05-10 durum güncellemesi:**

- Hat A için tag kesildi ve origin'e push edildi:
  `hat-a-v0.4.1-2026-05-10`.
- Hat A evidence pack üretildi, arşivlendi ve GitHub'da draft/prerelease
  olarak yüklendi.
- Bu durum yalnızca Source / CLI / Enterprise self-hosted candidate kapsamıdır.
  Hat B desktop installer release iddiası yoktur.

**Yapılacaklar:**

1. Release branch veya tag oluştur.
2. Tüm gate artifact’larını tek klasöre topla.
3. README, RELEASE_CHECKLIST, QUALIFICATION_MATRIX ve release notes’u gerçek durumla hizala.
4. No-ship listesi boş değilse release yapma.
5. Release notes içinde desteklenen ve desteklenmeyen yüzeyleri açık yaz.
6. Post-release backlog’u ayrı dosyaya taşı.

**Önerilen artifact pack:**

```text
artifacts/release-pack/<version>/
  head_commit.txt
  git_status.txt
  test_summary.json
  security_posture.json
  team_pilot_report.json
  qualification_report.json
  ga_readiness_report.json
  metrics_snapshot.json
  support_bundle_manifest.json
  computer_use_platform_matrix.json
  operator_capabilities.json
  windows-public-release-gate.json       # varsa
  macos_notarization_evidence.json       # varsa
```

**Kapanış kriteri:**

- Hat A release için Core + Team + Enterprise + Qualification gates geçmiştir.
- Hat B release için macOS/Windows desktop gate’leri ayrıca geçmiştir.
- Kalan işler post-v1.0 backlog’a taşınmıştır.
- Yeni özellik ekleme döngüsü durdurulmuş ve release tag’i kesilmiştir.

---

## 7. Nihai “hazır” tanımı

Aşağıdaki checklist tamamlandığında mevcut geliştirme döngüsü bitmiş sayılır.

### 7.1 Hat A — Source / CLI / Enterprise self-hosted release

- [x] Git worktree temiz veya değişiklikler bilinçli commit’lenmiş.
- [x] `make mainline-gate` PASS.
- [x] `make pilot-gate` PASS.
- [x] `make enterprise-gate` PASS.
- [x] `make qualification-run` en az 6h candidate smoke-soak ile PASS.
- [x] 24h release-candidate soak PASS. 2026-05-12 run
  `rc24h-20260511T153314Z`; supervisor `completed_success`, signed
  qualification report verified, GA readiness green/go. Reporting alignment
  fixed and aligned signed evidence published with `24h_soak_flow=pass`.
- [x] `ga_readiness_report.json` signed ve verify edilmiş.
- [x] `security_posture.json` signed ve verify edilmiş.
- [x] Key rotation dry-run PASS.
- [x] Backup/restore verification PASS.
- [x] Replay/signature tamper drills PASS.
- [x] README ve docs gerçek destek sınırlarıyla uyumlu.
- [x] Computer-use claims qualification evidence dışına taşmıyor.

Durum: Hat A candidate kapsamı kapandı. Bu, 24h RC/final-GA claim değildir;
6h signed qualification evidence ile desteklenen draft/prerelease candidate'tır.

### 7.2 Hat B — Desktop installer release

- [ ] macOS codesign PASS.
- [ ] macOS notarization PASS.
- [ ] macOS stapler PASS.
- [ ] macOS clean-machine Gatekeeper open PASS.
- [ ] Windows signed RC PASS.
- [ ] Windows clean VM smoke PASS.
- [ ] Windows promote gate PASS.
- [ ] `windows-public-release-gate.json` `status=pass`, `public_release_allowed=true`, `blocking_reasons=[]`.
- [ ] Windows computer-use disabled evidence PASS.

Hat B’deki maddeler tamamlanmamışsa proje Hat A olarak release edilebilir; fakat desktop installer release iddiası yapılmaz.

Durum: Hat B blocked. macOS signing/notarization credentials, Windows
Authenticode signing credentials, signed RC evidence, and clean-machine smoke
evidence hazır olmadan bu checklist işaretlenmeyecek. Ayrıntılı handoff:
`docs/HAT_B_DESKTOP_RELEASE_HANDOFF_2026-05-10.md`. Tracking issue:
https://github.com/bakiacikgoz/BinLiquidAI/issues/4.

---

## 8. Çalışma ritmi

### Haftalık döngü

**1. gün — Gate günü**

- Mainline, pilot, enterprise gate çalıştır.
- Kırıkları listele.
- Yeni feature ekleme.

**2–3. gün — Fix günü**

- Sadece gate kırıklarını ve release blocker’larını düzelt.
- Her fix için ilgili test ekle veya mevcut testi güçlendir.

**4. gün — Evidence günü**

- Qualification, security baseline, metrics snapshot, support bundle üret.
- Artifact’ları release-pack klasörüne taşı.

**5. gün — Scope review günü**

- Yeni gelen fikirleri `post-v1.0` backlog’a ayır.
- No-ship listesini kontrol et.
- Release notes ve docs gerçek durumu söylüyor mu bak.

---

## 9. Görev seçme kuralı

Her yeni görev şu dört sorudan en az birine “evet” demiyorsa release öncesi yapılmamalı:

1. Bir gate’i yeşile çeviriyor mu?
2. Bir no-ship riskini kapatıyor mu?
3. Qualification evidence üretmeye yardım ediyor mu?
4. Docs ile gerçek runtime davranışı arasındaki çelişkiyi gideriyor mu?

Eğer cevapların tamamı “hayır” ise görev `post-v1.0` backlog’a gider.

---

## 10. Öncelik sırası

1. **Fail-closed güvenlik ve governance correctness**
2. **Contract/schema stability**
3. **Replay/audit integrity**
4. **Enterprise signing/key management**
5. **Qualification evidence**
6. **Operator Panel release artifact gates**
7. **Computer-use platform qualification**
8. **Research/router tuning**
9. **Yeni özellikler**

Bu sırayı bozma. Özellikle yeni özellikler, release evidence tamamlanmadan ana hatta alınmamalı.

---

## 11. Kritik teknik riskler

| Risk | Etki | Önlem |
|---|---|---|
| Sürekli yeni feature ekleme | Release hiç kapanmaz. | Kapsam dondurma ve no-new-feature kuralı. |
| External signing secrets beklemek | Proje bitmemiş hissi verir. | Hat A ve Hat B’yi ayır. |
| Computer-use overclaim | Güvenlik ve doğruluk riski. | Qualification evidence olmadan support claim yok. |
| Enterprise signing zayıf kalır | GA readiness bloke olur. | `local_file` asymmetric signing + rotation drill. |
| Replay/audit integrity kırığı | SEV0 release blocker. | Tamper tests + replay verify mandatory. |
| Shared memory silent overwrite | Multi-agent güvenilirliğini bozar. | Conflict-heavy soak + bounded concurrency checks. |
| Docs gerçek durumdan daha iddialı | Yanlış release claim. | Docs alignment gate. |

---

## 12. İlk somut adım

Bugün yapılacak ilk iş:

```bash
mkdir -p artifacts/readiness/2026-05-10
make mainline-gate | tee artifacts/readiness/2026-05-10/mainline_gate.log
```

Eğer bu çok büyükse:

```bash
uv run --extra dev ruff check . | tee artifacts/readiness/2026-05-10/ruff.log
uv run --extra dev pytest -q | tee artifacts/readiness/2026-05-10/pytest.log
corepack pnpm --dir apps/operator-panel test | tee artifacts/readiness/2026-05-10/ui_test.log
corepack pnpm --dir apps/operator-panel lint | tee artifacts/readiness/2026-05-10/ui_lint.log
corepack pnpm --dir apps/operator-panel build | tee artifacts/readiness/2026-05-10/ui_build.log
cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml \
  | tee artifacts/readiness/2026-05-10/rust_gate.log
```

Sonra tek bir dosya üret:

```text
artifacts/readiness/2026-05-10/READINESS_SUMMARY.md
```

Bu summary şu üç başlığı içersin:

1. Green gates
2. Red gates
3. Next blocker to fix

---

## 13. Kapanış prensibi

Bu planın ana ilkesi:

> Proje artık “ne ekleyebilirim?” sorusundan “hangi gate’i kapatırsam release olur?” sorusuna geçmelidir.

Mevcut geliştirme döngüsünü bitirecek nokta budur.
