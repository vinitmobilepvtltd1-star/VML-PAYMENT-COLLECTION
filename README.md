# VML-PAYMENT-COLLECTION

Vinit Mobile card-machine settlement reconciliation code.

## sib/
- `sib_parse.py` : South Indian Bank EDC "Daily Statement" PDF parser (needs `pdftotext`).
  Usage: `python3 sib_parse.py <pdf_dir> <out_csv>`
  Output columns: paid_date, mid, tid, rrn, batch, txn_date, txn_type, card, txn_amount, msf, total_gst, net.
- Tested 16 Nov 2026 on 9 statements (12-13 Nov): 15 rows, net total 366993.90.

## Rules
- This repo is PUBLIC. Never commit statement PDFs, CSVs, card numbers or any credentials.
- Next step: daily job (Render) that reads the SIB statement mails and runs the parser.
