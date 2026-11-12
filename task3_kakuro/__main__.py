import sys
from pathlib import Path

if __package__ in (None, ""):  # `python task3_kakuro` (the folder itself), not `python -m task3_kakuro`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from task3_kakuro.main import main  # noqa: E402  (import after the path set-up above)

main()
