# cert-manager 1.21.0 (digest-pinned)

Required dependency of Barman Cloud Plugin 0.13.0 (P8B). Scope limited to Barman
Cloud Plugin internal client/server certificates. NOT used for Portal ingress /
ACME / Gateway certificates.

## Images (linux/amd64, digest-pinned)
- controller: quay.io/jetstack/cert-manager-controller@sha256:79a65ab008da7f067d6f68be937ba60d1d8a174168f66b6530c5ed0927c69986
- webhook:    quay.io/jetstack/cert-manager-webhook@sha256:af0a4f097872194799c07e24eda4561ade538fcee1d531d7ff824eeb297b0ae5
- cainjector: quay.io/jetstack/cert-manager-cainjector@sha256:d4962457c0c6b7a1399bdc84bd2748070353b5170bf856f697f09b239187b74a
- acmesolver: quay.io/jetstack/cert-manager-acmesolver@sha256:6198cb796023163a6726589d3f9dbe76bb76289fea8c948ea6feb36e4617122c

## Known issue
cert-manager 1.21.0: Certificate.spec.renewal.policy=Disabled may crash the
trigger controller. P8B MUST NOT use renewal.policy: Disabled.

## Files
- cert-manager-v1.21.0-upstream.yaml — exact official release asset (unaltered)
- cert-manager-v1.21.0-digest-pinned.yaml — all executable images pinned to digest

## Deploy
```
kubectl apply --server-side -f cert-manager-v1.21.0-digest-pinned.yaml
```
Namespace: cert-manager.
