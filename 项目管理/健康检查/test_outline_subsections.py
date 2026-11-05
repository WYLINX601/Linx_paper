"""Read-only regression tests for outline subsections; no Paper writes."""
from pathlib import Path
from copy import deepcopy
import argparse,unittest,yaml
import research_structure as rs

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-dir',type=Path,help='Optional reviewed candidate overlay outside Paper')
args,remaining=parser.parse_known_args()
cache={}
def current(p):
    if p not in cache:
        f=args.source_dir/p if args.source_dir else None
        cache[p]=f.read_text() if f and f.is_file() else rs.read(p) if (rs.ROOT/p).is_file() else ''
    return cache[p]
model=yaml.safe_load(current(rs.OUTLINE))
base_out,base_stats=rs.generate(current)
ch2=next(c for c in model['chapters'] if any(s.get('subsections') for s in c['sections']))
chapter_index=model['chapters'].index(ch2)
section_index=next(i for i,s in enumerate(ch2['sections']) if s.get('subsections'))

def render(m):
    return rs.generate(lambda p:yaml.safe_dump(m,allow_unicode=True,sort_keys=False) if p==rs.OUTLINE else current(p))
def selected(m):return m['chapters'][chapter_index]['sections'][section_index]
def shown(out):return out['论文章节/现行大纲.md'].split('## 标题总览（二级与已展开的三级）',1)[1].split('## 后续证据任务',1)[0]

class OutlineSubsectionTests(unittest.TestCase):
    def test_three_level_rendering(self):
        sub=selected(model)['subsections'][0]
        self.assertIn(sub['title'],shown(base_out))
        self.assertIn('<a id="'+sub['id']+'"></a>',base_out[ch2['path']])
        self.assertIn(' --> '+sub['id'],base_out[ch2['path']])
    def test_idempotent_generation(self):
        out,stats=rs.generate(lambda p:base_out[p] if p in base_out else current(p))
        self.assertEqual(base_out,out);self.assertEqual(base_stats,stats)
    def test_reorder(self):
        m=deepcopy(model);subs=selected(m)['subsections'];subs[0],subs[1]=subs[1],subs[0]
        out,stats=render(m)
        self.assertIn(f'{chapter_index+1}.{section_index+1}.1 '+subs[0]['title'],shown(out))
        self.assertEqual(stats['subsections'],base_stats['subsections'])
        self.assertEqual(rs.adoption_records(m),rs.adoption_records(model))
    def test_add(self):
        m=deepcopy(model);sub=deepcopy(selected(m)['subsections'][0]);sub['id']='sub-regression-only';sub['title']='测试节点';selected(m)['subsections'].append(sub)
        out,stats=render(m);self.assertEqual(stats['subsections'],base_stats['subsections']+1)
        self.assertIn('测试节点',shown(out));self.assertEqual(rs.adoption_records(m),rs.adoption_records(model))
    def test_disable_child_preserves_anchor(self):
        m=deepcopy(model);sub=selected(m)['subsections'][0];sub['included']=False
        out,stats=render(m);self.assertNotIn(sub['title'],shown(out));self.assertIn('<a id="'+sub['id']+'"></a>',out[ch2['path']])
        self.assertEqual(stats['subsections'],base_stats['subsections']-1)
    def test_disable_parent_preserves_children(self):
        m=deepcopy(model);sec=selected(m);sec['included']=False
        out,stats=render(m)
        for sub in sec['subsections']:
            self.assertNotIn(sub['title'],shown(out));self.assertIn('<a id="'+sub['id']+'"></a>',out[ch2['path']])
        self.assertEqual(stats['subsections'],base_stats['subsections']-sum(x['included'] for x in sec['subsections']))
    def test_disable_chapter_preserves_children(self):
        m=deepcopy(model);m['chapters'][chapter_index]['included']=False
        out,stats=render(m)
        for s in m['chapters'][chapter_index]['sections']:
            for sub in s.get('subsections',[]):self.assertIn('<a id="'+sub['id']+'"></a>',out[ch2['path']])
        self.assertEqual(stats['chapters'],base_stats['chapters']-1)
    def test_cross_chapter_move_preserves_forwarding_anchor(self):
        m=deepcopy(model);sub=selected(m)['subsections'].pop(0);dest=next(c for c in m['chapters'] if c['id']!=ch2['id']);dest['sections'][0].setdefault('subsections',[]).append(sub)
        out,stats=render(m)
        self.assertIn('<a id="'+sub['id']+'"></a>',out[ch2['path']]);self.assertIn('<a id="'+sub['id']+'"></a>',out[dest['path']])
        self.assertIn('三级稳定ID不变，原入口转接',out[ch2['path']]);self.assertEqual(stats['subsections'],base_stats['subsections'])
    def test_duplicate_ids_rejected(self):
        m=deepcopy(model);selected(m)['subsections'][0]['id']=m['chapters'][-1]['sections'][0]['id']
        with self.assertRaises(AssertionError):render(m)
    def test_invalid_child_rejected(self):
        m=deepcopy(model);selected(m)['subsections'][0]['included']='true'
        with self.assertRaises(AssertionError):render(m)
    def test_legacy_without_subsections(self):
        m=deepcopy(model)
        for c in m['chapters']:
            for s in c['sections']:s.pop('subsections',None)
        out,stats=render(m);self.assertEqual(stats['subsections'],0);self.assertEqual(rs.adoption_records(m),rs.adoption_records(model))

if __name__=='__main__':unittest.main(argv=['test_outline_subsections.py']+remaining,verbosity=2)
