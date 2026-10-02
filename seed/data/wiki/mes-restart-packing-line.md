# Restarting the packing-line MES (NF-SRV-MES-01)

_Space: IT-APPS · Owner: Agnieszka Dąbrowska · Last edited: 2026-06-11_

Use this when the MES on the packing line stops accepting batch orders, shows "service
unavailable" on the operator terminals, or after a server reboot when the services did not come
back in order.

## Before you start

- Confirm with the packing shift lead that **no batch is running**. A restart mid-batch loses the
  batch record and the line has to re-scan every case. If a batch is running, wait for it to close.
- Announce the restart in the `#packing-line` channel with the expected duration (about 8 minutes).
- Have the apps on-call on the phone if you are not from the apps team.

## Procedure

1. Log on to NF-SRV-MES-01 with your **own** admin account. Credentials live in the password
   vault (KeePass on the IT share) — never in a ticket, a chat or on a sticky note. If you find a
   password written in a ticket, tell the infra on-call so it gets rotated.
2. Open `services.msc` and stop the services in this order:
   1. `MES Terminal Gateway`
   2. `MES Batch Scheduler`
   3. `MES Core Service`
3. Wait until all three show "Stopped". Do not kill processes from Task Manager.
4. Start them in the **reverse** order: `MES Core Service` → `MES Batch Scheduler` →
   `MES Terminal Gateway`. Wait ~30 s between each; the Core Service needs to finish its database
   check first.
5. On an operator terminal, open the batch screen and create a test batch order in the `TEST`
   product family, then cancel it. If it is accepted, the restart worked.
6. Post the result to the NordDesk incident and close the announcement in `#packing-line`.

## If it still fails

- "Service unavailable" persists: check the SQL Server on `nf-sql-01` is reachable from the MES
  host (port 1433). The Core Service logs to `D:\MES\logs\core.log`.
- Terminal Gateway will not start: port 8443 is probably still held by a previous instance —
  reboot the server (this is the one case where a reboot is the right answer).
- Anything else: raise to the vendor under the support contract, hotfix 7.4.2 fixes the known
  batch-order timeout (see CHG-0310).
