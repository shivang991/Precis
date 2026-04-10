## Python Import Rules (`packages/api/app`)

### Rule 1: Same-domain imports must use relative paths

When importing from a module in the same domain, always use relative imports.

```python
# Bad
from app.highlights.models import Highlight

# Good
from .models import Highlight
```

### Rule 2: Cross-domain imports must go through the domain boundary (`__init__.py`)

When importing from another domain, first expose the symbol in that domain's `__init__.py`, then import from the package — never from a submodule path.

```python
# Bad
from app.users.models import User
from app.document_content_tree.service import DocumentContentTreeService

# Good — after exposing in users/__init__.py and document_content_tree/__init__.py
from app.users import User
from app.document_content_tree import DocumentContentTreeService
```

### Exceptions (circular-import safety)

The following fully-qualified submodule imports are intentional and must not be changed:

- `models.py` files importing `from app.shared.database import Base`
- `errors.py` files importing `from app.shared.domain_error import DomainError`
- `users/dependencies.py` importing `from app.shared.database import get_db`

The first two bypass `shared/__init__.py` to avoid triggering its full import chain during model registration. The last one bypasses `shared/__init__.py` for the same reason — `users/dependencies.py` is loaded by `users/__init__.py`, which could create a circular chain if it imported through the `app.shared` boundary.
