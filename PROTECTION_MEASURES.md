# SecureNet — Protection measures (per attack)

How Advanced Protection stops each attack the model is trained on, and **why a wrong label
(e.g. SQL Injection read as DoS) does not break the protection.**

---

## 1. How protection works (and why the label doesn't matter)

When **Advanced Protection** is ON and the network turns abnormal (attacks > 30 % of the recent
window), SecureNet blocks the **attacker's SOURCE IP** at the Windows Firewall
(`netsh advfirewall ... action=block remoteip=<attacker>` — `app/ml/protection.py`).

This block is **type-agnostic**: it does **not** depend on *which* attack the model named. It blocks
the machine that is attacking, so **every** packet from that machine stops — whatever it was doing.

> **"Sometimes SQL Injection is detected as DoS — how is it protected then?"**
> It is still protected, fully. The model's label is only used for the *report wording*
> ("possible attack: …"). The **action** is to block the attacker's IP. So whether the flow is
> labelled SQL Injection, DoS, or anything else, the same thing happens: the attacker's IP is
> blocked and the SQL Injection traffic stops with it. A confused label never leaves an attack
> un-protected — the attacker's source is cut off regardless.
>
> This is deliberate. Per-attack-type actions (e.g. "block port 80 for SQLi, rate-limit for DoS")
> would be *fragile* exactly because the label can be wrong. Blocking the source is robust to the
> model's confusion between the web attacks (SQLi / XSS / Web-brute) and DoS.

Two layers feed the block:
- the **ML model** (per-flow attack call), and
- the **behavioural rule layer** (`rule_engine.py`: port scan / host sweep / brute-force / flood /
  ICMP flood) — a cross-flow second opinion that catches what the per-flow model misses.

Both end at the same place: an abnormal source → that source's IP blocked → written to the report
(`action = BLOCKED`), and a one-off **"protection successful / attack still active"** notification.

**Static hardening** (set up once, `harden_victim.ps1`) makes each attack *fail* even before the
block, and is the real fix for payload attacks (SQLi/XSS) that a network IDS can only alert on.

---

## 2. Per-attack table (14 CIC-IDS2018 attacks, Infiltration excluded per request)

| # | Attack label | Dynamic (automatic, on detection) | Static hardening (makes it fail) |
|---|---|---|---|
| 1 | **DoS attacks-Hulk** | block source IP (+ rate-limit) | Apache `mod_evasive` (per-IP request cap) + `mod_ratelimit`, connection caps, caching |
| 2 | **DoS attacks-GoldenEye** | block source IP | `mod_evasive` + `mod_reqtimeout`; cap concurrent connections per IP |
| 3 | **DoS attacks-Slowloris** | block source IP | Apache `mod_reqtimeout` (request timeouts) + min data-rate + max conns/IP |
| 4 | **DoS attacks-SlowHTTPTest** | block source IP | `mod_reqtimeout` + `mod_qos` (slow-request limits) |
| 5 | **DDoS attack-HOIC** *(not a model class → reads as Hulk/Bot; still blocked)* | block/limit source IP | `mod_evasive`; real distributed floods need upstream scrubbing (Cloudflare/ISP) |
| 6 | **DDoS attacks-LOIC-HTTP** *(not a model class → reads as Hulk)* | block/limit source IP | `mod_evasive` + caching; upstream scrubbing for multi-source |
| 7 | **DDoS attack-LOIC-UDP** | block + per-IP UDP rate-limit | drop/rate-limit inbound UDP to unused ports; upstream scrubbing if spoofed |
| 8 | **SSH-Bruteforce** | block source IP | account lockout (5/15 min), `MaxAuthTries 3`, key-only auth + MFA |
| 9 | **FTP-BruteForce** | block source IP | account lockout, strong creds, disable anonymous/unused FTP |
| 10 | **Brute Force -Web** | block source IP | app login lockout/CAPTCHA, rate-limit the login endpoint |
| 11 | **SQL Injection** | block source IP | **WAF (ModSecurity)** + **parameterised queries / input validation** (the real fix) |
| 12 | **Brute Force -XSS** | block source IP | **WAF** + output encoding / CSP / input sanitisation |
| 13 | **Bot / C2 beacon** | block the C2 source/destination | outbound allow-listing, DNS sinkhole, EDR on hosts |
| — | **Infilteration** | *(excluded from the model and from this table per request)* | — |

Behavioural-rule detections also protect, the same way. (They still run internally, but they are
**not shown under these names** — every rule hit is displayed as a single generic **"Reconnaissance"**
label; the specific rule is kept only in the backend log.)

| Rule detection | Dynamic | Static hardening |
|---|---|---|
| **Port scan / host sweep (recon)** | block the scanning IP | close unused ports, default-deny firewall, tarpit/portspoof |
| **Flood / ICMP flood** | block + rate-limit source | per-IP rate limits; disable inbound Echo if needed; upstream scrubbing for spoofed floods |

---

## 3. Honest limits
- IP-blocking is **reactive**: the first few flows still arrive; it stops the *sustained* attack, not
  packet #1. (That's why the 30 % gate + the success/failure notice exist.)
- **Spoofed-source / distributed** floods rotate IPs → host-level blocking can't keep up; those need
  upstream scrubbing.
- **Payload** attacks (SQLi/XSS): the malicious request already reached the app, so a **WAF + code
  fixes** are the real prevention. The IP-block stops that attacker afterwards.
- Blocking is a **detection → prevention** aid, not a guarantee; `harden_victim.ps1` closes the gap.

## 4. Turning it on
1. In the app: **Settings → Advanced Protection → ON** (confirmed by an emailed code).
2. Run SecureNet elevated (the netsh firewall edit needs admin — the app's launcher already is).
3. Run `harden_victim.ps1` once (as admin) for the static hardening above.

**Safety:** Protection can **never** block this PC's own IPs (host addresses + loopback + the optional
`PROTECTION_NEVER_BLOCK` list are always excluded). The attacking VM is blocked; the host is not.
