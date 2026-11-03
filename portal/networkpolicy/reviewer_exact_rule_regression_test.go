package networkpolicy

import (
 "testing"
 corev1 "k8s.io/api/core/v1"
 netv1 "k8s.io/api/networking/v1"
 metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
 "k8s.io/apimachinery/pkg/util/intstr"
)

// Reviewer source regression; NOT executed in the Architect environment (Go unavailable).
// Copy into portal/networkpolicy as *_test.go; run with the existing suite.
func TestReviewerExactRuleContract(t *testing.T) {
 tests := []struct{name, policy string; mutate func(*netv1.NetworkPolicy)}{
  {"ingress-extra-tcp9999","p8c-portal-flows",func(p *netv1.NetworkPolicy) {
   p.Spec.Ingress[0].Ports=append(p.Spec.Ingress[0].Ports,netv1.NetworkPolicyPort{Port:portPtr(9999)})
  }},
  {"ingress-extra-udp8080","p8c-portal-flows",func(p *netv1.NetworkPolicy) {
   p.Spec.Ingress[0].Ports=append(p.Spec.Ingress[0].Ports,netv1.NetworkPolicyPort{Port:portPtr(8080),Protocol:protoPtr(corev1.ProtocolUDP)})
  }},
  {"dns-extra-tcp5432","p8c-portal-flows",func(p *netv1.NetworkPolicy) {
   p.Spec.Egress[0].Ports=append(p.Spec.Egress[0].Ports,netv1.NetworkPolicyPort{Port:portPtr(5432)})
  }},
  {"ingress-empty-selectors","p8c-portal-flows",func(p *netv1.NetworkPolicy) {
   p.Spec.Ingress[0].From=[]netv1.NetworkPolicyPeer{{NamespaceSelector:&metav1.LabelSelector{},PodSelector:&metav1.LabelSelector{}}}
  }},
  {"cnpg-peer-selector-widened","p8c-cnpg-existing-flows",func(p *netv1.NetworkPolicy) {
   p.Spec.Egress[len(p.Spec.Egress)-1].To[0].PodSelector=&metav1.LabelSelector{}
  }},
  {"migrator-extra-api","p8c-migrator-flows",func(p *netv1.NetworkPolicy) {
   p.Spec.Egress=append(p.Spec.Egress,netv1.NetworkPolicyEgressRule{To:[]netv1.NetworkPolicyPeer{{IPBlock:&netv1.IPBlock{CIDR:"10.96.0.1/32"}}},Ports:[]netv1.NetworkPolicyPort{{Port:portPtr(443)}}})
  }},
  {"deny-baseline-extra-egress","baseline-default-deny-all",func(p *netv1.NetworkPolicy) {
   p.Spec.Egress=[]netv1.NetworkPolicyEgressRule{{To:[]netv1.NetworkPolicyPeer{{IPBlock:&netv1.IPBlock{CIDR:"10.96.0.1/32"}}},Ports:[]netv1.NetworkPolicyPort{{Port:portPtr(443)}}}}
  }},
  {"portal-missing-ingress","p8c-portal-flows",func(p *netv1.NetworkPolicy) {p.Spec.Ingress=nil}},
  {"ingress-nil-port","p8c-portal-flows",func(p *netv1.NetworkPolicy) {p.Spec.Ingress[0].Ports[0].Port=nil}},
  {"ingress-named-port","p8c-portal-flows",func(p *netv1.NetworkPolicy) {
   v:=intstr.FromString("https");p.Spec.Ingress[0].Ports[0].Port=&v
  }},
 }
 for _,tc:=range tests {t.Run(tc.name,func(t *testing.T) {
  ps:=loadPolicies(t)
  found:=false
  for i:=range ps {if ps[i].Name==tc.policy {tc.mutate(&ps[i]);found=true}}
  if !found {t.Fatal("fixture policy missing")}
  if len(validateStructure(ps))==0 {t.Fatal("non-contract rule accepted")}
 })}
}
