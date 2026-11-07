import sys
sys.path.insert(0, '.')
from app.db.session import SessionLocal
from app.modules.platform.services.entitlements import _get_active_subscription
from sqlalchemy import select
from app.modules.platform.models import PlatformSubscription
import uuid

db = SessionLocal()
tid = uuid.UUID("840614ea-d3cf-4493-a111-f8cc4d4c4b23")
sub = _get_active_subscription(db, tid)
if sub is None:
    print("sub: None")
    rows = db.scalars(select(PlatformSubscription).where(PlatformSubscription.restaurant_id == tid)).all()
    for r in rows:
        print("any-sub:", str(r.id), "status=", r.status, "plan_version_id=", r.plan_version_id)
else:
    print("sub:", str(sub.id), "status=", sub.status, "plan_version_id=", sub.plan_version_id)
db.close()
