import sys

from scripts.run_provider_governance_gate import main

if __name__ == "__main__":
    sys.exit(main(["--profile", "enterprise", "--json"]))
