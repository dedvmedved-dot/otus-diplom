package main
import("encoding/json";"fmt";"os";"strings";"github.com/sigstore/cosign/v3/pkg/cosign/attestation")
func main(){
 b,e:=os.ReadFile(os.Args[1]);if e!=nil{panic(e)}
 opts:=attestation.GenerateOpts{Predicate:strings.NewReader(string(b)),Type:"slsaprovenance",Digest:strings.Repeat("a",64),Repo:"ghcr.io/dedvmedved-dot/otus-diplom-portal"}
 st,e:=attestation.GenerateStatement(opts);if e!=nil{panic(e)}
 raw,e:=json.Marshal(st);if e!=nil{panic(e)};os.WriteFile("generated-statement.json",raw,0600)
 var v map[string]any;if e=json.Unmarshal(raw,&v);e!=nil{panic(e)}
 if v["predicateType"]!="https://slsa.dev/provenance/v0.2"{panic("type")}
 opts.Predicate=strings.NewReader(string(raw))
 if _,e=attestation.GenerateStatement(opts);e==nil{fmt.Println("NOTE: pinned Cosign accepts nested Statement but drops its fields; release-check must reject the empty predicate") }
 fmt.Println("pinned Cosign v3.1.3 GenerateStatement: valid predicate generation PASS; application verifier supplies strict field checks")
}
