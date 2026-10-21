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
	envoy := peer{"envoy-gateway-system", map[string]string{"gateway.envoyproxy.io/owning-gateway-name": "portal-gateway", "gateway.envoyproxy.io/owning-gateway-namespace": "portal"}, "10.1.2.1"}
	control := peer{"envoy-gateway-system", map[string]string{"control-plane": "envoy-gateway"}, "10.1.2.2"}
	dns := peer{"kube-system", map[string]string{"k8s-app": "kube-dns"}, "10.1.3.1"}
	operator := peer{"cnpg-system", map[string]string{"app.kubernetes.io/name": "cloudnative-pg"}, "10.1.4.1"}
	other := peer{"other", map[string]string{"app.kubernetes.io/name": "pak-portal"}, "10.1.9.1"}
	wrongOwner := peer{envoy.ns, map[string]string{"gateway.envoyproxy.io/owning-gateway-name": "portal-gateway", "gateway.envoyproxy.io/owning-gateway-namespace": "other"}, envoy.ip}
	tests := []struct {
		name     string
		src, dst peer
		port     int
		protocol string
		want     bool
	}{
		{"app-db", portal, db, 5432, "TCP", true}, {"app-metrics", portal, db, 9187, "TCP", true}, {"migrator-db", migrator, db, 5432, "TCP", true}, {"migrator-no-metrics", migrator, db, 9187, "TCP", false}, {"peer-replication", db, db, 5432, "TCP", true}, {"peer-manager", db, db, 8000, "TCP", true}, {"operator-manager", operator, db, 8000, "TCP", true}, {"gateway-backend", envoy, portal, 8080, "TCP", true}, {"xds", envoy, control, 18000, "TCP", true}, {"dns-udp", portal, dns, 53, "UDP", true}, {"dns-tcp", migrator, dns, 53, "TCP", true}, {"cross-ns-denied", other, db, 5432, "TCP", false}, {"wrong-owner-denied", wrongOwner, portal, 8080, "TCP", false}, {"management-denied", envoy, portal, 8081, "TCP", false}, {"udp-db-denied", portal, db, 5432, "UDP", false}, {"migrator-api-denied", migrator, peer{ip: "172.30.140.100"}, 6443, "TCP", false}, {"app-s3-denied", portal, peer{ip: "172.30.143.10"}, 443, "TCP", false}, {"db-s3", db, peer{ip: "172.30.143.10"}, 443, "TCP", true},
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
