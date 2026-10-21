import base64
import copy
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('release_check', Path(__file__).with_name('release-check.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class TestReleaseBindings(unittest.TestCase):
    source = 'a' * 40
    digest = 'sha256:' + 'b' * 64

    def envelope(self, predicate, typ=None):
        return {'payload': base64.b64encode(json.dumps({'_type':'https://in-toto.io/Statement/v0.1', 'predicateType':typ or r.SLSA,
            'subject':[{'name':r.IMAGE,'digest':{'sha256':self.digest[7:]}}], 'predicate':predicate}).encode()).decode()}

    def test_predicate_and_subject_source_negatives(self):
        predicate = r.predicate(self.source)
        valid = self.envelope(predicate)
        r.check_attestations(json.dumps([valid]), self.digest, self.source, r.SLSA)
        for field in ('subject', 'source', 'builder', 'type', 'nested-statement'):
            bad = json.loads(base64.b64decode(valid['payload']))
            if field == 'subject': bad['subject'][0]['name'] = 'ghcr.io/other/image'
            elif field == 'source': bad['predicate']['invocation']['configSource']['digest']['sha1'] = 'c' * 40
            elif field == 'builder': bad['predicate']['builder']['id'] = 'wrong'
            elif field == 'type': bad['predicateType'] = 'wrong'
            else: bad['predicate'] = copy.deepcopy(bad)
            wrapped = {'payload':base64.b64encode(json.dumps(bad).encode()).decode()}
            with self.subTest(field=field), self.assertRaises(ValueError):
                r.check_attestations(json.dumps(wrapped), self.digest, self.source, r.SLSA)
        with self.assertRaises(ValueError): r.check_attestations(json.dumps(valid), 'sha256:'+'c'*64, self.source, r.SLSA)

    def test_sbom_exact_payload(self):
        sbom = {'spdxVersion':'SPDX-2.3','SPDXID':'SPDXRef-DOCUMENT'}
        signed = json.dumps(self.envelope(sbom, r.SPDX))
        r.check_attestations(signed,self.digest,self.source,r.SPDX,sbom)
        with self.assertRaises(ValueError): r.check_attestations(signed,self.digest,self.source,r.SPDX,{})

    def test_digest_and_private_gate_fail_closed(self):
        for value in ('', 'sha256:x', 'sha256:'+'A'*64, 'sha512:'+'b'*64):
            with self.assertRaises(ValueError): r.digest(value)
        good={'name':'otus-diplom-portal','package_type':'container','visibility':'private','repository':{'full_name':r.REPO}}
        self.assertEqual(r.private_metadata(good)['visibility'],'private')
        for key in ('name','package_type','visibility','repository'):
            bad=copy.deepcopy(good);bad.pop(key)
            with self.assertRaises(ValueError): r.private_metadata(bad)
        good['visibility']='public'
        with self.assertRaises(ValueError): r.private_metadata(good)

    def test_signature_source_digest(self):
        good={'critical':{'image':{'docker-manifest-digest':self.digest},'identity':{'docker-reference':r.IMAGE}},'optional':{'ref':self.source}}
        r.check_signature(json.dumps([good]),self.digest,self.source)
        with self.assertRaises(ValueError): r.check_signature(json.dumps([good]),self.digest,'c'*40)
        good['critical']['identity']['docker-reference']='wrong'
        with self.assertRaises(ValueError): r.check_signature(json.dumps([good]),self.digest,self.source)

if __name__ == '__main__': unittest.main()
