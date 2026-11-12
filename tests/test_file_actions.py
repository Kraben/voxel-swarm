import os
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import file_actions as files

class FileSearchTests(unittest.TestCase):
    def test_natural_request_and_followup(self):
        self.assertEqual(files.intent('puedes buscar un archivo en mi Mac? necesito encontrarlo y no lo recuerdo'),'')
        self.assertEqual(files.intent('creo que se llama informe',[('busca un archivo',files.PROMPT)]),'informe')
        self.assertEqual(files.intent('busca el archivo informe.pdf'),'informe.pdf')
        self.assertIsNone(files.intent('no busques archivos'))
        self.assertIsNone(files.intent('qué es JSON'))
    def test_names_only_confined_no_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp,tempfile.TemporaryDirectory() as outside:
            root=Path(tmp);(root/'Informe.pdf').write_text('SECRET_CONTENT')
            (root/'.informe-oculto.pdf').write_text('hidden')
            (Path(outside)/'informe-externo.pdf').write_text('external')
            (root/'enlace').symlink_to(outside,target_is_directory=True)
            with patch.dict(os.environ,{'GHOST_SEARCH_ROOT':tmp}):
                answer=files.search('informe')
                self.assertIn('Informe.pdf',answer)
                for secret in ['SECRET_CONTENT','oculto','externo']:self.assertNotIn(secret,answer)
                self.assertIn('sin rutas',files.search('../'))
                self.assertIn('No encontré',files.search('no-existe'))

    def test_extension_in_request_and_followup(self):
        self.assertEqual(files.intent('puedes ayudarme a buscar un archivo en mi Mac o listarme los archivos que encuentres en extension .csv?'),'.csv')
        self.assertEqual(files.intent('extensión .csv',[('busca un archivo',files.PROMPT)]),'.csv')
        self.assertEqual(files.intent('lista los archivos con extensión CSV'),'.csv')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('cuentas.CSV','archivo.csv.bak','nota.txt'):(root/name).write_text('private')
            with patch.dict(os.environ,{'GHOST_SEARCH_ROOT':tmp}):
                answer=files.search('extensión .csv')
                self.assertIn('cuentas.CSV',answer)
                self.assertNotIn('archivo.csv.bak',answer)
                self.assertNotIn('nota.txt',answer)
    def test_default_folders_and_fair_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            for name in ('Desktop','Downloads','Documents','Music','Pictures','Movies'):(home/name).mkdir()
            (home/'Desktop'/'many').mkdir()
            for i in range(10):(home/'Desktop'/'many'/f'item{i}.csv').write_text('test')
            for name in ('Downloads','Music'):(home/name/f'{name}.csv').write_text('test')
            with patch.dict(os.environ,{'GHOST_SEARCH_ROOT':''}),patch.object(files.Path,'home',return_value=home),patch.object(files,'MAX_ENTRIES_PER_ROOT',3):
                self.assertEqual(len(files.roots()),6)
                answer=files.search('.csv')
                self.assertIn('Downloads.csv',answer);self.assertIn('Music.csv',answer)
                self.assertIn('Puede haber más',answer)
            with patch.dict(os.environ,{'GHOST_SEARCH_ROOT':str(home/'Music')}):
                self.assertEqual(files.roots(),[home/'Music'])

if __name__=='__main__':unittest.main()
