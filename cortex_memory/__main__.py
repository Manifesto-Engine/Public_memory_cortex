"""Allow running dashboard as: python -m cortex_memory [db_path]"""
import sys
from cortex_memory.dashboard import run_dashboard

if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "/tmp/cortex_dashboard.db"
    print(f"Launching Cortex Dashboard → {db}")
    print("Press 'q' to exit.\n")
    run_dashboard(db)
