# RV-02 — bounded follow-up read contract, Architect revision after bcda2f7

Date: 2026-10-27. SOURCE DESIGN ONLY. No live execution/handoff/apply authorization.
This revision supersedes the incomplete S2 plan under evidence/P8/20261027T150000Z-p8c-rv02-s1-s2/.
Historical evidence is not edited. S1 identity source is accepted separately.

## Purpose and limits

Collect missing policy configuration with explicit completeness/compatibility results.
This is NOT a policy evaluator, packet test or proof of EFFECTIVE_POLICY_UNION.
No new cluster read is authorized by this design. The former one-run budget is consumed.
Future live execution requires reviewed new script bytes and a separate Gate, including
a trusted SSH host-key verification path and an authorized current credential.

Reuse base records and Phase-2 C1/C2/S1/S2. Do not reread ObjectStore, Cluster, Barman pods,
full base inventory or accepted registry metadata. D1/I1 renewal is proposed only as
fresh prerequisites to previously BLOCKED Calico reads, not to repeat accepted results.

## Source pins and machine-readable types

1. Calico source: ansible/playbooks/files/calico-v3.32.0.yaml at
bcda2f78e20a5f83a05f021c5bb4726202f6ca0e, blob 21ea9b4b163305ea479bc7708965104465ffc716.
2. CNP candidate: kubernetes-sigs/network-policy-api commit
730bd5474d82a2cf82be8b0c6c2a5515598cc44e, types blob
8f534d3c92ce0acdce8560d8190ebb574ee4240b, standard CRD blob
eca1eca97c14f56836aaf8f2394fa03479e01b5f (bundle v0.2.0/standard in upstream header).
This is a candidate source contract, NOT proof of installed bundle/channel.
3. portal/networkpolicy/followup-typed-contract.json is a mechanical extraction of
the spec schemas for CNP, HostEndpoint and Tier at those pins. Only description keys
were removed recursively; types, required, bounds, defaults, allOf/anyOf, CEL and
Kubernetes extensions are preserved. This artifact is part of the contract, not a
placeholder such as "Peer"/"Protocol to be defined".

The baseline NP/GNP/Felix projection is the already reviewed supplemental.py at
source 3139e08e4243868d5de2aa9f52d054e424e0a653, blob
1b613fbd1e35a109072d2843d6e5f3a3fd47b3d6. Its finite semantic limits remain in force.
Do not broaden these projectors in this iteration or pretend they implement full CRD admission.

## Wrapper, dependencies and exact reads

Fixed context kubernetes-admin@pak-portal, wrapper
kubectl --context kubernetes-admin@pak-portal --request-timeout=15s.
Each subprocess timeout 20s. No arbitrary caller-supplied API paths.
Table paths are literal argv elements following get --raw unless explicitly stated.

| ID | Requirement / existing fact | Exact path or argv tail | Shape/scope | Dependencies | Projection / FLOW-ID |
|---|---|---|---|---|---|
| F-D1 | Renew Calico served-kind guard; previous D1 known | /apis/crd.projectcalico.org/v1 | APIResourceList | none | name/kind/namespaced/verbs; BASELINE/CNI |
| F-I1 | Current bound identity before blocked Calico reads; old I1 accepted as historical | get pods -n kube-system -l k8s-app=calico-node -o json | PodList, kube-system | none | existing safe pod projector + accepted finite identity; CNI |
| F-CS | Compare exact CNP spec contract, which D2 cannot prove | /apis/apiextensions.k8s.io/v1/customresourcedefinitions/clusternetworkpolicies.policy.networking.k8s.io | one cluster-scoped CRD | none | safe schema fingerprint only; BASELINE |
| F-CNP | Actual CNP objects; D2 observed discovery only | /apis/policy.networking.k8s.io/v1alpha2/clusternetworkpolicies | ClusterNetworkPolicyList, cluster | F-CS compatible | CNP contract below; BASELINE |
| F-NP | Prior C3 BLOCKED | /apis/crd.projectcalico.org/v1/networkpolicies | NetworkPolicyList, all namespaces | F-D1 + F-I1 | existing NP projector; BASELINE |
| F-GNP | Prior C4 BLOCKED | /apis/crd.projectcalico.org/v1/globalnetworkpolicies | GlobalNetworkPolicyList, cluster | F-D1 + F-I1 | existing GNP projector; BASELINE |
| F-FELIX | Prior C5 BLOCKED; default only | /apis/crd.projectcalico.org/v1/felixconfigurations/default | one FelixConfiguration, cluster/name=default | F-D1 + F-I1 | existing Felix projector; CNI |
| F-HEP | Host inputs may affect node-backed API endpoint traffic | /apis/crd.projectcalico.org/v1/hostendpoints | HostEndpointList, CLUSTER | F-D1 + F-I1 | HEP contract below; BASELINE/API-6443 |
| F-TIER | Ordering and default action, not order alone | /apis/crd.projectcalico.org/v1/tiers | TierList, cluster | F-D1 + F-I1 | Tier contract below; BASELINE |

