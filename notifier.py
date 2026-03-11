"""
Email notification system — sends deal alerts via SMTP.
"""

import logging
import smtplib
import socket
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from analyzer import DealResult
from config import Config

logger = logging.getLogger(__name__)


def _build_html_report(deals: list[DealResult]) -> str:
    """Build a nice HTML email body from deal results."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    rows = ""
    for deal in deals:
        color = "#2ecc71" if deal.score >= 85 else "#f39c12" if deal.score >= 70 else "#e74c3c"
        signals_html = "<br>".join(
            f"{'&#9989;' if s.bullish else '&#10060;'} {s.detail}"
            for s in deal.signals
        )
        rows += f"""
        <tr>
            <td style="padding:10px; border-bottom:1px solid #ddd;"><strong>{deal.ticker}</strong></td>
            <td style="padding:10px; border-bottom:1px solid #ddd;">{deal.current_price:.2f} EGP</td>
            <td style="padding:10px; border-bottom:1px solid #ddd;">
                <span style="color:{color}; font-weight:bold; font-size:18px;">{deal.score:.0f}/100</span>
            </td>
            <td style="padding:10px; border-bottom:1px solid #ddd;">
                <span style="color:{color}; font-weight:bold;">{deal.recommendation}</span>
            </td>
            <td style="padding:10px; border-bottom:1px solid #ddd; font-size:12px;">{signals_html}</td>
        </tr>
        """

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
        <div style="max-width: 900px; margin: auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #2c3e50;">&#128200; Thndr Deal Alert</h1>
            <p style="color: #7f8c8d;">Scan completed at <strong>{now}</strong></p>
            <p>Found <strong>{len(deals)}</strong> potential deal(s) scoring above <strong>{Config.MIN_DEAL_SCORE}</strong>:</p>

            <table style="width:100%; border-collapse: collapse; margin-top: 15px;">
                <tr style="background: #34495e; color: white;">
                    <th style="padding:10px; text-align:left;">Ticker</th>
                    <th style="padding:10px; text-align:left;">Price</th>
                    <th style="padding:10px; text-align:left;">Score</th>
                    <th style="padding:10px; text-align:left;">Recommendation</th>
                    <th style="padding:10px; text-align:left;">Signals</th>
                </tr>
                {rows}
            </table>

            <p style="margin-top:20px; color:#95a5a6; font-size:12px;">
                &#9888; This is an automated analysis — not financial advice. Always do your own research.
            </p>
        </div>
    </body>
    </html>
    """
    return html


def send_deal_alert(deals: list[DealResult]) -> bool:
    """Send an email alert with the top deals."""
    if not deals:
        logger.info("No deals to report — skipping email.")
        return False

    sender = Config.EMAIL_SENDER
    password = Config.EMAIL_PASSWORD
    receiver = Config.EMAIL_RECEIVER
    smtp_server = Config.SMTP_SERVER
    smtp_port = Config.SMTP_PORT

    logger.info(f"Email config: sender={sender}, receiver={receiver}, server={smtp_server}:{smtp_port}")

    if not sender or not password:
        logger.error(f"Email credentials missing! sender='{sender}', password={'SET' if password else 'EMPTY'}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Thndr Bot - {len(deals)} Deal(s) Found! ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    msg["From"] = sender
    msg["To"] = receiver

    # Plain text fallback
    plain = "Thndr Deal Alert\n\n"
    for deal in deals:
        plain += f"{deal.ticker}: Score={deal.score:.0f}/100 | {deal.recommendation} | Price={deal.current_price:.2f} EGP\n"
        for s in deal.signals:
            plain += f"  {'✅' if s.bullish else '❌'} {s.detail}\n"
        plain += "\n"
    plain += "\n⚠️ Not financial advice."

    html = _build_html_report(deals)

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        # Force IPv4 resolution to avoid "Network is unreachable" on cloud platforms
        addr_info = socket.getaddrinfo(smtp_server, smtp_port, socket.AF_INET)
        ipv4_addr = addr_info[0][4][0]
        logger.info(f"Resolved {smtp_server} -> {ipv4_addr}")

        # Use SSL on port 465 (more reliable on cloud), fallback to STARTTLS on 587
        if smtp_port == 465:
            logger.info(f"Connecting via SMTP_SSL to {ipv4_addr}:{smtp_port}...")
            with smtplib.SMTP_SSL(ipv4_addr, smtp_port, timeout=30) as server:
                logger.info("SSL connected, logging in...")
                server.login(sender, password)
                logger.info("Login OK, sending email...")
                server.sendmail(sender, receiver, msg.as_string())
        else:
            logger.info(f"Connecting via STARTTLS to {ipv4_addr}:{smtp_port}...")
            with smtplib.SMTP(ipv4_addr, smtp_port, timeout=30) as server:
                server.starttls()
                logger.info("STARTTLS OK, logging in...")
                server.login(sender, password)
                logger.info("Login OK, sending email...")
                server.sendmail(sender, receiver, msg.as_string())
        logger.info(f"Deal alert email sent to {receiver}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}", exc_info=True)
        return False
