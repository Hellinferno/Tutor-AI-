from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from .models import MeteredAction, Plan, PlanTier, Subscription, UsageRecord, utc_now
from .store import InMemoryStudyLabStore


# Deterministic plan catalog. Prices are integer cents. A quota of ``None`` is
# unlimited. These are product defaults; real catalogs would live in the billing
# provider, but keeping them here makes quota enforcement testable offline.
PLAN_CATALOG: dict[PlanTier, Plan] = {
    "free": Plan(
        tier="free",
        name="Free",
        price_cents=0,
        currency="usd",
        quotas={
            "ask": 50,
            "solve": 50,
            "quiz": 10,
            "paper": 5,
            "artifact": 10,
            "source_import": 5,
            "teaching": 10,
        },
        features=[
            "1 active notebook focus",
            "Verified solver + cited answers",
            "Quizzes, papers, revision",
        ],
    ),
    "scholar": Plan(
        tier="scholar",
        name="Scholar",
        price_cents=900,
        currency="usd",
        quotas={
            "ask": 1000,
            "solve": 1000,
            "quiz": 200,
            "paper": 100,
            "artifact": 200,
            "source_import": 100,
            "teaching": 200,
        },
        features=[
            "Everything in Free",
            "Website / YouTube / Docs connectors",
            "Multi-agent teaching",
            "Voice tutor (with API key)",
        ],
    ),
    "pro": Plan(
        tier="pro",
        name="Pro",
        price_cents=2900,
        currency="usd",
        quotas={
            "ask": None,
            "solve": None,
            "quiz": None,
            "paper": None,
            "artifact": None,
            "source_import": None,
            "teaching": None,
        },
        features=[
            "Everything in Scholar",
            "Unlimited usage",
            "Priority compute",
            "Team-ready (seat billing seam)",
        ],
    ),
}

DEFAULT_TIER: PlanTier = "free"


class QuotaExceededError(Exception):
    """Raised when a metered action would exceed the user's plan quota.

    Carries the quota detail so the HTTP layer can return a 402 with context.
    """

    def __init__(self, detail: dict[str, Any]) -> None:
        self.detail = detail
        action = detail.get("action")
        limit = detail.get("limit")
        super().__init__(f"Quota exceeded for '{action}' ({detail.get('used')}/{limit} this period). Upgrade your plan.")


def current_billing_period() -> str:
    """Return the UTC billing period as ``YYYY-MM``."""
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


class BillingProvider(ABC):
    """Seam for a real payment processor (Stripe, etc.).

    The mock provider activates a plan immediately so the product is fully usable
    offline. A real provider would return a hosted-checkout URL and only flip the
    subscription to ``active`` on a verified webhook.
    """

    name = "mock"

    @abstractmethod
    def start_checkout(self, user_id: str, plan: Plan) -> dict[str, Any]:
        ...


class MockBillingProvider(BillingProvider):
    name = "mock"

    def start_checkout(self, user_id: str, plan: Plan) -> dict[str, Any]:
        # Free plan needs no payment; paid plans auto-activate in mock mode.
        return {
            "provider": "mock",
            "status": "active",
            "checkout_url": None,
            "external_id": f"mock_sub_{user_id}_{plan.tier}",
            "message": (
                "Free plan active."
                if plan.price_cents == 0
                else f"Mock checkout: {plan.name} activated (${plan.price_cents / 100:.2f}/mo)."
            ),
        }


class StripeBillingProvider(BillingProvider):
    """Env-gated real billing path. Requires STRIPE_API_KEY and the ``stripe`` SDK.

    Kept as a thin seam: it builds a Checkout Session and leaves the subscription
    in ``past_due`` (pending) until a webhook confirms payment.
    """

    name = "stripe"

    def __init__(self) -> None:
        api_key = os.getenv("STRIPE_API_KEY")
        if not api_key:
            raise RuntimeError("STRIPE_API_KEY not set")
        import stripe  # type: ignore

        stripe.api_key = api_key
        self._stripe = stripe
        self._success_url = os.getenv("STRIPE_SUCCESS_URL", "https://example.com/billing/success")
        self._cancel_url = os.getenv("STRIPE_CANCEL_URL", "https://example.com/billing/cancel")

    def start_checkout(self, user_id: str, plan: Plan) -> dict[str, Any]:
        if plan.price_cents == 0:
            return {"provider": "stripe", "status": "active", "checkout_url": None, "external_id": None,
                    "message": "Free plan active."}
        session = self._stripe.checkout.Session.create(
            mode="subscription",
            client_reference_id=user_id,
            success_url=self._success_url,
            cancel_url=self._cancel_url,
            line_items=[{
                "quantity": 1,
                "price_data": {
                    "currency": plan.currency,
                    "recurring": {"interval": "month"},
                    "unit_amount": plan.price_cents,
                    "product_data": {"name": f"StudyLab {plan.name}"},
                },
            }],
        )
        return {
            "provider": "stripe",
            "status": "past_due",  # pending until webhook confirms
            "checkout_url": session.url,
            "external_id": session.id,
            "message": "Complete checkout to activate your plan.",
        }