F-D1 verifies kind/scope and list verb for NP/GNP/HEP/Tier; get for Felix.
HostEndpoint is cluster-scoped, as both pinned CRD and stored live D1 establish.
A missing/wrong descriptor blocks only the affected dependent reads; malformed D1
blocks all Calico config reads. I1 failure blocks all five Calico config reads.
F-CS failure blocks F-CNP. Independent reads may continue within an eventual bounded run.

## Common output contract and failure handling

Every object: exact apiVersion/kind, nonempty string metadata.name; namespaced
objects additionally require the requested/nonempty namespace. Cluster-scoped metadata
namespace must be absent/empty, never silently accepted as namespaced.
Output identity and labels (string:string map) where needed for selector applicability.
Drop annotations/managedFields/ownerReferences, arbitrary top-level metadata and raw status.
No env/args/Secret/ConfigMap reads, exception text or raw stdout/stderr in evidence.
Safe object names, labels/selectors and secret-ref names are not values of Secrets;
perform content review before publishing output.

For new CNP/HEP/Tier projectors, retain ALL validated semantic spec fields defined in
followup-typed-contract.json; recursively reject unknown semantic keys as UNSUPPORTED.
No blanket dictionary copy. Known extra metadata is dropped. Unknown observed schema
features are UNSUPPORTED, not converted to invented defaults.
Malformed JSON, wrong types, names/scope, missing required fields, failed bounds or
cross-field conditions: PARSE_ERROR, empty output for the affected record.
Do not coerce bool to int, null to a required object, or false to an empty collection.
Omitted optional fields remain omitted; optional arrays absent are not fabricated facts.
Finite numbers only; no NaN/Infinity. Preserve order of policy/rule arrays.

Allowlist validation implements the referenced type/required/enum/min/max/string-length/
array-size/exactly-one/allOf/anyOf contracts. Only four CEL rules occur in the new extracted
specs; implement their explicit equivalents, not a generic CEL interpreter:
- port range start < end;
- network CIDR is valid and canonical/masked;
- HEP has nonempty interfaceName OR nonempty expectedIPs;
- HEP node is present and nonempty.
Kubernetes LabelSelector: matchLabels string map; expression key/operator required,
operator In/NotIn/Exists/DoesNotExist, values nonempty for In/NotIn and absent/empty
for Exists/DoesNotExist. Preserve empty selector {} as match-all, not absent.
Enforce uniqueness for schema set lists; preserve atomic list order.

Error categories: PARSE_ERROR / UNSUPPORTED / TIMEOUT / FORBIDDEN / API_NOT_SERVED /
CONNECTION / GET_FAILED; unmet prerequisite BLOCKED_NOT_EXECUTED.
Pagination limits yield PARTIAL with explicit completeness=false, not OK/empty.
HTTP expiry or failed continuation invalidates completeness; no retry.
Any non-OK/partial/blocked row makes aggregate exit nonzero.
Only sanitized validated output may be retained; failure never emits unprojected content.

