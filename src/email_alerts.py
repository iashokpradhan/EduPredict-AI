"""IILM University Automated Academic Advisory Email Dispatcher.

Handles:
- Generation of institutional advisory notices for at-risk students.
- HTML and plain-text multi-part email templating with 4-Week Recovery Roadmaps.
- SMTP dispatching (supporting environment-based Gmail/SMTP, Resend/SendGrid)
  with a robust offline simulation mode for local viva demonstrations.
"""

from __future__ import annotations

import email.message
import html
import logging
import os
import smtplib
from typing import Any

LOGGER = logging.getLogger("edupredict.email_alerts")

# Configuration via environment variables
SMTP_HOST = os.environ.get("EDUPREDICT_SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("EDUPREDICT_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("EDUPREDICT_SMTP_USER", "")
SMTP_PASS = os.environ.get("EDUPREDICT_SMTP_PASS", "")
FROM_EMAIL = os.environ.get("EDUPREDICT_FROM_EMAIL", "academics@iilm.edu")
FROM_NAME = "IILM University Academic Advisory Cell"


def generate_advisory_email_html(
    student_name: str,
    student_email: str,
    predicted_cgpa: float,
    major: str,
    attendance_pct: float,
    recovery_plan: list[dict[str, Any]] | None = None,
    advisor_name: str = "Dr. Priya Mehta (Dean of Academics)",
) -> str:
    """Generate a clean, institutional HTML email for student performance warning & recovery."""
    sanitized_name = html.escape(student_name)
    sanitized_major = html.escape(major)
    sanitized_advisor = html.escape(advisor_name)

    weeks_html = ""
    if recovery_plan:
        for item in recovery_plan:
            week_title = html.escape(str(item.get("title", f"Week {item.get('week', '')}")))
            week_focus = html.escape(str(item.get("focus", "")))
            actionable = html.escape(str(item.get("actionable", "")))
            hours = html.escape(str(item.get("hours_target", "")))
            weeks_html += f"""
            <div style="background: #f8fafc; border-left: 4px solid #6366f1; padding: 12px 16px; margin-bottom: 10px; border-radius: 4px;">
                <div style="font-weight: 700; color: #1e293b; font-size: 14px;">{week_title}: {week_focus}</div>
                <div style="color: #475569; font-size: 13px; margin: 4px 0;"><strong>Action:</strong> {actionable}</div>
                <div style="color: #64748b; font-size: 12px;"><strong>Study Target:</strong> {hours}</div>
            </div>
            """
    else:
        weeks_html = "<p style='color: #64748b; font-size: 13px;'>Consult your assigned faculty advisor to formulate a personalized 4-week recovery milestone.</p>"

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>IILM University — Academic Advisory Notification</title>
</head>
<body style="font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px; color: #334155;">
  <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); padding: 24px; text-align: center; color: #ffffff;">
      <div style="font-size: 13px; letter-spacing: 0.1em; text-transform: uppercase; color: #a5b4fc; font-weight: 600;">IILM University · Academic Advisory Cell</div>
      <h1 style="margin: 8px 0 0 0; font-size: 20px; font-weight: 700; color: #ffffff;">Proactive Academic Support Notice</h1>
    </div>

    <!-- Main Content -->
    <div style="padding: 24px 28px;">
      <p style="font-size: 15px; line-height: 1.5; color: #1e293b; margin-top: 0;">
        Dear <strong>{sanitized_name}</strong>,
      </p>
      <p style="font-size: 14px; line-height: 1.6; color: #475569;">
        This is an automated early-warning notice from the <strong>IILM University EduPredict System</strong>. Based on midterm behavioural indicators in <strong>{sanitized_major}</strong>, our proactive early warning model has projected a trajectory that may place you at risk of academic warning or probation.
      </p>

      <!-- Key Metrics Table -->
      <div style="display: flex; gap: 12px; margin: 20px 0; background: #fef2f2; border: 1px solid #fee2e2; border-radius: 8px; padding: 14px;">
        <div style="flex: 1; text-align: center; border-right: 1px solid #fca5a5;">
          <div style="font-size: 11px; text-transform: uppercase; color: #991b1b; font-weight: 600;">Projected CGPA</div>
          <div style="font-size: 22px; font-weight: 800; color: #b91c1c;">{predicted_cgpa:.2f}</div>
        </div>
        <div style="flex: 1; text-align: center; border-right: 1px solid #fca5a5;">
          <div style="font-size: 11px; text-transform: uppercase; color: #991b1b; font-weight: 600;">Attendance</div>
          <div style="font-size: 22px; font-weight: 800; color: #b91c1c;">{attendance_pct:.1f}%</div>
        </div>
        <div style="flex: 1; text-align: center;">
          <div style="font-size: 11px; text-transform: uppercase; color: #991b1b; font-weight: 600;">Risk Level</div>
          <div style="font-size: 18px; font-weight: 800; color: #b91c1c; margin-top: 3px;">High Priority</div>
        </div>
      </div>

      <h3 style="font-size: 15px; color: #1e293b; margin-bottom: 8px; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px;">
        📋 Recommended 4-Week Recovery Roadmap
      </h3>
      {weeks_html}

      <div style="margin-top: 24px; padding: 16px; background: #eff6ff; border-radius: 8px; border: 1px solid #bfdbfe;">
        <div style="font-weight: 600; color: #1e40af; font-size: 13px;">👨‍🏫 Required Next Step:</div>
        <p style="margin: 4px 0 0 0; font-size: 13px; color: #1e3a8a; line-height: 1.5;">
          Please schedule an office-hour consultation with <strong>{sanitized_advisor}</strong> within the next 5 business days to review this recovery plan and adjust your course workload.
        </p>
      </div>
    </div>

    <!-- Footer -->
    <div style="background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 16px 24px; text-align: center; font-size: 11px; color: #94a3b8;">
      <p style="margin: 0;">This email is an automated academic decision-support communication sent by IILM University EduPredict AI.</p>
      <p style="margin: 4px 0 0 0;">Confidential · Intended solely for {student_email}</p>
    </div>
  </div>