def make_billing_provider() -> BillingProvider:
    if os.getenv("STRIPE_API_KEY"):
        try:
            return StripeBillingProvider()
        except Exception:
            pass
    return MockBillingProvider()


class PricingEngine:
    """Deterministic plans, subscriptions, usage metering, and quota checks.

    Usage is metered per (user, action, billing period). Quotas come from the plan
    catalog. Metering is non-blocking by design: ``meter`` always records, and
    ``check_quota`` reports remaining allowance so callers/UI can react. Real
    payment goes through the env-gated billing provider.
    """

    def __init__(self, store: InMemoryStudyLabStore, billing: BillingProvider | None = None) -> None:
        self.store = store
        self.billing = billing or make_billing_provider()

    def list_plans(self) -> list[Plan]:
        return list(PLAN_CATALOG.values())

    def get_plan(self, tier: PlanTier) -> Plan:
        if tier not in PLAN_CATALOG:
            raise ValueError(f"Unknown plan tier: {tier}")
        return PLAN_CATALOG[tier]

    def get_subscription(self, user_id: str) -> Subscription:
        """Return the user's subscription, creating a default Free one on first read."""
        existing = self.store.subscription_for(user_id)
        if existing:
            return existing
        subscription = Subscription(
            id=self.store.next_id("sub"),
            user_id=user_id,
            tier=DEFAULT_TIER,
            status="active",
            billing_period=current_billing_period(),
            provider=self.billing.name,
        )
        return self.store.add_subscription(subscription)

    def set_plan(self, user_id: str, tier: PlanTier) -> dict[str, Any]:
        """Change a user's plan via the billing provider, persisting the result."""
        plan = self.get_plan(tier)
        checkout = self.billing.start_checkout(user_id, plan)
        subscription = self.get_subscription(user_id)
        subscription.tier = tier
        subscription.status = checkout.get("status", "active")
        subscription.provider = checkout.get("provider", self.billing.name)
        subscription.external_id = checkout.get("external_id")
        subscription.billing_period = current_billing_period()
        subscription.updated_at = utc_now()
        self.store.save_subscription(subscription)
        return {"subscription": subscription, "checkout": checkout, "plan": plan}

    def enforce(self, user_id: str, action: MeteredAction, quantity: int = 1) -> UsageRecord:
        """Check the quota, then meter. Raises QuotaExceededError if over the limit.

        This is the *enforcing* counterpart to ``meter`` (which only records). The
        gateway uses it when ``STUDYLAB_ENFORCE_QUOTAS`` is enabled so plans gate
        real usage; offline/test flows keep using non-blocking ``meter``.
        """
        quota = self.check_quota(user_id, action)
        if not quota["allowed"]:
            raise QuotaExceededError(quota)
        return self.meter(user_id, action, quantity)

    def meter(self, user_id: str, action: MeteredAction, quantity: int = 1) -> UsageRecord:
        record = UsageRecord(
            id=self.store.next_id("usage"),
            user_id=user_id,
            action=action,
            billing_period=current_billing_period(),
            quantity=quantity,
        )
        return self.store.add_usage_record(record)

    def usage_count(self, user_id: str, action: MeteredAction, billing_period: str | None = None) -> int:
        period = billing_period or current_billing_period()
        return sum(
            r.quantity for r in self.store.usage_for_period(user_id, period) if r.action == action
        )

    def check_quota(self, user_id: str, action: MeteredAction) -> dict[str, Any]:
        subscription = self.get_subscription(user_id)
        plan = self.get_plan(subscription.tier)
        limit = plan.quotas.get(action)
        used = self.usage_count(user_id, action, subscription.billing_period)
        if limit is None:
            return {"action": action, "used": used, "limit": None, "remaining": None, "allowed": True}
        remaining = max(0, limit - used)
        return {
            "action": action,
            "used": used,
            "limit": limit,
            "remaining": remaining,
            "allowed": remaining > 0,
        }

    def usage_summary(self, user_id: str) -> dict[str, Any]:
        subscription = self.get_subscription(user_id)
        plan = self.get_plan(subscription.tier)
        actions = [self.check_quota(user_id, action) for action in plan.quotas]  # type: ignore[arg-type]
        return {
            "user_id": user_id,
            "tier": subscription.tier,
            "status": subscription.status,
            "billing_period": subscription.billing_period,
            "provider": subscription.provider,
            "price_cents": plan.price_cents,
            "currency": plan.currency,
            "actions": actions,
        }