## CNP schema compatibility preflight (F-CS)

Read only the named CRD above into memory. Verify CRD apiVersion
apiextensions.k8s.io/v1, kind CustomResourceDefinition, exact metadata.name;
spec.group=policy.networking.k8s.io, names.kind=ClusterNetworkPolicy,
names.plural=clusternetworkpolicies, scope=Cluster; exactly one versions entry named
v1alpha2 with served=true and an object openAPIV3Schema.properties.spec.

Extract that spec subtree; remove description only as a schema annotation at
schema-node positions. Preserve property names inside properties/patternProperties/
definitions/$defs/dependentSchemas maps (including a property called description).
Traverse schema-valued nodes and schema arrays; preserve literal defaults/enums/
examples and extension payloads. Do not apply a blind recursive key deletion.
See FU-05 in docs/architecture/P8C_RV02_REVIEW_4c21b2a_20261028.md and its offline
schema_normalization_reference.py. The accepted pinned hash remains unchanged.
Canonicalize:
JSON UTF-8, sorted keys, separators comma/colon, ensure_ascii=false, allow_nan=false;
preserve array order and all other keys. Compare SHA256 to
770130a412fd6fab2f02d953edf35f8cc68bf4379db8307e2185937c1e699568.
A well-formed mismatch → UNSUPPORTED; malformed → PARSE_ERROR.
Do not infer compatibility from apiVersion/kind/scope alone.
Output ONLY validated identity, group/kind/plural/scope/version/served and computed
schema hash + compatible boolean. Do not emit raw schema, annotations, conversion
webhooks, CA bundles or unknown CRD content. No installation/change of CRDs.
A match establishes this spec-schema contract only; installed release provenance,
channel, controller support and enforcement remain separate UNKNOWNs.

## CNP semantic projection (F-CNP)

Complete nested schema is normative in followup-typed-contract.json / cnp.spec_schema.
Required tier Admin|Baseline; priority integer 0..1000; subject exactly one namespaces
selector or pods object. NamespacedPod requires podSelector; namespaceSelector optional.
Ingress/egress optional arrays max25. Rule action Accept|Deny|Pass required; name optional
string max100; from/to required arrays 1..25. Preserve rule order.
Ingress peer exactly one namespaces|pods. Egress peer exactly one namespaces|pods|networks.
Networks array 1..25 canonical CIDRs (each max43 chars). Do not invent ingress networks.
Optional protocols array 1..25; each exactly one tcp|udp|sctp; protocol object nonempty;
destinationPort exactly one number(1..65535)|range(start,end 1..65535,start<end).
Subject/peer/selector/protocol unknown keys fail UNSUPPORTED, never silently widen matches.
Empty ingress/egress vs absent have their source semantics; no "healthy/no policies"
claim merely from absent fields. Status is not part of policy execution input here.

## HostEndpoint and Tier

HEP: identity + metadata.labels + validated spec.node/interfaceName/expectedIPs/profiles/ports.
node nonempty max253; interfaceName optional max15; at least one nonempty interfaceName
or expectedIPs. expectedIPs/profiles optional string arrays (set semantics); preserve IP
strings and profile references, do not infer resolved addresses/profile rules.
ports optional array of {name:string,port:integer1..65535,protocol:string|integer},
all three required, per pinned schema. Unknown protocol semantics stay unevaluated.
Missing labels or named ports must not be fabricated from other objects.
Presence does not establish which host policy actually applies.

Tier: identity + labels + spec.order finite number optional + spec.defaultAction
Pass|Deny optional. The pinned schema default is Deny; preserve absence and distinguish
schema-derived default from an observed field. Dropping defaultAction is not allowed.
Ordering/default action alone do not evaluate all tiers/policies.

## Completeness / selectors / excluded reads

