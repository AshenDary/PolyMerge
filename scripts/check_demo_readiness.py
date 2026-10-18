"""Check read-only preflight or the running launcher-owned demo stack."""
import sys
from local_demo import main

if __name__ == '__main__':
    sys.argv.insert(1, 'check')
    raise SystemExit(main())
