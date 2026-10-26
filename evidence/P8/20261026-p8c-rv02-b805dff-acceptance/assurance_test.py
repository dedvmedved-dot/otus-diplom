#!/usr/bin/env python3
"""Independent main-path assurance for the existing TC closure; mock kubectl only."""
import datetime, json, subprocess, tempfile, unittest
from pathlib import Path
from unittest import mock
import inventory as inv
from inventory_test import fixture, CANARY, KIND_BY_RESOURCE

class Assurance(unittest.TestCase):
    def run_item(self, kind, item, completed=None):
        resource=next(k for k,v in KIND_BY_RESOURCE.items() if v==kind)
        tail=["get",resource,"-A","-o","json"]
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"new"
            result=completed or subprocess.CompletedProcess([],0,json.dumps({"items":[item]}),"")
            with mock.patch.object(inv,"COMMANDS",[(tail,resource)]), mock.patch.object(inv.shutil,"which",return_value="/mock/kubectl"), mock.patch.object(inv.subprocess,"run",return_value=result) as run, mock.patch.object(inv.sys,"argv",["inventory.py","--context","mock","--output",str(dest)]):
                code=inv.main()
            row=json.loads((dest/"inventory.jsonl").read_text())
            self.assertEqual(row["argv"],run.call_args.args[0])
            self.assertEqual(row["argv"],["kubectl","--context","mock","--request-timeout=15s"]+tail)
            self.assertLessEqual(datetime.datetime.fromisoformat(row["start"]),datetime.datetime.fromisoformat(row["end"]))
            return code,row

    def test_both_url_fields_through_main(self):
        variants=[
            ("HTTPS://user:"+CANARY+"@host.invalid:9000/p?q="+CANARY,"https://host.invalid:9000"),
            ("https://[2001:db8::1]:9000/path","https://[2001:db8::1]:9000"),
            ("https://bad host.invalid/path",None),
            ("https://user:"+CANARY+"@host.invalid:bad/p",None),
            ("ftp://user:"+CANARY+"@host.invalid/path",None),
            ({"bad":CANARY},None),
            ("https://127.0.0.1:9000/path","https://127.0.0.1:9000"),
        ]
        for field in ("endpointURL","destinationPath"):
            for value,want in variants:
                with self.subTest(field=field,value_type=type(value).__name__):
                    item=fixture("ObjectStore");item["spec"]["data"][field]=value
                    code,row=self.run_item("ObjectStore",item)
                    self.assertEqual(code,0);self.assertIsNone(row["category"])
                    self.assertEqual(json.loads(row["output"])[0]["spec"]["data"][field],want)
                    self.assertNotIn(CANARY,row["output"])

    def test_legitimate_explicit_empty_rule_and_peer(self):
        item=fixture("NetworkPolicy")
        item["spec"]["ingress"]=[{},{"from":[{}]}]
        code,row=self.run_item("NetworkPolicy",item)
        self.assertEqual(code,0)
        self.assertEqual(json.loads(row["output"])[0]["spec"]["ingress"],[{},{"from":[{}]}])

    def test_sibling_lists_reject_falsey_wrong_shapes(self):
        for kind,field in [("NetworkPolicy","ingress"),("NetworkPolicy","egress"),("Gateway","listeners")]:
            for value in (False,0,"",{}):
                with self.subTest(kind=kind,field=field,value=value):
                    item=fixture(kind);item["spec"][field]=value
                    code,row=self.run_item(kind,item)
                    self.assertEqual((code,row["category"],row["output"]),(1,"PARSE_ERROR",""))

    def test_error_timestamps_and_exact_argv(self):
        for category,stderr in [("FORBIDDEN","Forbidden"),("TIMEOUT","context deadline exceeded"),("CONNECTION","connection refused")]:
            code,row=self.run_item("NetworkPolicy",fixture("NetworkPolicy"),subprocess.CompletedProcess([],1,CANARY,stderr+" "+CANARY))
            self.assertEqual((code,row["category"],row["output"]),(1,category,""))
            self.assertNotIn(CANARY,json.dumps(row))

if __name__=="__main__":unittest.main()
