# Shift handover — night 2026-09-10

_Prepared by OpsCopilot for **Piotr Wiśniewski** (outgoing) → **Marek Zieliński** (incoming).
Every bullet must reference a ticket id or a wiki page — no unreferenced claims._

## 1. Open incidents (P1/P2 first)

| Ticket | System | Priority | Status | Since | One-line state |
|---|---|---|---|---|---|
| INC-1039 | mes-packing | P2 | in_progress | 2026-09-10 22:40 | MES refuses new batch orders since Sunday patching; app service restart needed in the documented order (`mes-restart-packing-line`). |

## 2. Tickets needing follow-up on the next shift

- **REQ-2201** — VPN access for Ewa Sikora (Quality) waiting on infra; needs `VPN-Users` +
  `LIMS-Remote` groups (`vpn-setup-v2-FINAL`).
- **CHG-0310** — MES hotfix 7.4.2 proposed for Sun 21 Sep 22:00–23:30; needs CAB approval.

## 3. Anything flagged sensitive

- **INC-1039** — a comment contains a server credential in clear text. Flagged for rotation; not
  repeated here.

## 4. On-call for the next shift

| Team | Name | Reach |
|---|---|---|
| OT   | Marek Zieliński | +48 600 100 201 |
| Infra | Anna Kowalczyk | +48 600 100 301 |
| Servicedesk | Marta Nowak | ext. 4411 |

## 5. One-paragraph summary for management

One P2 open: the packing-line MES is not accepting new batch orders after Sunday's patching; the
line runs on existing batches and a controlled restart is planned for the day shift. Two requests
need routine follow-up. No production line is stopped.
