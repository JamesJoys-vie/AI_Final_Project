import sys
from pathlib import Path

if __package__ in (None, ""):  # `python task2_tank_battle` (the folder itself), not `python -m task2_tank_battle`
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from task2_tank_battle.main import main  # noqa: E402  (import after the path set-up above)

main()
