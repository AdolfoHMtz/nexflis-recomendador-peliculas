"""Tests Fase 3 - Trazabilidad IR y metricas."""
import unittest


# ---------------------------------------------------------------------------
# ir_tecnicas en evaluar_matriz_recomendacion
# ---------------------------------------------------------------------------

class TestIRTecnicasEnScores(unittest.TestCase):

    def setUp(self):
        from core.motor_recomendacion import MotorRecomendacion
        self.motor = MotorRecomendacion()
        self.historial = [
            {
                'id': 1, 'title': 'Inception', 'runtime': 148,
                'genres_list': ['Ciencia ficción', 'Acción'],
                'keywords_list': ['sueños', 'ladrón', 'mente'],
                'cast_list': ['Leonardo DiCaprio', 'Joseph Gordon-Levitt'],
                'director': 'Christopher Nolan',
                'collection_id': 0, 'collection_name': '',
                'overview': 'Un ladrón que roba secretos a través de los sueños.',
                'vote_average': 8.8, 'progreso': 80, 'reaccion': 'like',
            }
        ]
        self.candidata = {
            'id': 2, 'title': 'Interstellar',
            'genres_list': ['Ciencia ficción', 'Drama'],
            'keywords_list': ['espacio', 'tiempo', 'agujero negro'],
            'cast_list': ['Matthew McConaughey', 'Anne Hathaway'],
            'director': 'Christopher Nolan',
            'collection_id': 0, 'collection_name': '',
            'overview': 'Un viaje a través del espacio para salvar a la humanidad.',
            'runtime': 169, 'vote_average': 8.6,
        }

    def test_ir_tecnicas_presente_en_recomendacion(self):
        result = self.motor.evaluar_matriz_recomendacion(self.candidata, self.historial)
        self.assertIn('ir_tecnicas', result)

    def test_ir_tecnicas_tiene_todas_las_claves(self):
        result = self.motor.evaluar_matriz_recomendacion(self.candidata, self.historial)
        claves = {'jaccard', 'jaccard_idf', 'bm25', 'semantica', 'intent'}
        self.assertEqual(set(result['ir_tecnicas'].keys()), claves)

    def test_ir_tecnicas_valores_en_rango(self):
        result = self.motor.evaluar_matriz_recomendacion(self.candidata, self.historial)
        for k, v in result['ir_tecnicas'].items():
            self.assertGreaterEqual(v, 0.0, f"{k} debe ser >= 0")
            self.assertLessEqual(v, 1.0, f"{k} debe ser <= 1")

    def test_jaccard_idf_refleja_cast_y_generos(self):
        result = self.motor.evaluar_matriz_recomendacion(self.candidata, self.historial)
        expected = round(result['expl_cast'] + result['expl_genres'], 4)
        self.assertAlmostEqual(result['ir_tecnicas']['jaccard_idf'], expected, places=3)

    def test_ir_tecnicas_presente_en_descubrimiento(self):
        result = self.motor.evaluar_matriz_descubrimiento(self.candidata, self.historial)
        self.assertIn('ir_tecnicas', result)
        claves = {'jaccard', 'jaccard_idf', 'bm25', 'semantica', 'intent'}
        self.assertEqual(set(result['ir_tecnicas'].keys()), claves)


# ---------------------------------------------------------------------------
# ir_tecnicas en MotorExplicacion
# ---------------------------------------------------------------------------

