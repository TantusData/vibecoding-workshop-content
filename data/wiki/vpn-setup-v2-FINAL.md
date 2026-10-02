# VPN setup v2 (FINAL) — remote access after the firewall change

_Space: IT-INFRA · Owner: Anna Kowalczyk · Last edited: 2026-03-14_

After the FortiGate upgrade in March 2026 the VPN moved off the old portal. **This page
replaces the older "VPN setup" page**, which we have not yet deleted because some screenshots on it
are still referenced by the onboarding checklist.

## Client

Use **FortiClient VPN** (not GlobalProtect any more). It is pre-installed on all laptops imaged
after March 2026; older laptops get it from the software portal.

## Connection profile

- Remote gateway: `vpn2.nordfarm.example`
- Port: `443`
- Username: your email address (`firstname.lastname@nordfarm.example`)
- Password: your normal Windows password
- Second factor: approve the push notification in the **Microsoft Authenticator** app. Hardware
  tokens are no longer accepted.

## Access request

Still through NordDesk as an access request; the infra team adds you to the `VPN-Users` group.
Quality technicians additionally need the `LIMS-Remote` group for LIMS reports.

## Known issues

- Push notification never arrives: check the phone has data, then retry; after two failures raise
  a ticket, do not keep retrying (five failures locks the account for 15 minutes).
- Home routers with "SIP ALG" enabled sometimes drop the tunnel — turn it off.
