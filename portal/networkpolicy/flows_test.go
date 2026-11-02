package networkpolicy

import (
	appsv1 "k8s.io/api/apps/v1"
	batchv1 "k8s.io/api/batch/v1"
	netv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"net"
	"os"
	"sigs.k8s.io/yaml"
	"strings"
	"testing"
)

type peer struct {
	ns     string
	labels map[string]string
	ip     string
}

func matches(sel metav1.LabelSelector, values map[string]string) bool {
	s, e := metav1.LabelSelectorAsSelector(&sel)
	return e == nil && s.Matches(labels.Set(values))
}
func matchPeer(rule netv1.NetworkPolicyPeer, other peer, policyNS string) bool {
	if rule.IPBlock != nil {
		_, cidr, e := net.ParseCIDR(rule.IPBlock.CIDR)
		if e != nil || !cidr.Contains(net.ParseIP(other.ip)) {
			return false
		}
		for _, exclude := range rule.IPBlock.Except {
			_, block, _ := net.ParseCIDR(exclude)
			if block.Contains(net.ParseIP(other.ip)) {
				return false
			}
		}
		return true
	}
	if rule.NamespaceSelector != nil {
		if !matches(*rule.NamespaceSelector, map[string]string{"kubernetes.io/metadata.name": other.ns}) {
			return false
		}
	} else if other.ns != policyNS {
		return false
	}
	return rule.PodSelector == nil || matches(*rule.PodSelector, other.labels)
}
func portsAllow(ports []netv1.NetworkPolicyPort, port int, protocol string) bool {
	if len(ports) == 0 {
		return true
	}
	for _, p := range ports {
		proto := "TCP"
		if p.Protocol != nil {
			proto = string(*p.Protocol)
		}
		if proto != protocol {
			continue
		}
		if p.Port == nil {
			return true
		}
		if p.Port.Type != 0 {
			panic("named ports need explicit evaluator support")
		}
		if int(p.Port.IntVal) == port {
			return true
		}
	}
	return false
}
func allowed(policies []netv1.NetworkPolicy, src, dst peer, port int, protocol string) bool {
	for _, direction := range []netv1.PolicyType{netv1.PolicyTypeEgress, netv1.PolicyTypeIngress} {
		selected, permit := false, false
		target, other := src, dst
		if direction == netv1.PolicyTypeIngress {
			target, other = dst, src
		}
		for _, policy := range policies {
			if policy.Namespace != target.ns || !matches(policy.Spec.PodSelector, target.labels) {
				continue
			}
			active := false
			for _, typ := range policy.Spec.PolicyTypes {
				if typ == direction {
					active = true
				}
			}
			if !active {
				continue
			}
			selected = true
			if direction == netv1.PolicyTypeIngress {
				for _, rule := range policy.Spec.Ingress {
					if !portsAllow(rule.Ports, port, protocol) {
						continue
					}
					if len(rule.From) == 0 {
						permit = true
					}
					for _, from := range rule.From {
						if matchPeer(from, other, policy.Namespace) {
							permit = true
						}
					}
				}
			} else {
				for _, rule := range policy.Spec.Egress {
					if !portsAllow(rule.Ports, port, protocol) {
						continue
					}
					if len(rule.To) == 0 {
						permit = true
					}
					for _, to := range rule.To {
						if matchPeer(to, other, policy.Namespace) {
							permit = true
						}
					}
				}
			}
		}
		if selected && !permit {
			return false
		}
	}
	return true
}
func withLabel(m map[string]string, k, v string) map[string]string {
	out := map[string]string{}
	for kk, vv := range m {
		out[kk] = vv
	}
	out[k] = v
	return out
}
func withoutLabel(m map[string]string, k string) map[string]string {
	out := map[string]string{}
	for kk, vv := range m {
		if kk != k {
			out[kk] = vv
		}
	}
	return out
}
func TestCandidatePolicyUnionBothSides(t *testing.T) {
	data, e := os.ReadFile("../manifests/networkpolicy.yaml")
	if e != nil {
		t.Fatal(e)
	}
	policies := []netv1.NetworkPolicy{}
	for _, doc := range strings.Split(string(data), "\n---") {
		var p netv1.NetworkPolicy
		if e := yaml.UnmarshalStrict([]byte(doc), &p); e != nil {
			t.Fatal(e)
		}
		if p.Kind != "" {
			policies = append(policies, p)
		}
	}
	portal := peer{"portal", map[string]string{"app.kubernetes.io/name": "pak-portal"}, "10.1.1.1"}
	migrator := peer{"portal", map[string]string{"app.kubernetes.io/name": "pak-portal-migrator"}, "10.1.1.2"}
	db := peer{"portal", map[string]string{"cnpg.io/cluster": "portal-db", "cnpg.io/podRole": "instance"}, "10.1.1.3"}
	envoyLabels := map[string]string{
		"app.kubernetes.io/component":                    "proxy",
		"app.kubernetes.io/managed-by":                   "envoy-gateway",
		"app.kubernetes.io/name":                         "envoy",
		"gateway.envoyproxy.io/owning-gateway-name":      "portal-gateway",
		"gateway.envoyproxy.io/owning-gateway-namespace": "portal",
	}
	envoy := peer{"envoy-gateway-system", envoyLabels, "10.1.2.1"}
	control := peer{"envoy-gateway-system", map[string]string{"control-plane": "envoy-gateway"}, "10.1.2.2"}
	dns := peer{"kube-system", map[string]string{"k8s-app": "kube-dns"}, "10.1.3.1"}
	operator := peer{"cnpg-system", map[string]string{"app.kubernetes.io/name": "cloudnative-pg"}, "10.1.4.1"}
	barman := peer{"cnpg-system", map[string]string{"app": "barman-cloud"}, "10.1.4.2"}
	other := peer{"other", map[string]string{"app.kubernetes.io/name": "pak-portal"}, "10.1.9.1"}
	apiClusterIP := peer{ip: "10.96.0.1"}
	api101 := peer{ip: "172.30.140.101"}
	api102 := peer{ip: "172.30.140.102"}
	api103 := peer{ip: "172.30.140.103"}
	apiVIP := peer{ip: "172.30.140.100"}
	api104 := peer{ip: "172.30.140.104"}
	s3 := peer{ip: "172.30.143.10"}
	envoyWrongOwnerName := peer{envoy.ns, withLabel(envoyLabels, "gateway.envoyproxy.io/owning-gateway-name", "other-gateway"), envoy.ip}
	envoyWrongOwnerNS := peer{envoy.ns, withLabel(envoyLabels, "gateway.envoyproxy.io/owning-gateway-namespace", "other"), envoy.ip}
	envoyNoComponent := peer{envoy.ns, withoutLabel(envoyLabels, "app.kubernetes.io/component"), envoy.ip}
	envoyWrongNS := peer{"other", envoyLabels, envoy.ip}
	tests := []struct {
		name     string
		src, dst peer
		port     int
		protocol string
		want     bool
	}{
		// existing flows (NP-04 preserved)
		{"app-db", portal, db, 5432, "TCP", true},
		{"app-metrics", portal, db, 9187, "TCP", true},
		{"migrator-db", migrator, db, 5432, "TCP", true},
		{"migrator-no-metrics", migrator, db, 9187, "TCP", false},
		{"peer-replication", db, db, 5432, "TCP", true},
		{"peer-manager", db, db, 8000, "TCP", true},
		{"operator-manager", operator, db, 8000, "TCP", true},
		{"gateway-backend", envoy, portal, 8080, "TCP", true},
		{"xds", envoy, control, 18000, "TCP", true},
		{"dns-udp", portal, dns, 53, "UDP", true},
		{"dns-tcp", migrator, dns, 53, "TCP", true},
		{"cross-ns-denied", other, db, 5432, "TCP", false},
		{"management-denied", envoy, portal, 8081, "TCP", false},
		{"udp-db-denied", portal, db, 5432, "UDP", false},
		// S3 (NP-02 sidecar preserved; Portal/migrator denied)
		{"db-s3", db, s3, 443, "TCP", true},
		{"app-s3-denied", portal, s3, 443, "TCP", false},
		{"migrator-s3-denied", migrator, s3, 443, "TCP", false},
		// API tuples (NP-01): four allowed
		{"cnpg-api-clusterip", db, apiClusterIP, 443, "TCP", true},
		{"cnpg-api-101", db, api101, 6443, "TCP", true},
		{"cnpg-api-102", db, api102, 6443, "TCP", true},
		{"cnpg-api-103", db, api103, 6443, "TCP", true},
		{"portal-api-clusterip", portal, apiClusterIP, 443, "TCP", true},
		{"portal-api-101", portal, api101, 6443, "TCP", true},
		// API cross-product / non-tuple denied (no cartesian product)
		{"api-clusterip-6443-denied", db, apiClusterIP, 6443, "TCP", false},
		{"api-101-443-denied", db, api101, 443, "TCP", false},
		{"api-102-443-denied", db, api102, 443, "TCP", false},
		{"api-vip-denied", db, apiVIP, 6443, "TCP", false},
		{"api-104-denied", db, api104, 6443, "TCP", false},
		{"api-udp-denied", db, apiClusterIP, 443, "UDP", false},
		{"migrator-api-clusterip-denied", migrator, apiClusterIP, 443, "TCP", false},
		{"migrator-api-101-denied", migrator, api101, 6443, "TCP", false},
		// Barman controller -> DB5432 denied (NP-02)
		{"barman-db-denied", barman, db, 5432, "TCP", false},
		// dataplane 5-label identity (NP-03)
		{"dataplane-wrong-owner-name", envoyWrongOwnerName, portal, 8080, "TCP", false},
		{"dataplane-wrong-owner-ns", envoyWrongOwnerNS, portal, 8080, "TCP", false},
		{"dataplane-missing-component", envoyNoComponent, portal, 8080, "TCP", false},
		{"dataplane-wrong-ns", envoyWrongNS, portal, 8080, "TCP", false},
		// DNS peer precision (namespace AND pod label)
		{"dns-wrong-label-kubesystem", peer{"kube-system", map[string]string{"k8s-app": "other"}, "10.1.3.2"}, portal, 53, "UDP", false},
		{"dns-correct-label-wrong-ns", peer{"other", map[string]string{"k8s-app": "kube-dns"}, "10.1.3.3"}, portal, 53, "UDP", false},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got := allowed(policies, tc.src, tc.dst, tc.port, tc.protocol); got != tc.want {
				t.Fatalf("allow=%v want %v", got, tc.want)
			}
		})
	}
	// Omitting the destination's ingress allowance MUST fail despite client egress.
	reduced := []netv1.NetworkPolicy{}
	for _, p := range policies {
		if p.Name != "p8c-cnpg-existing-flows" {
			reduced = append(reduced, p)
		}
	}
	if allowed(reduced, portal, db, 5432, "TCP") {
		t.Fatal("egress alone incorrectly allowed DB ingress")
	}
	// Removal of existing-flows while baseline-default-deny (+allow-dns) remains must NOT
	// restore S0: CNPG loses S3/API/peer egress; only the explicit DNS allowance survives.
	denyOnly := []netv1.NetworkPolicy{}
	for _, p := range policies {
		if p.Name == "baseline-default-deny-all" || p.Name == "baseline-allow-dns-egress" {
			denyOnly = append(denyOnly, p)
		}
	}
	if allowed(denyOnly, db, dns, 53, "UDP") == false {
		t.Fatal("baseline-allow-dns-egress must still allow DNS for CNPG")
	}
	if allowed(denyOnly, db, s3, 443, "TCP") {
		t.Fatal("removing existing-flows while default-deny remains must not restore S0 S3 egress")
	}
	if allowed(denyOnly, db, apiClusterIP, 443, "TCP") {
		t.Fatal("removing existing-flows while default-deny remains must not restore S0 API egress")
	}
	if allowed(denyOnly, db, db, 5432, "TCP") {
		t.Fatal("removing existing-flows while default-deny remains must not allow peer replication")
	}
	deployments, e := os.ReadFile("../manifests/deployment.yaml")
	if e != nil {
		t.Fatal(e)
	}
	found := map[string]bool{}
	for _, doc := range strings.Split(string(deployments), "\n---") {
		var meta struct{ Kind string }
		yaml.Unmarshal([]byte(doc), &meta)
		switch meta.Kind {
		case "Deployment":
			var d appsv1.Deployment
			yaml.Unmarshal([]byte(doc), &d)
			if d.Spec.Template.Labels["app.kubernetes.io/name"] == "pak-portal" {
				found["app"] = true
			}
		case "Job":
			var j batchv1.Job
			yaml.Unmarshal([]byte(doc), &j)
			if j.Spec.Template.Labels["app.kubernetes.io/name"] == "pak-portal-migrator" {
				found["migrator"] = true
			}
		}
	}
	if !found["app"] || !found["migrator"] {
		t.Fatal("candidate workload labels do not match policies")
	}
}
