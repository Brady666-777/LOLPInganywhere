"""Qt geometry regression: a question mark must have its dot below its hook."""
import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('PySide6'), 'Qt geometry tests require PySide6')
class IconOrientationTests(unittest.TestCase):
    def test_question_mark_dot_is_below_hook(self):
        from lolping.visuals import Art, check_assets
        path = Art(check_assets()).paths['missing']
        contours = path.toSubpathPolygons()
        self.assertEqual(len(contours), 2)
        hook, dot = sorted(contours, key=lambda p: p.boundingRect().height(), reverse=True)
        self.assertGreater(dot.boundingRect().top(), hook.boundingRect().bottom())

    def test_asymmetric_icon_stays_upright_without_horizontal_mirroring(self):
        from PySide6.QtCore import QPointF
        from lolping.visuals import Art
        # An L with a foot to the right, authored in AppKit's y-up coordinates.
        vectors = {'fixture': {'contours': [[(0, 0), (1, 0), (1, .2), (.2, .2), (.2, 1), (0, 1)]]}}
        path = Art(vectors).paths['fixture']
        self.assertTrue(path.contains(QPointF(.8, .9)))  # Foot at bottom right.
        self.assertTrue(path.contains(QPointF(.1, .1)))  # Stem at top left.
        self.assertFalse(path.contains(QPointF(.8, .1)))
