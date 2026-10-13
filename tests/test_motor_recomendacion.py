import unittest

from core.motor_recomendacion import MotorRecomendacion


def _movie(
    movie_id,
    title,
    genres=None,
    keywords=None,
    cast=None,
    director='',
    collection_id=0,
    collection_name='',
    overview='',
    vote_average=7.0,
):
    return {
        'id': movie_id,
        'title': title,
        'genres_list': genres or [],
        'keywords_list': keywords or [],
        'cast_list': cast or [],
        'director': director,
        'collection_id': collection_id,
        'collection_name': collection_name,
        'poster_path': '',
        'runtime': 100,
        'vote_average': vote_average,
        'overview': overview,
        'release_date': '2020-01-01',
    }


class TestMotorRecomendacion(unittest.TestCase):
    def setUp(self):
        self.motor = MotorRecomendacion()
        self.historial = [
            _movie(
                1,
                'Chucky',
                genres=['Terror', 'Thriller'],
                keywords=['muneco', 'posesion'],
                cast=['Brad Dourif', 'Alex Vincent'],
                director='Tom Holland',
                collection_id=10,
                collection_name='Child\'s Play Collection',
                overview='Muneco asesino y terror psicologico.',
            ),
            _movie(
                2,
                'Annabelle',
                genres=['Terror'],
                keywords=['muneca', 'posesion'],
                cast=['Vera Farmiga', 'Patrick Wilson'],
                director='John R. Leonetti',
                overview='Historia de una muneca poseida.',
            ),
        ]

    def test_evaluar_matriz_recomendacion_retorna_campos_clave(self):
        candidata = _movie(
            3,
            'Insidious',
            genres=['Terror'],
            keywords=['posesion', 'familia'],
            cast=['Patrick Wilson'],
            director='James Wan',
            overview='Familia acosada por fuerzas sobrenaturales.',
        )

        score = self.motor.evaluar_matriz_recomendacion(
            candidata,
            self.historial,
            reaccion='like',
            val_tiempo=0.8,
        )

        self.assertIn('score_final', score)
        self.assertIn('expl_semantic', score)
        self.assertIn('shared_genres', score)
        self.assertGreaterEqual(score['score_final'], 0.0)
        self.assertLessEqual(score['score_final'], 1.0)

    def test_evaluar_matriz_descubrimiento_retorna_score_valido(self):
        candidata = _movie(
            4,
            'Toy Story',
            genres=['Animacion', 'Familia'],
            keywords=['juguetes', 'amistad'],
            cast=['Tom Hanks'],
            director='John Lasseter',
            overview='Juguetes cobran vida cuando no hay humanos.',
        )

        score = self.motor.evaluar_matriz_descubrimiento(
            candidata,
            self.historial,
            val_tiempo=0.5,
        )

        self.assertIn('score_final', score)
        self.assertIn('expl_quality', score)
        self.assertGreaterEqual(score['score_final'], 0.0)
        self.assertLessEqual(score['score_final'], 1.0)

    def test_construir_arbol_crea_ramas(self):
        seed = self.historial[0]
        candidatas_depth = [
            _movie(11, 'The Conjuring', genres=['Terror'], keywords=['posesion']),
            _movie(12, 'Sinister', genres=['Terror'], keywords=['misterio']),
        ]
        candidatas_expl = [
            _movie(21, 'Coraline', genres=['Fantasia'], keywords=['ninos']),
            _movie(22, 'Gremlins', genres=['Comedia', 'Terror'], keywords=['criaturas']),
        ]

        raiz = self.motor.construir_arbol(
            peli_semilla=seed,
            candidatas_depth=candidatas_depth,
            candidatas_exploracion=candidatas_expl,
            historial=self.historial,
            reaccion='like',
            val_tiempo=0.7,
            max_depth=2,
        )

        self.assertIsNotNone(raiz)
        self.assertEqual(raiz.tipo, 'seed')
        self.assertIsNotNone(raiz.izquierda)
        self.assertIsNotNone(raiz.derecha)


if __name__ == '__main__':
    unittest.main()
