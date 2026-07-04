"""Allow running CLI as: python -m src.cli"""

import sys
from .main import main

sys.exit(main())
