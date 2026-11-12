from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from desktop_actions import DesktopActions,intent

class DesktopActionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'desktop';self.root.mkdir()
        self.manager=DesktopActions(self.root,Path(self.tmp.name)/'data');self.session=str(uuid4())
    def test_plan_confirm_and_undo_preserve_content(self):
        for name in ['foto.png','respaldo.tar.gz','notas.md','script.py','otro.uf2']:(self.root/name).write_text(name)
        (self.root/'carpeta').mkdir();(self.root/'.oculto').write_text('privado')
        (self.root/'enlace').symlink_to(self.root/'notas.md')
        plan=self.manager.plan(self.session)
        self.assertEqual(plan['count'],5);self.assertTrue((self.root/'foto.png').exists())
        result=self.manager.execute(plan['id'],self.session)
        self.assertEqual(result['moved'],5);self.assertFalse(result['failed'])
        self.assertFalse((self.root/'foto.png').exists());self.assertTrue((self.root/'carpeta').is_dir())
        for row in plan['items']:self.assertEqual((self.root/row['to']).read_text(),row['from'])
        with self.assertRaises(ValueError):self.manager.execute(plan['id'],self.session)
        undo=self.manager.undo_plan(self.session);restored=self.manager.execute(undo['id'],self.session)
        self.assertEqual(restored['moved'],5)
        self.assertEqual((self.root/'foto.png').read_text(),'foto.png')
    def test_other_session_stale_file_symlink_and_no_overwrite(self):
        (self.root/'nota.txt').write_text('old');plan=self.manager.plan(self.session)
        with self.assertRaises(ValueError):self.manager.execute(plan['id'],str(uuid4()))
        (self.root/'nota.txt').write_text('updated')
        with self.assertRaises(ValueError):self.manager.execute(plan['id'],self.session)
        plan=self.manager.plan(self.session);result=self.manager.execute(plan['id'],self.session)
        (self.root/'nota.txt').write_text('new separate file')
        undo=self.manager.undo_plan(self.session);result=self.manager.execute(undo['id'],self.session)
        self.assertEqual(result['moved'],0);self.assertEqual((self.root/'nota.txt').read_text(),'new separate file')
        self.assertTrue((self.root/plan['items'][0]['to']).exists())
    def test_expired_preview_and_recovery_of_interrupted_manifest(self):
        (self.root/'nota.txt').write_text('datos')
        preview=self.manager.plan(self.session);saved=self.manager.load(preview['id']);saved['created']-=601;self.manager.save(saved)
        with self.assertRaises(ValueError):self.manager.execute(preview['id'],self.session)
        self.assertTrue((self.root/'nota.txt').exists())
        preview=self.manager.plan(self.session);self.manager.execute(preview['id'],self.session)
        saved=self.manager.load(preview['id']);saved['status']='applying';saved['items'][0]['state']='linking';self.manager.save(saved)
        undo=self.manager.undo_plan(self.session);self.assertEqual(undo['count'],1)
        self.assertEqual(self.manager.execute(undo['id'],self.session)['moved'],1)
        self.assertEqual((self.root/'nota.txt').read_text(),'datos')

    def test_direct_folders_reuse_accents_and_duplicate_names(self):
        (self.root/'Documentos').mkdir();(self.root/'Documentos'/'nota.txt').write_text('original existente')
        (self.root/'Imágenes').mkdir();(self.root/'nota.txt').write_text('nuevo')
        (self.root/'foto.png').write_text('imagen')
        preview=self.manager.plan(self.session)
        self.assertEqual(preview['layout'],'desktop')
        destinations={row['to'] for row in preview['items']}
        self.assertEqual(destinations,{'Documentos/nota_2.txt','Imágenes/foto.png'})
        self.assertEqual(self.manager.execute(preview['id'],self.session)['moved'],2)
        self.assertEqual((self.root/'Documentos'/'nota.txt').read_text(),'original existente')
        self.assertFalse(any(p.name.startswith('Ghost_') for p in self.root.iterdir()))
        undo=self.manager.undo_plan(self.session)
        self.assertEqual(self.manager.execute(undo['id'],self.session)['moved'],2)
        self.assertEqual((self.root/'nota.txt').read_text(),'nuevo')
        self.assertEqual((self.root/'Documentos'/'nota.txt').read_text(),'original existente')

    def test_block_destination_symlink_and_changed_folder(self):
        (self.root/'nota.txt').write_text('nuevo')
        outside=Path(self.tmp.name)/'outside';outside.mkdir()
        (self.root/'Documentos').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):self.manager.plan(self.session)
        (self.root/'Documentos').unlink();(self.root/'Documentos').mkdir()
        preview=self.manager.plan(self.session)
        (self.root/'Documentos').rename(self.root/'original')
        (self.root/'Documentos').mkdir()
        self.assertEqual(self.manager.execute(preview['id'],self.session)['moved'],0)
        self.assertEqual((self.root/'nota.txt').read_text(),'nuevo')
        self.assertEqual(list(outside.iterdir()),[])

    def test_old_batch_manifest_undo_and_empty_folder_cleanup(self):
        (self.root/'nota.txt').write_text('datos')
        public=self.manager.plan(self.session);plan=self.manager.load(public['id'])
        plan.pop('layout');plan['batch']='Ghost_Organizado_legacy'
        for row in plan['items']:
            for key in ('folder','folder_id','target_name'):row.pop(key,None)
        self.manager.save(plan)
        self.assertEqual(self.manager.execute(plan['id'],self.session)['moved'],1)
        self.assertTrue((self.root/plan['batch']/'Documentos'/'nota.txt').exists())
        undo=self.manager.undo_plan(self.session)
        self.assertEqual(self.manager.execute(undo['id'],self.session)['moved'],1)
        self.assertFalse((self.root/plan['batch']).exists())
        self.assertEqual((self.root/'nota.txt').read_text(),'datos')

    def test_intents(self):
        self.assertEqual(intent('¿Me ayudas a organizar mi escritorio?'),'organize')
        self.assertEqual(intent('deshacer organización del escritorio'),'undo')
        self.assertIsNone(intent('borra todo'))
