"""Read-only behavior tests; optional RESEARCH_TEST_INPUTS selects staged inputs."""
from pathlib import Path
import copy,json,os,re,unittest,yaml
import research_structure as rs
class DynamicResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ.get('RESEARCH_TEST_ROOT',str(rs.ROOT)))
        if os.environ.get('RESEARCH_TEST_INPUTS'):cls.base=json.loads(Path(os.environ['RESEARCH_TEST_INPUTS']).read_text())
        else:
            cls.base={}
            def reader(p):
                if p not in cls.base:cls.base[p]=rs.read(p) if (rs.ROOT/p).exists() else ''
                return cls.base[p]
            rs.generate(reader,cls.root)
        cls.model=yaml.safe_load(cls.base[rs.OUTLINE])
        cls.original_rows=rs.adoption_records(cls.model)
        cls.chapter_count=sum(c['included'] for c in cls.model['chapters'])
        cls.section_count=sum(s['included'] for c in cls.model['chapters'] if c['included'] for s in c['sections'])
    def setUp(self):self.data=copy.deepcopy(self.base);self.model=copy.deepcopy(self.model)
    def render(self):
        self.data[rs.OUTLINE]=yaml.safe_dump(self.model,allow_unicode=True,sort_keys=False)
        return rs.generate(lambda p:self.data.get(p,''),self.root)
    def test_idempotence(self):
        a,sa=self.render();self.data.update(a);b,sb=self.render();self.assertEqual(a,b);self.assertEqual(sa,sb)
    def test_initial_adoptions_kept(self):
        rows=rs.adoption_records(self.model);self.assertEqual(rows,self.original_rows)
        self.assertEqual(len({r['section_id'] for r in rows}),self.section_count)
    def test_chapter_reorder_preserves_identity_and_source(self):
        old=self.model['chapters'][0];oldid=old['id'];source=old['body_source'];self.model['chapters'][0],self.model['chapters'][1]=self.model['chapters'][1],self.model['chapters'][0]
        a,_=self.render();self.assertIn('# 第2章',a[old['path']]);self.assertEqual(self.model['chapters'][1]['id'],oldid);self.assertEqual(self.model['chapters'][1]['body_source'],source)
    def test_section_reorder_renumbers_only(self):
        c=self.model['chapters'][0];sid=c['sections'][0]['id'];c['sections'][0],c['sections'][1]=c['sections'][1],c['sections'][0]
        rows=rs.adoption_records(self.model);self.assertTrue(all(r['section'].startswith('1.2 ') for r in rows if r['section_id']==sid))
    def test_move_section_between_chapters(self):
        c=self.model['chapters'];sec=c[0]['sections'].pop(0);c[1]['sections'].append(sec);a,_=self.render();rows=json.loads(a['项目管理/章节采用记录.json']);self.assertTrue(all(r['chapter_id']==c[1]['id'] for r in rows if r['section_id']==sec['id']))
    def test_new_section(self):
        c=self.model['chapters'][0];s=copy.deepcopy(c['sections'][0]);s.update(id='section-test-added',title='测试新增节点',change_note='仅测试，不写入研究库');s.pop('subsections',None);c['sections'].append(s)
        a,st=self.render();self.assertEqual(st['sections'],self.section_count+1);self.assertIn('section-test-added',a[c['path']])
    def test_new_chapter(self):
        c=copy.deepcopy(self.model['chapters'][0]);c.update(id='chapter-test-added',path='论文章节/测试新章/章节导航.md',title='测试新章');c['sections']=[];self.model['chapters'].append(c)
        a,st=self.render();self.assertEqual(st['chapters'],self.chapter_count+1);self.assertIn(c['path'],a)
    def test_inactive_section_is_traceable_not_adopted(self):
        sec=self.model['chapters'][0]['sections'][0];sec['included']=False;a,st=self.render();self.assertEqual(st['sections'],self.section_count-1);self.assertIn(sec['id'],a[self.model['chapters'][0]['path']]);self.assertFalse(any(x['section_id']==sec['id'] for x in json.loads(a['项目管理/章节采用记录.json'])))
    def test_inactive_chapter(self):
        self.model['chapters'][0]['included']=False;a,st=self.render();self.assertEqual(st['chapters'],self.chapter_count-1);self.assertIn('停用但保留',a['论文章节/现行大纲.md'])
    def test_duplicate_id_rejected(self):
        self.model['chapters'][1]['sections'][0]['id']=self.model['chapters'][0]['sections'][0]['id']
        with self.assertRaises(AssertionError):self.render()
    def test_unknown_topic_rejected(self):
        self.model['chapters'][0]['sections'][0]['topics']=['主题研究/不存在/主题研究.md']
        with self.assertRaises(AssertionError):self.render()
    def test_unknown_role_rejected(self):
        p='主题研究/〔研究界定〕研究对象与样本边界/〔研究界定〕研究对象与样本边界.md';m=rs.meta(self.data[p]);m['research_role']='任意角色';self.data[p]=rs.header(self.data[p],m)
        with self.assertRaises(AssertionError):self.render()
    def test_role_change_updates_tags_and_views(self):
        p='主题研究/〔研究界定〕研究对象与样本边界/〔研究界定〕研究对象与样本边界.md';m=rs.meta(self.data[p]);m['research_roles_secondary']=['操作方法'];self.data[p]=rs.header(self.data[p],m);a,_=self.render()
        self.assertIn('研究角色/操作方法',rs.meta(a[p])['tags']);self.assertIn('〔研究界定〕研究对象与样本边界',a['主题研究/README.md'])
    def test_primary_role_change_requires_path_migration(self):
        p='主题研究/〔研究界定〕研究对象与样本边界/〔研究界定〕研究对象与样本边界.md';m=rs.meta(self.data[p]);m['research_role']='操作方法';self.data[p]=rs.header(self.data[p],m)
        with self.assertRaises(AssertionError):self.render()
    def test_topic_identity_independent_of_prefix(self):
        found=rs.artifacts.discover_topics(lambda p:self.data.get(p,''),self.root)
        expected={rs.meta(s)['wiki_id'] for p,s in self.data.items() if p.startswith('主题研究/') and s.startswith('---\n') and rs.meta(s).get('type')=='research-topic'}
        self.assertEqual({v['meta']['wiki_id'] for v in found.values()},expected)
        self.assertTrue(all(not t.startswith('〔') and v['meta']['wiki_id'].startswith('topic-') for t,v in found.items()))
    def test_duplicate_topic_id_rejected(self):
        found=list(rs.artifacts.discover_topics(lambda p:self.data.get(p,''),self.root).values());p=found[1]['path'];m=found[1]['meta'];m['wiki_id']=found[0]['meta']['wiki_id'];self.data[p]=rs.header(self.data[p],m)
        with self.assertRaises(AssertionError):self.render()
    def test_artifact_label_path_mismatch_rejected(self):
        p=next(p for p in self.data if p.startswith('研究成果/') and p.endswith('/README.md'));m=rs.meta(self.data[p]);m['artifact_label']='错误标签';self.data[p]=rs.header(self.data[p],m)
        with self.assertRaises(AssertionError):self.render()
    def test_evidence_requirements_rendered(self):
        c=self.model['chapters'][0];c['sections'][0]['evidence_required']=['仅测试的必要证据'];c['sections'][0]['completion_gate']='仅测试的完成判据';a,_=self.render()
        self.assertIn('仅测试的必要证据',a['论文章节/现行大纲.md']);self.assertIn('仅测试的完成判据',a[c['path']])
    def test_dependency_cycle_rejected(self):
        r={'schema_version':1,'nodes':[{'id':i,'title':i,'status':'仅测试','topics':[]} for i in ('a','b')],
           'edges':[{'from':'a','to':'b','kind':'dependency','label':'测试依赖'},{'from':'b','to':'a','kind':'dependency','label':'测试环'}]}
        with self.assertRaises(AssertionError):rs.validate_route(r,{})
    def test_feedback_cycle_allowed(self):
        r={'schema_version':1,'nodes':[{'id':i,'title':i,'status':'仅测试','topics':[]} for i in ('a','b')],
           'edges':[{'from':'a','to':'b','kind':'dependency','label':'测试依赖'},{'from':'b','to':'a','kind':'feedback','label':'测试反馈'}]}
        rs.validate_route(r,{})
    def test_state_change_updates_adoptions_without_promoting_others(self):
        s=self.model['chapters'][0]['sections'][0];s['status']='测试状态：暂停采用';a,_=self.render();rows=json.loads(a['项目管理/章节采用记录.json']);self.assertTrue(all(r['status']=='测试状态：暂停采用' for r in rows if r['section_id']==s['id']));self.assertTrue(all(r['status']!='测试状态：暂停采用' for r in rows if r['section_id']!=s['id']))
if __name__=='__main__':unittest.main(verbosity=2)
