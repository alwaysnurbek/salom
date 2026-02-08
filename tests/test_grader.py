import unittest
from services.grader import normalize_answers, grade_submission

class TestGrader(unittest.TestCase):
    def test_normalize_letters(self):
        self.assertEqual(normalize_answers("abc"), "ABC")
        self.assertEqual(normalize_answers("A B C"), "ABC")
        self.assertEqual(normalize_answers("A,B,C"), "ABC")
    
    def test_normalize_indexed(self):
        self.assertEqual(normalize_answers("1A 2B 3C"), "ABC")
        self.assertEqual(normalize_answers("1.A 2.b 3.C"), "ABC")
        # Edge case: multiple digits? "12 A" -> "A"
        self.assertEqual(normalize_answers("10A 11B"), "AB")
        
    def test_grading_perfect(self):
        key = "ABCDE"
        sub = "ABCDE"
        c, w, p = grade_submission(sub, key)
        self.assertEqual(c, 5)
        self.assertEqual(w, 0)
        self.assertEqual(p, 100.0)

    def test_grading_partial(self):
        key = "ABCDE"
        sub = "ABXDE" # 3rd wrong
        c, w, p = grade_submission(sub, key)
        self.assertEqual(c, 4)
        self.assertEqual(w, 1) # Total 5, 4 correct -> 1 wrong
        self.assertEqual(p, 80.0)
        
    def test_grading_length_mismatch(self):
        # Grader assumes lengths match or iterates zip.
        # Zip stops at shortest.
        key = "ABC"
        sub = "AB"
        c, w, p = grade_submission(sub, key)
        self.assertEqual(c, 2)
        self.assertEqual(w, 1) # Total 3, 2 correct -> 1 wrong
        self.assertAlmostEqual(p, 66.67, places=2)

if __name__ == '__main__':
    unittest.main()
