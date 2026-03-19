#!/usr/bin/env python3
"""Send the daily scores report as email."""

import os, argparse, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path


def send(file_path, date):
    sender   = os.environ["MAIL_SENDER"]
    password = os.environ["MAIL_PASSWORD"]
    receiver = os.environ["MAIL_RECEIVER"]

    body = Path(file_path).read_text(encoding="utf-8")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 今日热帖简报 · {date}"
    msg["From"]    = sender
    msg["To"]      = receiver
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(sender, password)
        s.sendmail(sender, receiver, msg.as_string())

    print(f"✓ 邮件已发送 → {receiver}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()
    send(args.file, args.date)


if __name__ == "__main__":
    main()
