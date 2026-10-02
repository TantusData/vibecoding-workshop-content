# Zebra ZT411 label printers — first-line troubleshooting

_Space: IT-SD · Owner: Marta Nowak · Last edited: 2026-02-02_

Applies to the Zebra ZT411 printers on Lines 1, 2 and 3 (assets NF-PRN-L1-01, NF-PRN-L2-01,
NF-PRN-L3-01).

## Blank labels / every second label blank

Almost always a media calibration problem after a ribbon or label-roll change.

1. Hold **Pause + Cancel** for 2 s to run the media calibration; the printer feeds a few labels.
2. If labels are still blank, check the ribbon is loaded with the **ink side facing the labels**
   (the "coated side out" arrow on the ribbon core points towards the printhead).
3. Check the label sensor position matches the gap/notch on the label stock.
4. Print a test label from the printer menu. If the test label is fine but production labels are
   blank, the problem is the label template, not the printer — raise it to apps.

## Labels shifted up/down

Run the calibration (step 1 above) and check the "tear-off" setting in the printer menu is `0`.

## Printer offline in the MES

Check the Ethernet link light; power-cycle the printer; confirm the IP on the printer's network
settings screen matches the one in the MES device list. Do not change the IP yourself — raise a
ticket to infra.

## When to replace

Printheads are consumables. If the test label shows a permanent vertical white line, the printhead
is worn; the servicedesk keeps one spare per line.
