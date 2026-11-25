import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def main():
    gmail_user = os.environ["GMAIL_USER"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]
    gmail_to = os.getenv("GMAIL_TO", "").strip() or gmail_user

    status = json.loads(Path("data/latest_status.json").read_text(encoding="utf-8"))
    wechat_text = Path("data/wechat_text.txt").read_text(encoding="utf-8")
    html_path = Path(status["html_path"])

    tag = "" if status["published_to_homepage"] else "[内部核验稿-未满5条] "
    subject = f"{tag}【科技】全球科技产业观察 {status['issue_date_bj']}"

    body_parts = [wechat_text] if status["threshold_met"] else ["本期内部核验稿见附件。"]
    if not status["threshold_met"]:
        body_parts.append("\n" + "=" * 40)
        body_parts.append("【内部核验提示】以下站点未满 5 条（本次未覆盖正式首页）：")
        for s in status["shortfalls"]:
            body_parts.append(f"- {s}")
        if status.get("kouzhaoge_note"):
            body_parts.append(f"口罩哥索引状态：{status['kouzhaoge_note']}")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = gmail_to
    msg.set_content("\n".join(body_parts), charset="utf-8")

    # 同步附上单文件 HTML，方便微信拦截域名时直接转发文件
    msg.add_attachment(
        html_path.read_bytes(),
        maintype="text",
        subtype="html",
        filename=html_path.name if tag else f"全球科技产业观察_{status['issue_date_bj']}.html",
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_pass)
        smtp.send_message(msg)

    print(f"[send_email] Sent to {gmail_to}: {subject}")


if __name__ == "__main__":
    main()
