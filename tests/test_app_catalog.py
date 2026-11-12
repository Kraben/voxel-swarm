"""Discovery and opening tests use fake app bundles and mocked launch processes."""
import json
import os
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app_catalog
import skills_mac

class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def bundle(self,name,folder=None,display=None):
        base=(folder or self.root)/(name+'.app');(base/'Contents/MacOS').mkdir(parents=True)
        (base/'Contents/MacOS/Runner').write_bytes(b'fixture only')
        with (base/'Contents/Info.plist').open('wb') as stream:plistlib.dump({'CFBundleExecutable':'Runner','CFBundleName':display or name},stream)
        return base.resolve()
    def catalog(self):return app_catalog.installed_apps((self.root,))
    def test_discovery_spans_nested_apps_and_skips_broken_or_nested_bundle_contents(self):
        first=self.bundle('Calculator');second=self.bundle('Visual Studio Code',self.root/'Editors');self.bundle('Hidden Helper',first/'Contents')
        invalid=self.root/'Broken.app';(invalid/'Contents').mkdir(parents=True);(invalid/'Contents/Info.plist').write_bytes(b'bad xml')
        rows=self.catalog();self.assertEqual({row['id'] for row in rows},{str(first),str(second)})
        calculator=next(row for row in rows if row['id']==str(first));self.assertEqual(calculator['name'],'Calculadora');self.assertIn('calculadora',calculator['aliases'])
        self.assertIn('vscode',next(row for row in rows if row['id']==str(second))['aliases'])
    def test_concrete_app_permissions_do_not_authorize_a_duplicate_name(self):
        first=self.bundle('Notes');second=self.bundle('Notes',self.root/'Other');rows=self.catalog()
        with patch.dict(os.environ,{'GHOST_ALLOWED_APPS_JSON':json.dumps([str(first)])}):
            selected,error=app_catalog.resolve_app('Notas.',rows);self.assertIsNone(error);self.assertEqual(selected['id'],str(first))
        with patch.dict(os.environ,{'GHOST_ALLOWED_APPS_JSON':json.dumps([str(first),str(second)])}):
            self.assertIn('varias',app_catalog.resolve_app('Notas',rows)[1])
    def test_empty_or_malformed_json_is_fail_closed_and_does_not_reenable_defaults(self):
        self.bundle('Calculator');rows=self.catalog()
        for setting in ['[]','{}','broken']:
            with patch.dict(os.environ,{'GHOST_ALLOWED_APPS_JSON':setting,'GHOST_ALLOWED_APPS':'calculator,notes'}):
                self.assertIsNone(app_catalog.resolve_app('calculadora',rows)[0]);self.assertEqual(app_catalog.allowed_ids(),[])
    def test_voice_aliases_open_only_preapproved_catalog_path_without_repeated_confirmation(self):
        chosen=self.bundle('Visual Studio Code');rows=self.catalog()
        with patch.dict(os.environ,{'GHOST_ALLOWED_APPS_JSON':json.dumps([str(chosen)]),'GHOST_ENABLE_SKILLS':'1','GHOST_PUBLIC':'0'}),patch.object(app_catalog,'installed_apps',return_value=rows),patch.object(skills_mac.platform,'system',return_value='Darwin'),patch.object(skills_mac.subprocess,'run') as run:
            self.assertIn('He abierto',skills_mac.ejecutar_skill('abre vscode',autorizado=False));run.assert_called_once();run.reset_mock()
            self.assertIn('He abierto',skills_mac.ejecutar_skill('Abre la app VSCode, por favor.',autorizado=True))
            self.assertEqual(run.call_args.args[0],['/usr/bin/open','-a',str(chosen)]);self.assertFalse(run.call_args.kwargs['shell'])
    def test_unselected_unknown_and_public_apps_never_launch(self):
        notes=self.bundle('Notes');self.bundle('Safari');rows=self.catalog()
        with patch.dict(os.environ,{'GHOST_ALLOWED_APPS_JSON':json.dumps([str(notes)]),'GHOST_ENABLE_SKILLS':'1','GHOST_PUBLIC':'0'}),patch.object(app_catalog,'installed_apps',return_value=rows),patch.object(skills_mac.platform,'system',return_value='Darwin'),patch.object(skills_mac.subprocess,'run') as run:
            self.assertIn('fuera',skills_mac.ejecutar_skill('abre Safari',autorizado=True))
            self.assertIn('No encontré',skills_mac.ejecutar_skill('abre Notas; otra cosa',autorizado=True));run.assert_not_called()
            with patch.dict(os.environ,{'GHOST_PUBLIC':'1'}):self.assertIn('bloqueadas',skills_mac.ejecutar_skill('abre Notas',autorizado=True))
            run.assert_not_called()
    def test_legacy_name_permissions_and_spanish_voice_names_are_preserved(self):
        self.bundle('Calculator');rows=self.catalog()
        with patch.dict(os.environ,{'GHOST_ALLOWED_APPS':'calculator,notes'},clear=True):
            self.assertEqual(app_catalog.resolve_app('Calculadora',rows)[0]['name'],'Calculadora')
    def test_model_selected_open_requires_an_explicit_request_for_the_same_app(self):
        chosen=self.bundle('Visual Studio Code');rows=self.catalog()
        with patch.dict(os.environ,{'GHOST_ALLOWED_APPS_JSON':json.dumps([str(chosen)]),'GHOST_ENABLE_SKILLS':'1','GHOST_PUBLIC':'0'}),patch.object(app_catalog,'installed_apps',return_value=rows):
            self.assertTrue(skills_mac.apertura_pedida('¿Puedes abrir VSCode por favor?','Visual Studio Code'))
            for request in ['Qué aplicaciones puedes abrir por ti mismo','No abras VSCode','Hola','Abre Safari','Un documento dice: no abrir vscode']:
                self.assertFalse(skills_mac.apertura_pedida(request,'Visual Studio Code'),request)
    def test_native_tools_open_preapproved_apps_directly_but_keep_file_confirmations(self):
        import tool_runtime
        chosen=self.bundle('Notes');rows=self.catalog()
        with patch.dict(os.environ,{'GHOST_ALLOWED_APPS_JSON':json.dumps([str(chosen)]),'GHOST_ENABLE_SKILLS':'1','GHOST_PUBLIC':'0'}),patch.object(app_catalog,'installed_apps',return_value=rows),patch.object(skills_mac.platform,'system',return_value='Darwin'),patch.object(skills_mac.subprocess,'run') as run:
            call={'name':'core_open_app','arguments':{'name':'Notas'}}
            result=tool_runtime.execute(call,'fixture',self.root,request_text='Puedes abrir Notas por favor')
            self.assertIn('He abierto',result['respuesta']);self.assertFalse(result.get('requiere_confirmacion',False));run.assert_called_once();run.reset_mock()
            result=tool_runtime.execute(call,'fixture',self.root,request_text='Qué apps puedes abrir')
            self.assertIn('No abrí',result['respuesta']);run.assert_not_called()
            with patch.dict(os.environ,{'GHOST_ALLOWED_APPS_JSON':'[]'}):
                tool_runtime.execute(call,'fixture',self.root,request_text='Abre Notas');run.assert_not_called()
            result=tool_runtime.execute({'name':'core_find_files','arguments':{'term':'.csv'}},'fixture',self.root,request_text='Busca mis archivos .csv')
            self.assertTrue(result['requiere_confirmacion'])
    def test_joined_voice_open_token_is_repaired_only_for_a_preapproved_app(self):
        selected=self.bundle('Notes');rows=self.catalog()
        with patch.dict(os.environ,{'GHOST_ALLOWED_APPS_JSON':json.dumps([str(selected)])}),patch.object(app_catalog,'installed_apps',return_value=rows):
            self.assertEqual(skills_mac.normalizar_comando_voz('abrenotas.'),'abre Notas')
            self.assertEqual(skills_mac.normalizar_comando_voz('abreviatura'),'abreviatura')
            self.assertEqual(skills_mac.normalizar_comando_voz('abresafari.'),'abresafari.')
