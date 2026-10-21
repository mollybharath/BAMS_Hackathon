import pandas as pd

def demo_transactions():
    # Entirely fictional, deterministic scenario matching the proposal.
    rows = [
        ("TXN-1001", "2026-10-20 09:00:00", "A-101", "A-201", 120000, "INR", "IMPS", "C-101"),
        ("TXN-1002", "2026-10-20 09:05:00", "A-102", "A-201", 110000, "INR", "IMPS", "C-102"),
        ("TXN-1003", "2026-10-20 09:11:00", "A-103", "A-201", 130000, "INR", "NEFT", "C-103"),
        ("TXN-1004", "2026-10-20 09:20:00", "A-104", "A-201", 120000, "INR", "IMPS", "C-104"),
        ("TXN-1005", "2026-10-20 09:27:00", "A-201", "A-301", 450000, "INR", "RTGS", "C-201"),
        # Background activity gives investigators context.
        ("TXN-1006", "2026-10-20 10:40:00", "A-401", "A-402", 8500, "INR", "UPI", "C-401"),
        ("TXN-1007", "2026-10-20 11:10:00", "A-402", "A-403", 2200, "INR", "UPI", "C-402"),
        ("TXN-1008", "2026-10-20 12:00:00", "A-501", "A-502", 15000, "INR", "NEFT", "C-501"),
    ]
    return pd.DataFrame(rows, columns=[
        "transaction_id", "timestamp", "source_account", "destination_account",
        "amount", "currency", "channel", "customer_id"
    ])
