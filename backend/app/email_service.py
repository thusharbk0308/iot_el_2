import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os
import logging
import threading
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _send_email_sync(subject: str, html_body: str, attachment_path: str = None):
    """
    Synchronously sends an email. Should be run inside a thread.
    """
    try:
        # Check if email is configured
        if config.SMTP_USER == "your_email@gmail.com" or not config.SMTP_PASSWORD:
            logger.warning("SMTP email not fully configured in config.py. Skipping email dispatch.")
            return

        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = config.SMTP_USER
        msg["To"] = config.ALERT_RECEIVER_EMAIL

        # HTML body
        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)
        
        msg_text = MIMEText(html_body, "html")
        msg_alternative.attach(msg_text)

        # Attachment
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                img_data = f.read()
            image = MIMEImage(img_data, name=os.path.basename(attachment_path))
            # Define ID for embedding in HTML if wanted, or just attach
            image.add_header("Content-ID", "<intruder_image>")
            image.add_header("Content-Disposition", "inline", filename=os.path.basename(attachment_path))
            msg.attach(image)

        # Connection
        if config.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=10)
            server.ehlo()
            if server.has_extn("STARTTLS"):
                server.starttls()
                server.ehlo()

        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.sendmail(config.SMTP_USER, config.ALERT_RECEIVER_EMAIL, msg.as_string())
        server.quit()
        logger.info(f"Intruder alert email successfully sent to {config.ALERT_RECEIVER_EMAIL}.")
        
    except Exception as e:
        logger.error(f"Failed to send email alert: {str(e)}")

def send_intruder_email(timestamp_str: str, attachment_path: str = None):
    """
    Triggers an email alert asynchronously in a background thread to prevent blocking AI inference.
    """
    subject = "⚠️ Security Alert: Unknown Intruder Detected!"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
          <h2 style="color: #d9534f; border-bottom: 2px solid #d9534f; padding-bottom: 10px; margin-top: 0;">
            ⚠️ Intruder Security Alert
          </h2>
          <p>The Smart Security System has detected an unauthorized person attempting to gain access.</p>
          <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <tr style="background-color: #f9f9f9;">
              <td style="padding: 10px; font-weight: bold; width: 120px;">Timestamp:</td>
              <td style="padding: 10px;">{timestamp_str}</td>
            </tr>
            <tr>
              <td style="padding: 10px; font-weight: bold;">Status:</td>
              <td style="padding: 10px; color: #d9534f; font-weight: bold;">Access Denied</td>
            </tr>
          </table>
          <p>Please review the dashboard immediately to check the live stream and take action.</p>
          <div style="text-align: center; margin-top: 20px;">
             <p style="font-style: italic; color: #777;">A snapshot of the incident is attached to this email.</p>
          </div>
        </div>
      </body>
    </html>
    """
    
    thread = threading.Thread(
        target=_send_email_sync,
        args=(subject, html_body, attachment_path),
        daemon=True
    )
    thread.start()