</body>
</html>
"""


def dispatch_advisory_email(
    student_name: str,
    student_email: str,
    predicted_cgpa: float,
    major: str,
    attendance_pct: float,
    recovery_plan: list[dict[str, Any]] | None = None,
    advisor_name: str = "Dr. Priya Mehta (Dean of Academics)",
) -> dict[str, Any]:
    """Dispatch the email alert or log simulation if SMTP credentials are unconfigured."""
    subject = f"⚠️ [IILM Academic Notice] Urgent Proactive Advisory Notice for {student_name}"
    html_content = generate_advisory_email_html(
        student_name=student_name,
        student_email=student_email,
        predicted_cgpa=predicted_cgpa,
        major=major,
        attendance_pct=attendance_pct,
        recovery_plan=recovery_plan,
        advisor_name=advisor_name,
    )

    # If real SMTP credentials exist in environment, dispatch via SMTP
    if SMTP_HOST and SMTP_USER and SMTP_PASS:
        try:
            msg = email.message.EmailMessage()
            msg["Subject"] = subject
            msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
            msg["To"] = student_email
            msg.set_content(
                f"Dear {student_name},\n\nThis is an urgent academic advisory notice from IILM University.\n"
                f"Your projected CGPA is {predicted_cgpa:.2f} with attendance of {attendance_pct:.1f}%.\n"
                f"Please consult {advisor_name} to review your 4-week recovery roadmap.\n\n"
                "IILM University EduPredict System."
            )
            msg.add_alternative(html_content, subtype="html")

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)

            LOGGER.info("Successfully delivered advisory email to %s via SMTP.", student_email)
            return {
                "status": "delivered",
                "recipient": student_email,
                "subject": subject,
                "mode": "live_smtp",
                "message": f"Official academic advisory warning successfully sent to {student_email}.",
            }
        except Exception as exc:
            LOGGER.warning("SMTP delivery failed (%s). Falling back to simulated log.", exc)

    # Standard / Offline Simulation Mode (Used for Capstone Demonstrations & Testing)
    LOGGER.info("[DEMO ALERT DISPATCHED] To: %s | Subject: %s", student_email, subject)
    return {
        "status": "delivered_simulated",
        "recipient": student_email,
        "subject": subject,
        "mode": "simulation",
        "message": f"Demonstration Notice: Official academic warning generated and queued for {student_email}.",
        "html_preview": html_content,
    }
