"""Dependency-free source check for the student form validation contract."""

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_HTML = PROJECT_ROOT / "frontend" / "index.html"


class FrontendValidationTests(unittest.TestCase):
    def test_invalid_student_submission_replaces_old_status_before_api_requests(self):
        html = FRONTEND_HTML.read_text(encoding="utf-8")

        # novalidate lets the submit handler run, where reportValidity() still
        # invokes the browser's native constraint message and focus behavior.
        self.assertIn('<form id="student-form" novalidate>', html)
        invalid_branch = html.split("if (!form.reportValidity()) {", 1)[1].split("return;", 1)[0]
        self.assertIn("statusNode.className = 'status error';", invalid_branch)
        self.assertIn(
            "statusNode.textContent = 'Please correct the highlighted student information fields before submitting.';",
            invalid_branch,
        )
        self.assertNotIn("post('/api/v1/", invalid_branch)


if __name__ == "__main__":
    unittest.main()
