"""Last owned child: audit saved files only, then let runner seal after exit."""
import json
from verify import audit
print(json.dumps(audit(False)))
