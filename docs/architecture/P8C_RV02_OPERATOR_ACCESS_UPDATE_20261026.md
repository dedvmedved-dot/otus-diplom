# P8C RV-02 — operator access clarification

Date: 2026-10-26 (Europe/Moscow).
Recovered Connector main: 6324d1b3e3bf9147abaa8748d28d76931ded0aba.
Authority: Owner supplies the actual existing access path and requests the instruction correction.
Base inventory gate remains docs/architecture/P8C_RV02_ACCEPTANCE_b805dff_20261026.md.

## Decision / scope
Proceed with the approved base inventory through the existing authorized operator path below. No further "continue" is needed for that read-only collection and subsequent evidence processing.
This updates the access assumption; it does not modify or reapprove different script bytes, grant Portal privileges or open apply/CI/production/Phase2 gates.

## Owner-reported path, not independently runtime-verified here
- Operator origin: skhome01, Office VPN tun1, existing route192.168.194.0/24.
- Target: root@192.168.194.38; reported hostname node-01.
- No node-01 SSH alias is assumed.
- Owner reports Python3.11.2, kubectl client v1.36.2 and existing root-local /etc/kubernetes/admin.conf.
- Target authentication is password-based; do not assume the operator's public key is authorized.
- Edge source: root@5.187.1.37, SSH port2222, existing repository path /root/otus-diplom/portal/networkpolicy/inventory.py.
- Direct GitHub access from node-01 is not established and is not required.

The earlier ACCESS_PATH=NONE described the Hermes host at that time. The operator path is now identified; inventory remains NOT_EXECUTED until actual evidence arrives.

## Transfer and authentication
Use two transfers through skhome01, avoiding a dependency on node-01 reaching Edge/GitHub:
1. On skhome01, use a new private staging directory and the existing authorized Edge authentication to fetch:
~~~sh
scp -P 2222 -o StrictHostKeyChecking=yes root@5.187.1.37:/root/otus-diplom/portal/networkpolicy/inventory.py ./inventory.py
~~~
2. Verify the approved hash on skhome01 before transfer:
~~~sh
printf '%s  %s\n' '7806f494bcee93f31eb2cb0348d2cd8f7cbbf5743261336226a251643d8988a2' 'inventory.py' | sha256sum --check --strict -
~~~
3. In the existing operator session on192.168.194.38 prepare a private staging directory. Copy only the verified script into it:
~~~sh
scp -o StrictHostKeyChecking=yes ./inventory.py root@192.168.194.38:<operator-created-staging-directory>/inventory.py
~~~
Replace the directory placeholder with the actual operator-created path. Do not overwrite unrelated files.
4. Open/use the authorized node session:
~~~sh
ssh -o StrictHostKeyChecking=yes root@192.168.194.38
~~~

Use interactive no-echo password entry or an ALREADY approved protected credential mechanism. No literal password in command arguments, environment evidence, Git, chat or logs. Do not reuse the node password for Edge by assumption.
Keep host-key verification. If a trusted key is not enrolled, the operator verifies its fingerprint through an independent trusted channel before enrollment; on mismatch STOP, do not erase/ignore it. Do not substitute StrictHostKeyChecking=no.
The approved script is standalone Python; a Git clone or dependency installation on node-01 is not required.

## Node-local execution
Use the existing /etc/kubernetes/admin.conf ONLY on node-01; do not copy or display its contents.
In the operator shell:
~~~sh
export KUBECONFIG=/etc/kubernetes/admin.conf
kubectl config current-context
~~~
Confirm the returned context is the intended authorized PAK cluster. This reads only the context name, not credential contents.

From the private staging directory, verify the hash AGAIN and run:
~~~sh
printf '%s  %s\n' '7806f494bcee93f31eb2cb0348d2cd8f7cbbf5743261336226a251643d8988a2' 'inventory.py' | sha256sum --check --strict - &&
python3 inventory.py --context "<approved-context>" --output "<new-nonexistent-output-directory>"
~~~
Source binding:9a98b385c5a484b0a8f79086b432b8b72289ccee; blob5f0e2450358bfd9b08b542f013be5a914b9195a4.
Different bytes -> STOP, even if fetched from the correct Edge path.

Record source/hash, UTC start/end, process exit and client/server version strings in the same context. Review the resulting inventory.jsonl locally and transfer only sanitized output plus safe run metadata.
For nonzero exit, retain safe categories/partial records and report; no silent PASS, access repair, raw stderr disclosure or alternate probe loops.

## Continuation / unchanged gates
Hermes processes the returned evidence under the existing task: verify binding/completeness, reconcile14 FLOW-IDs and8 gaps with record references, preserve UNKNOWN, prepare conditional Phase2 definitions for review.
Only local staging files and base GET/LIST collection are authorized here.
No live policies, production migrations/deployments, CI release/workflow publication/dispatch, provisioning helpers, workflow token, BMC/access bypass or accepted backup/restore/PITR/failover reruns.
NETPOL_APPROVED_FOR_APPLY=NO; P8C=NOT_FINAL_ACCEPTED; P8D-P8G/P9=NOT_AUTHORIZED.
