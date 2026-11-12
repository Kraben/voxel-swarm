import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import web_actions as web

class SearchTests(unittest.TestCase):
    def setUp(self):web.CACHE.clear()
    def test_exact_regression_json_and_unrelated_queen_are_not_mixed(self):
        rows=[{'title':'Queen Sonja of Norway','body':'Harald and Sonja married.','href':'https://en.wikipedia.org/wiki/Queen_Sonja'},
              {'title':'JSON — formato de datos','body':'JSON es un formato de intercambio de datos.','href':'https://example.com/json#intro'},
              {'title':'duplicate JSON','body':'JSON','href':'https://example.com/json#other'},
              {'title':'JSON','body':'bad','href':'javascript:alert(1)'}]
        result=web.clean_results(rows,'qué es JSON')
        self.assertEqual(len(result),1);self.assertEqual(result[0]['url'],'https://example.com/json')
    def test_fallback_error_then_irrelevant_then_good_and_cache(self):
        good=[{'title':'Qué es JSON','body':'JSON es un formato de datos.','href':'https://example.com/json'}]
        irrelevant=[{'title':'Queen Sonja of Norway','body':'A queen','href':'https://example.com/queen'}]
        with patch.object(web,'fetch_engine') as client:
            client.side_effect=[RuntimeError('temporary'),irrelevant,good]
            result=web.search('qué es JSON');self.assertTrue(result)
            self.assertEqual(client.call_count,3)
            self.assertEqual([call.args[0] for call in client.call_args_list],list(web.ENGINES))
            self.assertEqual(web.search('QUÉ ES JSON'),result)
            self.assertEqual(client.call_count,3)
    def test_no_fake_success_when_all_engines_fail(self):
        with patch.object(web,'fetch_engine') as client:
            client.side_effect=RuntimeError('fixture')
            with self.assertRaises(web.SearchUnavailable):web.search('qué es JSON')
            self.assertFalse(web.CACHE)

    def test_html_parser_resolves_redirect_and_extracts_only_results(self):
        page=b'<div class="result"><h2><a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fjson">JSON</a></h2><a class="result__snippet">JSON es un formato.</a></div><a href="https://bad.invalid">Not a search result</a>'
        rows=web.parse_engine('duckduckgo',page)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['href'],'https://example.com/json')
        self.assertEqual(rows[0]['body'],'JSON es un formato.')

class AutomaticRoutingTests(unittest.TestCase):
    def test_normal_questions_and_current_topics_use_web(self):
        examples={'¿Qué es JSON?':'Qué es JSON','qué es JSON':'qué es JSON','Explícame qué es JSON':'qué es JSON','¿Quién es el presidente de México?':'Quién es el presidente de México','¿Cómo funciona HTTP?':'Cómo funciona HTTP','¿Qué clima hace hoy en Monterrey?':'Qué clima hace hoy en Monterrey','Dime las últimas noticias de tecnología':'las últimas noticias de tecnología'}
        for text,query in examples.items():
            with self.subTest(text=text):
                decision=web.route(text);self.assertEqual(decision['query'],query);self.assertTrue(decision['automatic'])
    def test_conversation_local_commands_sensitive_data_and_optout_stay_out(self):
        examples=['Hola Ghost','¿Quién eres?','Ayúdame a redactar un mensaje','organiza mi escritorio','ver memoria','busca el archivo informe','¿Qué es mi contraseña?','qué es JSON sin internet','No uses internet: qué es JSON','¿Qué es JSON? Contacta a ejemplo@example.com','¿Cómo funciona este código?\n```python\nprint(1)\n```']
        for text in examples:
            with self.subTest(text=text):self.assertIsNone(web.route(text))
    def test_search_request_does_not_require_a_button_or_magic_internet_word(self):
        self.assertEqual(web.route('busca información de JSON'),{'query':'información de JSON','automatic':False})
