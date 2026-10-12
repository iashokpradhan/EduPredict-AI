import unittest
import pandas as pd

from tests.integration.prerequisites import DATA_PATH, require_local_files


EXPECTED_COLUMNS = [
    "Student_ID",
    "Gender",
    "Age",
    "Major",
    "Attendance_Pct",
    "Study_Hours_Per_Day",
    "Previous_CGPA",
    "Sleep_Hours",
    "Social_Hours_Week",
    "Final_CGPA",
]


class DatasetValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_local_files(DATA_PATH)
        cls.data = pd.read_csv(DATA_PATH)

    def test_source_schema_and_shape(self):
        self.assertEqual(self.data.shape, (5000, 10))
        self.assertEqual(self.data.columns.tolist(), EXPECTED_COLUMNS)
        self.assertEqual(self.data["Student_ID"].nunique(), len(self.data))

    def test_required_values_and_domains(self):
        self.assertFalse(self.data.isna().any().any())
        self.assertEqual(int(self.data.duplicated().sum()), 0)
        self.assertTrue(self.data["Final_CGPA"].between(0, 4).all())
        self.assertTrue(self.data["Attendance_Pct"].between(0, 100).all())
        self.assertTrue(self.data["Study_Hours_Per_Day"].between(0, 24).all())
        self.assertTrue(self.data["Sleep_Hours"].between(0, 24).all())
        self.assertTrue(self.data["Social_Hours_Week"].between(0, 168).all())


if __name__ == "__main__":
    unittest.main()
