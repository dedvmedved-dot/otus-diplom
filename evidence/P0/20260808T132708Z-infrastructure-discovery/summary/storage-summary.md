# Storage Summary
RUN_ID: 20260808T132708Z

| Endpoint | Device | Type | Size | Model | Serial |
| --- | --- | --- | --- | --- | --- |
| 38 | SCSI_Target0_LUN0 | HDD | ~480 GB | Adaptec OS | N/A |
| 38 | USB_Device0 | USB | — | — | — |
| 38 | USB_Device1 | USB | — | — | — |
| 40 | USB_Device0 | USB | — | — | — |
| 40 | USB_Device1 | USB | — | — | — |
| 39 | — | — | — | UNREACHABLE | — |

Note: Both 38 and 40 have Adaptec RAID controllers. 40's OS disk(s) are not
exported as individual drives in Redfish. Full storage discovery requires
OS-level access (lsblk, /dev/disk/by-id, LVM, filesystem info).
