"""SIB EDC daily statement PDF parser.
Usage: python3 sib_parse.py <pdf_dir> <out_csv>
Har PDF se har transaction ki row nikalta hai (MID, TID, txn date, amount, MSF, GST, net).
Zarurat: poppler-utils (pdftotext).
"""
import csv, re, subprocess, sys, pathlib

ROW = re.compile(
    r"^\s*(\d+)\s+(\d{4}-\d{2}-\d{2})\s+(\w+)\s+(\w+)\s+(\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s+(\d+)\s+"
    r"(\d{2}-[A-Z]{3}-\d{4})\s+(SALE|REFUND|VOID)\s+(CREDIT|DEBIT)\s+(\w+)\s+(\w+)\s+([-\d.]+)\s+INR\s+(.*)$"
)
NUM = re.compile(r"-?\d+(?:\.\d+)?")

def parse_pdf(path):
    text = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                          capture_output=True, text=True, check=True).stdout
    rows = []
    for line in text.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        g = m.groups()
        nums = NUM.findall(g[15])          # payment amt, [fx], MSF, IGST... NET
        net = float(nums[-1])
        gst = float(nums[-2]) if len(nums) >= 2 else 0.0
        msf = float(nums[2]) if len(nums) >= 12 else float(nums[1]) if len(nums) > 2 else 0.0
        rows.append({
            "paid_date": g[1], "mid": g[2], "tid": g[3], "rrn": g[6],
            "batch": g[8], "txn_date": g[9], "txn_type": g[10], "card": g[11],
            "txn_amount": float(g[14]), "msf": msf, "total_gst": gst, "net": net,
            "file": path.name,
        })
    return rows

def main(pdf_dir, out_csv):
    allrows = []
    for p in sorted(pathlib.Path(pdf_dir).glob("*.pdf")):
        allrows += parse_pdf(p)
    cols = ["paid_date","mid","tid","rrn","batch","txn_date","txn_type","card","txn_amount","msf","total_gst","net","file"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(allrows)
    print(len(allrows), "rows,", "net total:", round(sum(r["net"] for r in allrows), 2))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
