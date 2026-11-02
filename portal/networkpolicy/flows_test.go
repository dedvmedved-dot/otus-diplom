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

func loadPolicies(t *testing.T) []netv1.NetworkPolicy {
	t.Helper()
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
	return policies
}

func subset(policies []netv1.NetworkPolicy, names ...string) []netv1.NetworkPolicy {
	want := map[string]bool{}
	for _, n := range names {
		want[n] = true
	}
	out := []netv1.NetworkPolicy{}
	for _, p := range policies {
		if want[p.Name] {
			out = append(out, p)
		}
	}
	return out
}

func TestCandidatePolicyUnionBothSides(t *testing.T) {
	policies := loadPolicies(t)
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
	dnsWrongLabel := peer{"kube-system", map[string]string{"k8s-app": "other"}, "10.1.3.2"}
	dnsWrongNS := peer{"other", map[string]string{"k8s-app": "kube-dns"}, "10.1.3.3"}
	operator := peer{"cnpg-system", map[string]string{"app.kubernetes.io/name": "cloudnative-pg"}, "10.1.4.1"}
	barman := peer{"cnpg-system", map[string]string{"app": "barman-cloud"}, "10.1.4.2"}
	other := peer{"other", map[string]string{"app.kubernetes.io/name": "pak-portal"}, "10.1.9.1"}
	apiClusterIP := peer{ip: "10.96.0.1"}
	api101 := peer{ip: "172.30.140.101"}
	api102 := peer{ip: "172.30.140.102"}
	api103 := peer{ip: "172.30.140.103"}
	apiVIP := peer{ip: "172.30.140.100"}
	api104 := peer{ip: "172.30.140.104"}
	api50 := peer{ip: "172.30.140.50"}
	s3 := peer{ip: "172.30.143.10"}

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
		{"cross-ns-denied", other, db, 5432, "TCP", false},
		{"management-denied", envoy, portal, 8081, "TCP", false},
		{"udp-db-denied", portal, db, 5432, "UDP", false},
		// S3 (NP-02 sidecar preserved; Portal/migrator denied)
		{"db-s3", db, s3, 443, "TCP", true},
		{"app-s3-denied", portal, s3, 443, "TCP", false},
		{"migrator-s3-denied", migrator, s3, 443, "TCP", false},
		// API tuples (NP-01): four allowed for CNPG + Portal
		{"cnpg-api-clusterip", db, apiClusterIP, 443, "TCP", true},
		{"cnpg-api-101", db, api101, 6443, "TCP", true},
		{"cnpg-api-102", db, api102, 6443, "TCP", true},
		{"cnpg-api-103", db, api103, 6443, "TCP", true},
		{"portal-api-clusterip", portal, apiClusterIP, 443, "TCP", true},
		{"portal-api-101", portal, api101, 6443, "TCP", true},
		{"portal-api-102", portal, api102, 6443, "TCP", true},
		{"portal-api-103", portal, api103, 6443, "TCP", true},
		// API cross-product / non-tuple denied (no cartesian product)
		{"api-clusterip-6443-denied", db, apiClusterIP, 6443, "TCP", false},
		{"api-101-443-denied", db, api101, 443, "TCP", false},
		{"api-102-443-denied", db, api102, 443, "TCP", false},
		{"api-103-443-denied", db, api103, 443, "TCP", false},
		{"api-vip-denied", db, apiVIP, 6443, "TCP", false},
		{"api-104-denied", db, api104, 6443, "TCP", false},
		{"api-50-denied", db, api50, 6443, "TCP", false},
		{"api-udp-denied", db, apiClusterIP, 443, "UDP", false},
		// Barman controller -> DB5432 denied (NP-02)
		{"barman-db-denied", barman, db, 5432, "TCP", false},
	}
	// migrator reaches none of the four API tuples
	for _, tc := range []struct {
		name string
		dst  peer
		port int
	}{
		{"migrator-api-clusterip-denied", apiClusterIP, 443},
		{"migrator-api-101-denied", api101, 6443},
		{"migrator-api-102-denied", api102, 6443},
		{"migrator-api-103-denied", api103, 6443},
	} {
		tests = append(tests, struct {
			name     string
			src, dst peer
			port     int
			protocol string
			want     bool
		}{tc.name, migrator, tc.dst, tc.port, "TCP", false})
	}
	// dataplane 5-label identity: each label missing/wrong, wrong namespace, mgmt 8081
	labelKeys := []string{
		"app.kubernetes.io/component",
		"app.kubernetes.io/managed-by",
		"app.kubernetes.io/name",
		"gateway.envoyproxy.io/owning-gateway-name",
		"gateway.envoyproxy.io/owning-gateway-namespace",
	}
	for _, k := range labelKeys {
		tests = append(tests, struct {
			name     string
			src, dst peer
			port     int
			protocol string
			want     bool
		}{"dataplane-missing-" + k, peer{envoy.ns, withoutLabel(envoyLabels, k), envoy.ip}, portal, 8080, "TCP", false})
		tests = append(tests, struct {
			name     string
			src, dst peer
			port     int
			protocol string
			want     bool
		}{"dataplane-wrong-" + k, peer{envoy.ns, withLabel(envoyLabels, k, "wrong-value"), envoy.ip}, portal, 8080, "TCP", false})
	}
	tests = append(tests, struct {
		name     string
		src, dst peer
		port     int
		protocol string
		want     bool
	}{"dataplane-wrong-ns", peer{"other", envoyLabels, envoy.ip}, portal, 8080, "TCP", false})
	// DNS per-workload (correct peer UDP/TCP + two wrong peers)
	for _, wl := range []struct {
		name string
		p    peer
	}{
		{"cnpg", db}, {"portal", portal}, {"migrator", migrator}, {"dataplane", envoy},
	} {
		tests = append(tests,
			struct {
				name     string
				src, dst peer
				port     int
				protocol string
				want     bool
			}{"dns-" + wl.name + "-udp", wl.p, dns, 53, "UDP", true},
			struct {
				name     string
				src, dst peer
				port     int
				protocol string
				want     bool
			}{"dns-" + wl.name + "-tcp", wl.p, dns, 53, "TCP", true},
			struct {
				name     string
				src, dst peer
				port     int
				protocol string
				want     bool
			}{"dns-" + wl.name + "-wrong-label", wl.p, dnsWrongLabel, 53, "UDP", false},
			struct {
				name     string
				src, dst peer
				port     int
				protocol string
				want     bool
			}{"dns-" + wl.name + "-wrong-ns", wl.p, dnsWrongNS, 53, "UDP", false},
		)
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got := allowed(policies, tc.src, tc.dst, tc.port, tc.protocol); got != tc.want {
				t.Fatalf("allow=%v want %v", got, tc.want)
			}
		})
	}

	// Mutation regression: widening the DNS peer (drop podSelector) must make the
	// previously-denied bad-DNS peer allowed — proving the negative test is sensitive.
	widened := loadPolicies(t)
	for i := range widened {
		for j := range widened[i].Spec.Egress {
			for k := range widened[i].Spec.Egress[j].To {
				if widened[i].Spec.Egress[j].To[k].NamespaceSelector != nil {
					widened[i].Spec.Egress[j].To[k].PodSelector = nil
				}
			}
		}
	}
	if !allowed(widened, portal, dnsWrongLabel, 53, "UDP") {
		t.Fatal("mutation regression: widened DNS peer should be allowed (negative test would miss expansion)")
	}
	if allowed(policies, portal, dnsWrongLabel, 53, "UDP") {
		t.Fatal("unwidened candidate must still deny bad-DNS peer")
	}

	// Omitting the destination's ingress allowance MUST fail despite client egress.
	reduced := subset(policies, "baseline-default-deny-all", "baseline-allow-dns-egress",
		"p8c-portal-flows", "p8c-migrator-flows", "p8c-portal-dataplane-flows")
	if allowed(reduced, portal, db, 5432, "TCP") {
		t.Fatal("egress alone incorrectly allowed DB ingress")
	}

	// S1 / S2a / S2b individually preserve the necessary CNPG flows.
	s1 := subset(policies, "p8c-cnpg-existing-flows")
	s2a := subset(policies, "p8c-cnpg-existing-flows", "baseline-default-deny-all")
	s2b := subset(policies, "p8c-cnpg-existing-flows", "baseline-default-deny-all", "baseline-allow-dns-egress")
	cnpgFlows := []struct {
		name string
		src  peer
		dst  peer
		port int
		prot string
	}{
		{"peer-replication", db, db, 5432, "TCP"},
		{"peer-manager", db, db, 8000, "TCP"},
		{"operator-manager", operator, db, 8000, "TCP"},
		{"cnpg-s3", db, s3, 443, "TCP"},
		{"cnpg-api-clusterip", db, apiClusterIP, 443, "TCP"},
		{"cnpg-dns", db, dns, 53, "UDP"},
	}
	for _, stage := range []struct {
		name string
		ps   []netv1.NetworkPolicy
	}{{"S1", s1}, {"S2a", s2a}, {"S2b", s2b}} {
		for _, f := range cnpgFlows {
			if !allowed(stage.ps, f.src, f.dst, f.port, f.prot) {
				t.Fatalf("%s must preserve %s", stage.name, f.name)
			}
		}
	}

	// Removal of existing-flows while baseline-default-deny (+allow-dns) remains must NOT
	// restore S0: CNPG loses S3/API/peer egress; only the explicit DNS allowance survives.
	denyOnly := subset(policies, "baseline-default-deny-all", "baseline-allow-dns-egress")
	if !allowed(denyOnly, db, dns, 53, "UDP") {
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

	// Workload labels match candidate policy selectors.
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

func TestCandidatePolicyStructure(t *testing.T) {
	policies := loadPolicies(t)
	want := map[string]string{
		"p8c-cnpg-existing-flows":     "portal",
		"baseline-default-deny-all":   "portal",
		"baseline-allow-dns-egress":   "portal",
		"p8c-portal-flows":            "portal",
		"p8c-migrator-flows":          "portal",
		"p8c-portal-dataplane-flows":  "envoy-gateway-system",
	}
	if len(policies) != 6 {
		t.Fatalf("want 6 objects, got %d", len(policies))
	}
	seen := map[string]bool{}
	for _, p := range policies {
		ns, ok := want[p.Name]
		if !ok {
			t.Fatalf("unexpected policy name %q", p.Name)
		}
		if p.Namespace != ns {
			t.Fatalf("%s: namespace %q want %q", p.Name, p.Namespace, ns)
		}
		seen[p.Name] = true
		// no broad CIDR (only /32) and no unrestricted peer (empty To/From) anywhere
		for _, egr := range p.Spec.Egress {
			if len(egr.To) == 0 {
				t.Fatalf("%s: unrestricted egress rule (empty to)", p.Name)
			}
			for _, to := range egr.To {
				if to.IPBlock != nil {
					if to.IPBlock.CIDR == "" || !strings.HasSuffix(to.IPBlock.CIDR, "/32") {
						t.Fatalf("%s: broad IPBlock CIDR %q (only /32 allowed)", p.Name, to.IPBlock.CIDR)
					}
				}
			}
		}
		for _, ing := range p.Spec.Ingress {
			if len(ing.From) == 0 {
				t.Fatalf("%s: unrestricted ingress rule (empty from)", p.Name)
			}
		}
	}
	for name := range want {
		if !seen[name] {
			t.Fatalf("missing policy %q", name)
		}
	}
	// policyTypes spot checks
	byName := map[string]netv1.NetworkPolicy{}
	for _, p := range policies {
		byName[p.Name] = p
	}
	hasType := func(name string, t netv1.PolicyType) bool {
		for _, x := range byName[name].Spec.PolicyTypes {
			if x == t {
				return true
			}
		}
		return false
	}
	if !hasType("p8c-cnpg-existing-flows", netv1.PolicyTypeIngress) || !hasType("p8c-cnpg-existing-flows", netv1.PolicyTypeEgress) {
		t.Fatal("existing-flows must be Ingress+Egress")
	}
	if hasType("p8c-migrator-flows", netv1.PolicyTypeIngress) {
		t.Fatal("migrator must be Egress-only")
	}
	if hasType("p8c-portal-dataplane-flows", netv1.PolicyTypeIngress) {
		t.Fatal("dataplane must be Egress-only")
	}
}
