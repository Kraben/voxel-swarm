import sys,time,os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from group_actions import GroupActions,intent

class GroupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
  self.a=self.root/'Downloads';self.b=self.root/'Documents';self.desktop=self.root/'Desktop'
  for p in [self.a,self.b,self.desktop]:p.mkdir()
  for p in [self.a,self.b]:(p/'datos.csv').write_text(str(p))
  self.session=str(uuid4());self.manager=GroupActions(self.root/'data')
  self.manager.remember(self.session,[str(self.a/'datos.csv'),str(self.b/'datos.csv')])
 def test_preview_collisions_execute_undo(self):
  plan=self.manager.plan(self.session,self.desktop)
  self.assertEqual(len({r['to'] for r in plan['items']}),2)
  self.assertTrue((self.a/'datos.csv').exists());self.assertFalse(Path(plan['destination']).exists())
  with self.assertRaises(ValueError):self.manager.execute(plan['id'],str(uuid4()))
  self.assertEqual(self.manager.execute(plan['id'],self.session)['moved'],2)
  self.assertFalse((self.a/'datos.csv').exists())
  with self.assertRaises(ValueError):self.manager.execute(plan['id'],self.session)
  (self.a/'datos.csv').write_text('new')
  undo=self.manager.undo_plan(self.session);result=self.manager.execute(undo['id'],self.session)
  self.assertEqual(result['moved'],1);self.assertEqual(len(result['failed']),1)
  self.assertEqual((self.a/'datos.csv').read_text(),'new');self.assertEqual((self.b/'datos.csv').read_text(),str(self.b))
 def test_stale_search_changed_file_and_symlink_parent(self):
  stored=self.manager.read(self.session);stored['created']-=601;self.manager.save(stored)
  with self.assertRaises(ValueError):self.manager.plan(self.session,self.desktop)
  self.manager.remember(self.session,[str(self.a/'datos.csv')]);plan=self.manager.plan(self.session,self.desktop)
  (self.a/'datos.csv').write_text('changed')
  result=self.manager.execute(plan['id'],self.session);self.assertEqual(result['moved'],0)
  self.assertEqual((self.a/'datos.csv').read_text(),'changed')
  self.manager.remember(self.session,[str(self.b/'datos.csv')]);plan=self.manager.plan(self.session,self.desktop)
  moved=self.root/'Original';self.b.rename(moved);self.b.symlink_to(moved,target_is_directory=True)
  self.assertEqual(self.manager.execute(plan['id'],self.session)['moved'],0)
  self.assertTrue((moved/'datos.csv').exists())
 def test_context_required_and_negative_intent(self):
  with self.assertRaises(ValueError):self.manager.plan(str(uuid4()),self.desktop)
  self.assertEqual(intent('¿Puedes ayudarme a organizar esos archivos en una carpeta?'),'group')
  self.assertEqual(intent('deshacer agrupación de archivos'),'undo')
  self.assertIsNone(intent('no muevas esos archivos a una carpeta'))

if __name__=='__main__':unittest.main()
