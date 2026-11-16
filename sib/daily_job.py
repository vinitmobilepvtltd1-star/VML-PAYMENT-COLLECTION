"""SIB EDC daily statement job.
Gmail (IMAP) se pichle 30 ghante ke SIB statement mails padhta hai, PDF parse karta hai,
summary banakar usi Gmail se khud ko email karta hai (CSV attachment ke saath).

Env: GMAIL_USER, GMAIL_APP_PASSWORD   (App Password, normal password nahi)
Flags: --dry-run <pdf_dir>   (mail nahi padhta/bhejta, sirf local PDF se summary print karta hai)
"""
import csv, email, imaplib, io, os, pathlib, smtplib, sys, tempfile
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sib_parse import parse_pdf

SENDER = "SIB@edcstatements.com"
COLS = ["paid_date","mid","tid","rrn","batch","txn_date","txn_type","card",
        "txn_amount","msf","total_gst","net","file"]

def fetch_pdfs(user, pwd, outdir, hours=30):
    since = (datetime.now(timezone.utc) - timedelta(hours=hours))
    M = imaplib.IMAP4_SSL("imap.gmail.com")
    M.login(user, pwd)
    M.select('"[Gmail]/All Mail"', readonly=True)
    day = since.strftime("%d-%b-%Y")
    _, data = M.search(None, f'(FROM "{SENDER}" SINCE {day})')
    n = 0
    for num in data[0].split():
        _, msgdata = M.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(msgdata[0][1])
        when = email.utils.parsedate_to_datetime(msg["Date"])
        if when < since:
            continue
        for part in msg.walk():
            name = part.get_filename()
            if name and name.lower().endswith(".pdf"):
                (pathlib.Path(outdir) / name).write_bytes(part.get_payload(decode=True))
                n += 1
    M.logout()
    return n

def summarize(rows):
    if not rows:
        return "SIB: koi naya statement nahi mila."
    tot_amt = sum(r["txn_amount"] for r in rows)
    tot_net = sum(r["net"] for r in rows)
    fee = tot_amt - tot_net
    lines = [f"SIB EDC statements: {len(rows)} swipes, {len({r['mid'] for r in rows})} machines",
             f"Swipe total: Rs {tot_amt:,.2f}",
             f"Fee + GST kati: Rs {fee:,.2f}",
             f"Bank me net aaya: Rs {tot_net:,.2f}", ""]
    zero = [r for r in rows if r["txn_amount"] > 1 and r["msf"] == 0]
    if zero:
        lines.append("Dhyan do: in swipes par fee (MSF) zero lagi:")
        lines += [f"  {r['txn_date']} MID {r['mid']} Rs {r['txn_amount']:,.2f} ({r['card']})" for r in zero]
    return "\n".join(lines)

def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--dry-run":
        pdf_dir = sys.argv[2]
        rows = [r for p in sorted(pathlib.Path(pdf_dir).glob("*.pdf")) for r in parse_pdf(p)]
        print(summarize(rows)); return
    user, pwd = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"]
    with tempfile.TemporaryDirectory() as d:
        fetch_pdfs(user, pwd, d)
        rows = [r for p in sorted(pathlib.Path(d).glob("*.pdf")) for r in parse_pdf(p)]
    text = summarize(rows)
    print(text)
    msg = EmailMessage()
    msg["Subject"] = f"SIB daily statement summary {datetime.now().strftime('%d-%b-%Y')}"
    msg["From"] = user; msg["To"] = user
    msg.set_content(text)
    if rows:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=COLS); w.writeheader(); w.writerows(rows)
        msg.add_attachment(buf.getvalue().encode(), maintype="text", subtype="csv", filename="sib_swipes.csv")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pwd); s.send_message(msg)

if __name__ == "__main__":
    main()
