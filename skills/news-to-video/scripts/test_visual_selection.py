import copy
import unittest
from score_visuals import assess

class SelectionTests(unittest.TestCase):
    def project(self):
        def candidate(cid,image,score):
            return dict(id=cid,uses_image=image,gates=dict(facts=True,source=True,layout=True,execution=True),scores=dict(relevance=score,appeal=score,narrative=score,readability=score),reason='editor explanation')
        return dict(visual_selection_version=1,scenes=[dict(visual_selection=dict(goal='scale before numbers',selected='image',candidates=[candidate('image',True,4),candidate('text',False,3)]))])
    def test_weighted_selection(self):
        r=assess(self.project());self.assertEqual(r['status'],'passed');self.assertEqual(r['scenes'][0]['candidates'][0]['score'],80)
    def test_gate_overrules_score(self):
        p=self.project();p['scenes'][0]['visual_selection']['candidates'][0]['gates']['facts']=False
        self.assertEqual(assess(p)['status'],'failed')
    def test_missing_picture_alternative(self):
        p=self.project();p['scenes'][0]['visual_selection']['candidates'].pop(0)
        self.assertEqual(assess(p)['status'],'failed')
    def test_override_required(self):
        p=self.project();p['scenes'][0]['visual_selection']['selected']='text'
        self.assertEqual(assess(p)['status'],'failed')
        p['scenes'][0]['visual_selection']['override_reason']='user requires plain text'
        self.assertEqual(assess(p)['status'],'passed')
    def test_near_tie_picture_priority(self):
        p=self.project();spec=p['scenes'][0]['visual_selection']
        spec['candidates'][1]['scores']={k:4.2 for k in spec['candidates'][1]['scores']}
        self.assertEqual(assess(p)['scenes'][0]['recommended'],'image')
    def test_legacy_unchanged(self):
        self.assertEqual(assess(dict(scenes=[]))['status'],'legacy-not-assessed')
    def test_no_nan_or_boolean_scores(self):
        for value in (float('nan'),True):
            p=self.project();p['scenes'][0]['visual_selection']['candidates'][0]['scores']['appeal']=value
            self.assertEqual(assess(p)['status'],'failed')
    def test_middle_host_not_exempt(self):
        p=dict(visual_selection_version=1,scenes=[{},dict(presenter='host',visual_selection=dict(exempt_reason='host')),{}])
        self.assertTrue(any('exemption' in e for e in assess(p)['errors']))

if __name__=='__main__':
    unittest.main()
