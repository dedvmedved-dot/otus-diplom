package networkpolicy

import (
	appsv1 "k8s.io/api/apps/v1"
	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	netv1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/util/intstr"
	"net"
	"os"
	"sigs.k8s.io/yaml"
	"strconv"
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

type tc struct {
	name     string
	src, dst peer
	port     int
	protocol string
	want     bool
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

	tests := []tc{
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
		// S3
		{"db-s3", db, s3, 443, "TCP", true},
		{"app-s3-denied", portal, s3, 443, "TCP", false},
		{"migrator-s3-denied", migrator, s3, 443, "TCP", false},
		// API positive (four allowed TCP tuples per workload)
		{"cnpg-api-clusterip", db, apiClusterIP, 443, "TCP", true},
		{"cnpg-api-101", db, api101, 6443, "TCP", true},
		{"cnpg-api-102", db, api102, 6443, "TCP", true},
		{"cnpg-api-103", db, api103, 6443, "TCP", true},
		{"portal-api-clusterip", portal, apiClusterIP, 443, "TCP", true},
		{"portal-api-101", portal, api101, 6443, "TCP", true},
		{"portal-api-102", portal, api102, 6443, "TCP", true},
		{"portal-api-103", portal, api103, 6443, "TCP", true},
		// Barman controller -> DB5432 denied
		{"barman-db-denied", barman, db, 5432, "TCP", false},
	}
	// API negative: src={db,portal} x forbidden tuples + UDP on all four allowed tuples
	for _, srcSpec := range []struct {
		prefix string
		p      peer
	}{{"cnpg", db}, {"portal", portal}} {
		src := srcSpec.p
		prefix := srcSpec.prefix
		forbidden := []struct {
			name string
			dst  peer
			port int
		}{
			{"clusterip-6443", apiClusterIP, 6443},
			{"101-443", api101, 443},
			{"102-443", api102, 443},
			{"103-443", api103, 443},
			{"vip-6443", apiVIP, 6443},
			{"104-6443", api104, 6443},
			{"50-6443", api50, 6443},
		}
		for _, f := range forbidden {
			tests = append(tests, tc{prefix + "-api-" + f.name + "-denied", src, f.dst, f.port, "TCP", false})
		}
		for _, dst := range []struct {
			name string
			p    peer
			port int
		}{
			{"clusterip", apiClusterIP, 443},
			{"101", api101, 6443},
			{"102", api102, 6443},
			{"103", api103, 6443},
		} {
			tests = append(tests, tc{prefix + "-api-" + dst.name + "-udp-denied", src, dst.p, dst.port, "UDP", false})
		}
	}
	// migrator reaches none of the four API tuples
	for _, f := range []struct {
		name string
		dst  peer
		port int
	}{
		{"clusterip", apiClusterIP, 443},
		{"101", api101, 6443},
		{"102", api102, 6443},
		{"103", api103, 6443},
	} {
		tests = append(tests, tc{"migrator-api-" + f.name + "-denied", migrator, f.dst, f.port, "TCP", false})
	}
	// dataplane 5-label identity: missing + wrong each label, wrong namespace, 8081
	for _, k := range []string{
		"app.kubernetes.io/component",
		"app.kubernetes.io/managed-by",
		"app.kubernetes.io/name",
		"gateway.envoyproxy.io/owning-gateway-name",
		"gateway.envoyproxy.io/owning-gateway-namespace",
	} {
		tests = append(tests,
			tc{"dataplane-missing-" + k, peer{envoy.ns, withoutLabel(envoyLabels, k), envoy.ip}, portal, 8080, "TCP", false},
			tc{"dataplane-wrong-" + k, peer{envoy.ns, withLabel(envoyLabels, k, "wrong-value"), envoy.ip}, portal, 8080, "TCP", false},
		)
	}
	tests = append(tests, tc{"dataplane-wrong-ns", peer{"other", envoyLabels, envoy.ip}, portal, 8080, "TCP", false})
	// DNS per-workload: correct peer UDP+TCP, wrong-label and wrong-ns both UDP and TCP
	for _, wl := range []struct {
		name string
		p    peer
	}{
		{"cnpg", db}, {"portal", portal}, {"migrator", migrator}, {"dataplane", envoy},
	} {
		tests = append(tests,
			tc{"dns-" + wl.name + "-udp", wl.p, dns, 53, "UDP", true},
			tc{"dns-" + wl.name + "-tcp", wl.p, dns, 53, "TCP", true},
			tc{"dns-" + wl.name + "-wrong-label-udp", wl.p, dnsWrongLabel, 53, "UDP", false},
			tc{"dns-" + wl.name + "-wrong-label-tcp", wl.p, dnsWrongLabel, 53, "TCP", false},
			tc{"dns-" + wl.name + "-wrong-ns-udp", wl.p, dnsWrongNS, 53, "UDP", false},
			tc{"dns-" + wl.name + "-wrong-ns-tcp", wl.p, dnsWrongNS, 53, "TCP", false},
		)
	}
	for _, x := range tests {
		t.Run(x.name, func(t *testing.T) {
			if got := allowed(policies, x.src, x.dst, x.port, x.protocol); got != x.want {
				t.Fatalf("allow=%v want %v", got, x.want)
			}
		})
	}

	// Mutation regression: widening the DNS peer (drop podSelector on namespace-scoped peers)
	// must make the previously-denied bad-DNS peer allowed.
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

	// S1 / S2a / S2b individually preserve the necessary CNPG flows (now incl. DNS TCP + 3 endpoints).
	s1 := subset(policies, "p8c-cnpg-existing-flows")
	s2a := subset(policies, "p8c-cnpg-existing-flows", "baseline-default-deny-all")
	s2b := subset(policies, "p8c-cnpg-existing-flows", "baseline-default-deny-all", "baseline-allow-dns-egress")
	cnpgFlows := []tc{
		{"peer-replication", db, db, 5432, "TCP", true},
		{"peer-manager", db, db, 8000, "TCP", true},
		{"operator-manager", operator, db, 8000, "TCP", true},
		{"cnpg-s3", db, s3, 443, "TCP", true},
		{"cnpg-api-clusterip", db, apiClusterIP, 443, "TCP", true},
		{"cnpg-api-101", db, api101, 6443, "TCP", true},
		{"cnpg-api-102", db, api102, 6443, "TCP", true},
		{"cnpg-api-103", db, api103, 6443, "TCP", true},
		{"cnpg-dns-udp", db, dns, 53, "UDP", true},
		{"cnpg-dns-tcp", db, dns, 53, "TCP", true},
	}
	for _, stage := range []struct {
		name string
		ps   []netv1.NetworkPolicy
	}{{"S1", s1}, {"S2a", s2a}, {"S2b", s2b}} {
		for _, f := range cnpgFlows {
			if !allowed(stage.ps, f.src, f.dst, f.port, f.protocol) {
				t.Fatalf("%s must preserve %s", stage.name, f.name)
			}
		}
	}

	// Removal of existing-flows while baseline-default-deny (+allow-dns) remains must NOT restore S0.
	denyOnly := subset(policies, "baseline-default-deny-all", "baseline-allow-dns-egress")
	if !allowed(denyOnly, db, dns, 53, "UDP") {
		t.Fatal("baseline-allow-dns-egress must still allow DNS for CNPG")
	}
	if allowed(denyOnly, db, s3, 443, "TCP") {
		t.Fatal("deny-only must not restore S0 S3 egress")
	}
	if allowed(denyOnly, db, apiClusterIP, 443, "TCP") {
		t.Fatal("deny-only must not restore S0 API egress")
	}
	if allowed(denyOnly, db, db, 5432, "TCP") {
		t.Fatal("deny-only must not allow peer replication")
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

// validateStructure returns all structural/semantic violations of the candidate YAML.
func validateStructure(policies []netv1.NetworkPolicy) []string {
	var errs []string
	want := map[string]string{
		"p8c-cnpg-existing-flows":    "portal",
		"baseline-default-deny-all":  "portal",
		"baseline-allow-dns-egress":  "portal",
		"p8c-portal-flows":           "portal",
		"p8c-migrator-flows":         "portal",
		"p8c-portal-dataplane-flows": "envoy-gateway-system",
	}
	if len(policies) != 6 {
		errs = append(errs, "want 6 objects")
	}
	seen := map[string]bool{}
	// exact allowed ipBlock egress tuples (CIDR -> allowed ports+proto)
	allowedIP := map[string]map[string]bool{
		"10.96.0.1/32":       {"443/TCP": true},
		"172.30.140.101/32":  {"6443/TCP": true},
		"172.30.140.102/32":  {"6443/TCP": true},
		"172.30.140.103/32":  {"6443/TCP": true},
		"172.30.143.10/32":   {"443/TCP": true},
	}
	for _, p := range policies {
		if p.APIVersion != "networking.k8s.io/v1" || p.Kind != "NetworkPolicy" {
			errs = append(errs, p.Name+": apiVersion/kind mismatch")
		}
		ns, ok := want[p.Name]
		if !ok {
			errs = append(errs, "unexpected policy "+p.Name)
			continue
		}
		if p.Namespace != ns {
			errs = append(errs, p.Name+": namespace "+p.Namespace+" want "+ns)
		}
		seen[p.Name] = true
		// exact type-set without duplicates, matched to expected set
		wantTypes := map[string]map[netv1.PolicyType]bool{
			"p8c-cnpg-existing-flows":    {netv1.PolicyTypeIngress: true, netv1.PolicyTypeEgress: true},
			"baseline-default-deny-all":  {netv1.PolicyTypeIngress: true, netv1.PolicyTypeEgress: true},
			"baseline-allow-dns-egress":  {netv1.PolicyTypeEgress: true},
			"p8c-portal-flows":           {netv1.PolicyTypeIngress: true, netv1.PolicyTypeEgress: true},
			"p8c-migrator-flows":         {netv1.PolicyTypeEgress: true},
			"p8c-portal-dataplane-flows": {netv1.PolicyTypeEgress: true},
		}
		types := map[netv1.PolicyType]bool{}
		for _, typ := range p.Spec.PolicyTypes {
			if types[typ] {
				errs = append(errs, p.Name+": duplicate policyType "+string(typ))
			}
			types[typ] = true
		}
		exp := wantTypes[p.Name]
		if len(types) != len(exp) {
			errs = append(errs, p.Name+": policyType set mismatch")
		} else {
			for typ := range exp {
				if !types[typ] {
					errs = append(errs, p.Name+": missing policyType "+string(typ))
				}
			}
		}
		// check egress/ingress rules
		for _, egr := range p.Spec.Egress {
			if len(egr.To) == 0 {
				errs = append(errs, p.Name+": unrestricted egress (empty to)")
			}
			if len(egr.Ports) == 0 {
				errs = append(errs, p.Name+": egress rule with empty ports")
			}
			for _, port := range egr.Ports {
				if port.EndPort != nil {
					errs = append(errs, p.Name+": endPort unsupported")
				}
				if port.Port == nil {
					errs = append(errs, p.Name+": port=nil unsupported")
				}
				if port.Port != nil && port.Port.Type != 0 {
					errs = append(errs, p.Name+": named port unsupported")
				}
			}
			for _, to := range egr.To {
				if to.IPBlock != nil {
					cidr := to.IPBlock.CIDR
					if cidr == "" || !strings.HasSuffix(cidr, "/32") {
						errs = append(errs, p.Name+": broad IPBlock "+cidr)
						continue
					}
					ports, ok := allowedIP[cidr]
					if !ok {
						errs = append(errs, p.Name+": unexpected IPBlock "+cidr)
						continue
					}
					for _, port := range egr.Ports {
						if port.Port == nil || port.Port.Type != 0 {
							continue
						}
						proto := "TCP"
						if port.Protocol != nil {
							proto = string(*port.Protocol)
						}
						key := strconv.Itoa(int(port.Port.IntVal)) + "/" + proto
						if !ports[key] {
							errs = append(errs, p.Name+": unexpected tuple "+cidr+":"+key)
						}
					}
				}
				if to.PodSelector != nil || to.NamespaceSelector != nil {
					if (to.NamespaceSelector != nil && len(to.NamespaceSelector.MatchLabels) == 0 && len(to.NamespaceSelector.MatchExpressions) == 0) &&
						to.PodSelector == nil {
						errs = append(errs, p.Name+": empty namespaceSelector peer")
					}
				} else if to.IPBlock == nil {
					errs = append(errs, p.Name+": empty peer {}")
				}
			}
		}
		for _, ing := range p.Spec.Ingress {
			if len(ing.From) == 0 {
				errs = append(errs, p.Name+": unrestricted ingress (empty from)")
			}
		}
	}
	for name := range want {
		if !seen[name] {
			errs = append(errs, "missing policy "+name)
		}
	}
	return errs
}

func TestCandidatePolicyStructure(t *testing.T) {
	policies := loadPolicies(t)
	if errs := validateStructure(policies); len(errs) > 0 {
		t.Fatalf("candidate violates structure: %v", errs)
	}
}

func TestCandidatePolicyStructureRejectsMutations(t *testing.T) {
	mutate := func(fn func(*netv1.NetworkPolicy)) []netv1.NetworkPolicy {
		ps := loadPolicies(t)
		for i := range ps {
			fn(&ps[i])
		}
		return ps
	}
	cases := []struct {
		name string
		fn   func(*netv1.NetworkPolicy)
	}{
		{"extra-udp", func(p *netv1.NetworkPolicy) {
			if p.Name == "p8c-cnpg-existing-flows" {
				p.Spec.Egress = append(p.Spec.Egress, netv1.NetworkPolicyEgressRule{
					Ports: []netv1.NetworkPolicyPort{{Protocol: protoPtr(corev1.ProtocolUDP), Port: portPtr(9999)}},
					To:    []netv1.NetworkPolicyPeer{{IPBlock: &netv1.IPBlock{CIDR: "172.30.140.101/32"}}},
				})
			}
		}},
		{"sctp-rule", func(p *netv1.NetworkPolicy) {
			if p.Name == "p8c-portal-flows" {
				p.Spec.Egress = append(p.Spec.Egress, netv1.NetworkPolicyEgressRule{
					Ports: []netv1.NetworkPolicyPort{{Protocol: protoPtr(corev1.ProtocolSCTP), Port: portPtr(9999)}},
					To:    []netv1.NetworkPolicyPeer{{IPBlock: &netv1.IPBlock{CIDR: "10.96.0.1/32"}}},
				})
			}
		}},
		{"empty-peer", func(p *netv1.NetworkPolicy) {
			if p.Name == "p8c-cnpg-existing-flows" {
				p.Spec.Egress = append(p.Spec.Egress, netv1.NetworkPolicyEgressRule{
					To: []netv1.NetworkPolicyPeer{{}},
				})
			}
		}},
		{"removed-egress-type", func(p *netv1.NetworkPolicy) {
			if p.Name == "p8c-cnpg-existing-flows" {
				p.Spec.PolicyTypes = []netv1.PolicyType{netv1.PolicyTypeIngress}
			}
		}},
		{"unset-6443", func(p *netv1.NetworkPolicy) {
			if p.Name == "p8c-cnpg-existing-flows" {
				for i := range p.Spec.Egress {
					for j := range p.Spec.Egress[i].To {
						if p.Spec.Egress[i].To[j].IPBlock != nil && p.Spec.Egress[i].To[j].IPBlock.CIDR == "172.30.140.101/32" {
							p.Spec.Egress[i].To[j].IPBlock = nil
						}
					}
				}
			}
		}},
		{"endport", func(p *netv1.NetworkPolicy) {
			if p.Name == "p8c-cnpg-existing-flows" {
				for i := range p.Spec.Egress {
					for j := range p.Spec.Egress[i].Ports {
						p.Spec.Egress[i].Ports[j].EndPort = int32Ptr(6500)
					}
				}
			}
		}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if errs := validateStructure(mutate(c.fn)); len(errs) == 0 {
				t.Fatalf("mutated %s should be rejected", c.name)
			}
		})
	}
}

func protoPtr(p corev1.Protocol) *corev1.Protocol { return &p }
func portPtr(v int) *intstr.IntOrString          { x := intstr.FromInt(v); return &x }
func int32Ptr(v int) *int32                      { x := int32(v); return &x }
