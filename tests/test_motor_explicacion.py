import unittest

from core.motor_explicacion import MotorExplicacion


class TestMotorExplicacion(unittest.TestCase):
    def test_generar_explica_con_formula_y_texto(self):
        motor = MotorExplicacion()

        scores = {
            'score_final': 0.73,
            'expl_cast': 0.10,
            'expl_saga': 0.05,
            'expl_genres': 0.15,
            'expl_dir': 0.03,
            'expl_reaccion': 0.10,
            'expl_tiempo': 0.07,
            'expl_semantic': 0.13,
            'expl_intent': 0.10,
            'shared_cast': ['Actor Uno'],
            'shared_genres': ['Terror'],
            'same_director': False,
            'same_saga': False,
            'saga_name': '',
        }

        candidata = {
            'title': 'Pelicula Candidata',
            'genres_list': ['Terror'],
            'director': 'Director X',
        }
        semilla = {'title': 'Pelicula Base'}

        explicacion = motor.generar(scores, candidata, semilla)

        self.assertIn('Score =', explicacion.formula_texto)
        self.assertIn('Pelicula Candidata', explicacion.texto_natural)
        self.assertAlmostEqual(explicacion.score_final, 0.73, places=3)


if __name__ == '__main__':
    unittest.main()