For five --raw list reads F-CNP/F-NP/F-GNP/F-HEP/F-TIER propose pages limit=200,
total cap500, at most3 pages. Third page requests remaining100. Build query ONLY from
fixed path plus limit and URL-encoded opaque continue token; never treat token as path.
Require valid list shape, metadata.continue string if present; track resourceVersion
across pages. Nonempty continue at cap, changed resourceVersion, repeated token or
next-page failure => incomplete/PARTIAL, never complete []. Preserve only validated
items, collected count and reason; do not emit the continue token. No retries or mutation.
F-I1 existing kubectl list must expose/inspect metadata.continue; if nonempty, block
identity-dependent reads rather than accepting an incomplete list. No extra Pod read.
Discovery and named reads are not paginated. Future maximum scheduled object/discovery
calls: 9 initial + at most10 list-continuation calls. Version checks need their own Gate.

NetworkSet/GlobalNetworkSet are NOT proven irrelevant to pod flows: selectors can
depend on external address sets. They are excluded from this bounded collection
budget, not declared absent/out-of-scope semantically. Label/profile/selector membership
is NOT evaluated; any unresolved reference keeps EFFECTIVE_POLICY_UNION=UNKNOWN.
HostEndpoint profiles may require further approved evidence; no automatic read.
IPPool/BGP/Calico node/selector-scoped Felix/env/config can affect routing/effective mode.
Excluded here; no inference that their absence from this collector proves irrelevance.
kubecontrollersconfigurations is omitted because no specific versioned fact was identified
that would answer the missing DNAT/Felix question.

API endpoints are node addresses 172.30.140.101/102/103:6443; do not dismiss host policy as
secondary merely because a client uses a Service VIP. DNAT/enforcement remains UNKNOWN.
Default Felix is not effective per-node mode. Barman control/sidecar identity and endpoint
origin are already observed; traffic direction/routing not proven by this collection.
Monitoring/Gateway facts retain original collection timestamps.

Even if every proposed read returns OK, FLOW_MATRIX_COMPLETE and NETPOL_APPROVED_FOR_APPLY
do not change automatically. This plan collects bounded configuration, not a proof of
full policy union or permission to introduce namespace default-deny.

## Implementation handoff (requires accompanying Architect source authorization)

Prepare a NEW followup collector/module, reusing accepted pure projectors and finite
identity gate; do not invoke the old ten-read main() or change its pinned history.
The new script must enforce this read contract and dependencies internally, not rely
on an operator to skip commands. Existing source/tests are preserved except explicit
imports/integration needed for the separate module; no broad Portal/policy refactor.
No live execution until separate review and pinned handoff.

Required offline coverage in one package:
- actual stored three-Pod identity fixture, legacy/new positives and fail-closed negatives;
- discovery scope/kind/verbs + each dependency blocking with zero subprocess calls;
- F-CS exact canonical schema hash match, modified schema mismatch, invalid shape/no raw leak;
- CNP valid selectors/peers/protocols/port ranges and all stated bounds; unknown semantic fields;
- HEP cluster scope, labels/ports/profiles preserved, node/interface conditions;
- Tier defaultAction preserved, invalid enum rejected, absent versus observed value distinguished;
- empty/one-page/201/501/continue error/repeated token/resourceVersion swap/malformed list;
- subprocess timeout/forbidden/not-served/connection/OS error; no overwrite/no kubectl;
- main argv literal assertions, no extra read, no raw/error/annotation/env/credential canary leak.
No regression rerun outside changed collector scope, no accepted PG17/Portal/backup tests.

## Implementation review 4c21b2a — source correction required

Current implementation is NOT accepted for live use. Follow the complete FU-01..08
requirements in docs/architecture/P8C_RV02_REVIEW_4c21b2a_20261028.md.
The review clarifies fixed-context rejection before any output/call, independently
enforced cap500, exact list envelopes/types, honest process outcomes/page journal,
null-versus-absent semantics and per-resource discovery verdicts. Schema annotations
are removed only at schema nodes; semantic properties named description are preserved.
This corrects an ambiguity in the original Architect normalization wording.
No old evidence, accepted identity chain or supplemental source is superseded.
PHASE2_NEW_RUN_APPROVED=NO; NETPOL_APPROVED_FOR_APPLY=NO.
