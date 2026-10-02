# Palletiser KX-90 — maintenance handbook (Line 3)

_Space: OT-MAINT · Owner: Marek Zieliński · Last edited: 2026-05-08 · Applies to asset NF-PLT-003_

This page is the maintenance reference for the Kramer Automation KX-90 palletiser installed at the
end of Line 3 in the packing hall. It replaces the vendor's paper binder, which is still in the OT
office cabinet for anything not covered here. Read the whole page once before your first
intervention; afterwards the section you need is usually "Lockout and safe access".

## 1. Purpose and scope

The machine stacks finished cases from Line 3 onto euro pallets, wraps them and pushes them to the
outfeed conveyor. It is the last automated step before the warehouse, which is why a stop here backs
up the entire line within about ten minutes. Everything in this handbook is written for the OT
maintenance team and the shift leads who are authorised to perform first-line interventions. It is
not written for operators: operators may reset a fault from the HMI once, and if the fault returns
they call the OT on-call number instead of trying again.

## 2. Maintenance philosophy

Most stoppages on this machine are not mechanical failures. They are the consequence of sensors
that have drifted out of alignment during cleaning, of a wrapping film roll loaded the wrong way
round, or of a case that arrived deformed from upstream. Before assuming a component is broken,
walk the product path from the infeed to the outfeed and look for the obvious. The vendor's
statistic for our model family is that roughly seven out of ten fault calls are resolved without
replacing a single part.

Preventive work is scheduled in three rhythms: a daily check at the start of the day shift, a
weekly inspection on Monday mornings before production, and a quarterly service performed together
with the vendor engineer under the service contract. Do not skip the weekly inspection because the
machine "ran fine last week" — the weekly inspection is where gripper wear and belt tension are
caught early.

## 3. Daily and weekly checks

Daily, before the first pallet: confirm the safety fence gates are closed and the light curtain
self-test shows green on the HMI; check that the film roll has at least a quarter left; clear any
case debris from the layer table; verify the outfeed conveyor is empty. Record the check in the
shift log even if nothing was found.

Weekly, on Monday: inspect the gripper pads for cracks and glazing and replace them in pairs; check
the layer-table belt tension by hand (about 10 mm of deflection at the centre); wipe the position
sensors on the gripper carriage and the layer table with a dry cloth — never with the cleaning foam
used on the line; check the pallet dispenser for bent forks; look at the fault history on the HMI
and note any fault code that occurred more than three times during the week. Recurring codes go into
a NordDesk ticket against the system `palletiser-l3` so they are visible to the whole team.

## 4. Common fault codes

**F12 — film break.** Re-thread the film and press reset. If it recurs within an hour, check the
pre-stretch rollers for adhesive build-up.

**F19 — layer table timeout.** Usually a case jammed at the pusher. Clear the case; the machine
resumes automatically.

**F27 — gripper position.** The gripper carriage did not reach its taught position within the
allowed time. Almost always a misaligned or dirty position sensor (S3 on the carriage, S4 on the
column). This is the fault that requires opening the drive panel, and therefore the full lockout
procedure below. Do not attempt to realign S3 with the machine merely paused.

**F31 — pallet dispenser empty.** Load pallets. Not a maintenance call.

**F44 — safety circuit open.** A gate or the light curtain was interrupted. Close and reset. If
the code appears with all gates closed, the safety relay needs checking by an electrician; do not
bridge anything.

## 5. Lockout and safe access

This section is mandatory for any intervention that opens a panel, enters the fenced area beyond
the gate threshold, or touches the gripper carriage or its drives. It applies regardless of how
short the job is expected to be.

1. Stop the machine from the HMI and put it in **maintenance mode**.
2. Switch off the main isolator and apply your personal padlock and tag.
3. **Wait the mandatory 20-minute cool-down** before opening any drive panel. The servo drives and
   the braking resistor stay hot and the DC bus stays charged for well over ten minutes after
   isolation; the 20 minutes is a hard minimum, not a guideline, and it is written on the panel door.
4. **Two-person sign-off:** a second authorised person (another OT technician or the shift lead)
   must verify the isolation, check the cool-down time in the log, and countersign the lockout
   record before the panel is opened. One person alone may not proceed, even on the night shift —
   call the OT on-call if nobody else is on site.
5. Open **panel P3-07** (the drive panel on the column side, marked with the yellow triangle) only
   after steps 3 and 4 are complete. All other panels stay closed unless the job requires them.
6. Test for dead on the drive terminals before touching anything.
7. After the work: close and latch the panel, remove your padlock, restore the isolator, clear the
   maintenance mode on the HMI, and run one empty cycle with the fence closed before releasing the
   machine to production.

The lockout record lives in the yellow folder on the OT office wall. Every entry needs the time of
isolation, the time the panel was opened, and both signatures. Auditors check it.

## 6. Spare parts on site

Gripper pads (2 sets), position sensors S3/S4 (one each), film roll clamps, one pallet dispenser
fork, a set of safety relay fuses. Anything else is a vendor order under the service contract and
typically arrives within two working days.

## 7. Escalation

If a fault is not cleared within 30 minutes, or if any part of the safety circuit is suspected, the
shift lead raises or updates the NordDesk incident and calls the vendor line listed on the service
contract. Line 3 losses are booked at roughly 14 pallets per hour of standstill; make sure the
incident carries the standstill start time so the impact can be estimated later.
