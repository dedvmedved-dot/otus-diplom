# P7C-B2B-SC1 — Future Runtime Gate: P7C-B2B-SC2

SC2 may start only after the Architect accepts ADR-004.

Expected SC2 stages:
1. prove authorized external placement
2. confirm IPAM allocation
3. confirm DNS
4. confirm TLS/CA model
5. create controlled build environment
6. checkout exact source tag
7. verify exact source commit
8. pin Go toolchain
9. build MinIO
10. create SBOM
11. run vulnerability assessment
12. calculate binary SHA-256
13. preserve build evidence
14. transfer verified artifact to runtime host
15. install MinIO
16. expose S3 on HTTPS/TCP443
17. create bucket
18. enable versioning
19. configure Object Lock
20. create least-privilege credentials
21. test S3 write/read
22. test retention/delete protection
23. verify VLAN143 node path
24. reboot/persistence test
25. STOP for Architect verification

None of these steps are executed in SC1.