class TestMotorExplicacionIRTecnicas(unittest.TestCase):

    def test_generar_incluye_ir_tecnicas(self):
        from core.motor_explicacion import MotorExplicacion
        expl = MotorExplicacion()
        scores = {
            'score_final': 0.65, 'expl_cast': 0.10, 'expl_saga': 0.0,
            'expl_genres': 0.12, 'expl_dir': 0.05, 'expl_reaccion': 0.08,
            'expl_tiempo': 0.05, 'expl_semantic': 0.15, 'expl_intent': 0.10,
            'expl_quality': 0.0, 'shared_cast': ['Actor A'],
            'shared_genres': ['Drama'], 'same_director': True,
            'same_saga': False, 'saga_name': '',
        }
        candidata = {'id': 1, 'title': 'Test', 'genres_list': ['Drama'], 'director': 'Dir X'}
        semilla = {'id': 2, 'title': 'Seed', 'genres_list': ['Drama']}
        result = expl.generar(scores, candidata, semilla)

        self.assertIsInstance(result.ir_tecnicas, dict)
        self.assertIn('jaccard_idf', result.ir_tecnicas)
        self.assertAlmostEqual(
            result.ir_tecnicas['jaccard_idf'],
            round(scores['expl_cast'] + scores['expl_genres'], 4),
            places=3
        )
        self.assertAlmostEqual(result.ir_tecnicas['semantica'], scores['expl_semantic'], places=3)

    def test_to_dict_incluye_ir_tecnicas(self):
        from core.motor_explicacion import MotorExplicacion
        expl = MotorExplicacion()
        scores = {
            'score_final': 0.5, 'expl_cast': 0.08, 'expl_saga': 0.0,
            'expl_genres': 0.10, 'expl_dir': 0.0, 'expl_reaccion': 0.05,
            'expl_tiempo': 0.0, 'expl_semantic': 0.12, 'expl_intent': 0.07,
            'expl_quality': 0.0, 'shared_cast': [], 'shared_genres': [],
            'same_director': False, 'same_saga': False, 'saga_name': '',
        }
        result = expl.generar(scores, {'title': 'A'}, {'title': 'B'})
        d = result.to_dict()
        self.assertIn('ir_tecnicas', d)
        self.assertIsInstance(d['ir_tecnicas'], dict)


# ---------------------------------------------------------------------------
# Endpoint /api/recomendacion/ir-metrics via E2E
# ---------------------------------------------------------------------------

class TestIRMetricsEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        # Reutiliza la fabrica de la suite E2E
        from tests.test_e2e import _make_app
        cls.app = _make_app()
        cls.client = cls.app.test_client()

    def test_ir_metrics_historial_vacio(self):
        with self.client.session_transaction() as sess:
            sess.pop('historial', None)
        r = self.client.get('/api/recomendacion/ir-metrics')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data['n_historial'], 0)
        self.assertIn('tecnicas', data)
        for v in data['tecnicas'].values():
            self.assertEqual(v, 0.0)

    def test_ir_metrics_con_historial_en_session(self):
        with self.client.session_transaction() as sess:
            sess['historial'] = [
                {
                    'id': 10, 'title': 'Movie A', 'runtime': 100,
                    'genres_list': ['Drama'], 'keywords_list': ['amor'],
                    'cast_list': ['Actor X'], 'director': 'Dir A',
                    'collection_id': 0, 'collection_name': '',
                    'overview': 'Una historia de amor.', 'vote_average': 7.5,
                },
                {
                    'id': 11, 'title': 'Movie B', 'runtime': 90,
                    'genres_list': ['Drama', 'Romance'], 'keywords_list': ['amor', 'tragedia'],
                    'cast_list': ['Actor X', 'Actor Y'], 'director': 'Dir B',
                    'collection_id': 0, 'collection_name': '',
                    'overview': 'Una tragedia de amor.', 'vote_average': 7.0,
                },
            ]
        r = self.client.get('/api/recomendacion/ir-metrics')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data['n_historial'], 2)
        self.assertIn('tecnicas', data)
        self.assertIn('idf_terms', data)
        self.assertIn('historial_titles', data)
        self.assertEqual(len(data['historial_titles']), 2)
        # Jaccard de overviews similares debe ser > 0
        self.assertGreater(data['tecnicas']['jaccard'], 0.0)
        # IDF terms debe tener las tres categorias
        for campo in ('generos', 'keywords', 'cast'):
            self.assertIn(campo, data['idf_terms'])

    def test_ir_metrics_estructura_tecnicas(self):
        r = self.client.get('/api/recomendacion/ir-metrics')
        data = r.get_json()
        claves_esperadas = {'jaccard', 'jaccard_idf', 'bm25', 'semantica', 'intent'}
        self.assertEqual(set(data['tecnicas'].keys()), claves_esperadas)


if __name__ == '__main__':
    unittest.main()
