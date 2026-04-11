"""
Knowledge base for the AI support agent.
Static FAQ + product docs. Swap chunks into a vector DB (Chroma/Weaviate) later.
"""

from typing import Any

FAQ: list[dict[str, Any]] = [
    {
        "id": "bank_connect",
        "keywords": [
            "bank",
            "connect",
            "open banking",
            "link",
            "add bank",
            "plaid",
            "starling",
            "monzo",
            "barclays",
        ],
        "question": "How do I connect my bank account?",
        "answer": (
            "Go to **Dashboard → Bank Connections**, click **Add Bank**, and follow the secure Open Banking flow. "
            "Supported banks include Barclays, HSBC, Lloyds, Monzo, Starling, and 40+ more. "
            "The connection is read-only — SelfMonitor can never move money on your behalf."
        ),
    },
    {
        "id": "cancel",
        "keywords": [
            "cancel",
            "cancellation",
            "subscription",
            "stop",
            "unsubscribe",
            "quit",
        ],
        "answer": (
            "Go to **Billing → Your Plan → Cancel Subscription**. "
            "You keep full access until the end of your billing period. No hidden fees or penalties."
        ),
        "question": "How do I cancel my subscription?",
    },
    {
        "id": "security",
        "keywords": [
            "security",
            "safe",
            "secure",
            "encrypt",
            "data",
            "privacy",
            "gdpr",
            "hack",
        ],
        "question": "Is my financial data secure?",
        "answer": (
            "All data is encrypted with **AES-256** at rest and in transit (TLS 1.3). "
            "We store data exclusively in **UK data centres** and are fully GDPR compliant. "
            "We are FCA-registered and never sell your data to third parties."
        ),
    },
    {
        "id": "hmrc",
        "keywords": [
            "hmrc",
            "tax",
            "self assessment",
            "mtd",
            "submit",
            "return",
            "filing",
        ],
        "question": "How does HMRC auto-submission work?",
        "answer": (
            "On **Pro and Business plans**, SelfMonitor submits your Self Assessment"
            " return directly to HMRC via the MTD API. "
            "You always review and **approve before anything is sent**"
            " — we never submit without your explicit confirmation."
        ),
    },
    {
        "id": "export",
        "keywords": ["export", "csv", "pdf", "xero", "quickbooks", "download", "data"],
        "question": "Can I export my data?",
        "answer": (
            "Yes — go to **Reports → Export CSV / PDF**. "
            "You can also push invoices directly to Xero and QuickBooks from the Invoices page. "
            "Your data always belongs to you."
        ),
    },
    {
        "id": "trial",
        "keywords": ["trial", "free", "14 days", "expire", "plan", "billing"],
        "question": "What happens when my free trial ends?",
        "answer": (
            "After 14 days your account switches to the **Free plan** automatically"
            " — no charge unless you entered payment details. "
            "You can upgrade anytime from the **Billing** page."
            " All your data is preserved."
        ),
    },
    {
        "id": "invoice",
        "keywords": [
            "invoice",
            "invoicing",
            "bill client",
            "send invoice",
            "vat",
            "receipt",
        ],
        "question": "How do invoices work?",
        "answer": (
            "Go to **Invoices → New Invoice**, fill in client details, add line items, and hit Send. "
            "SelfMonitor generates a professional PDF and emails it automatically. "
            "You can track payment status and send reminders. VAT-inclusive invoices are supported."
        ),
    },
    {
        "id": "pricing",
        "keywords": [
            "price",
            "pricing",
            "cost",
            "plan",
            "starter",
            "growth",
            "pro",
            "business",
            "cheap",
            "upgrade",
        ],
        "question": "What are the pricing plans?",
        "answer": (
            "We have 5 plans:\n"
            "- **Free** — basic tracking, no card needed\n"
            "- **Starter £15/mo ex VAT** — bank sync + core tax tools\n"
            "- **Growth £18/mo ex VAT** — + higher limits, invoices & forecasting\n"
            "- **Pro £21/mo ex VAT** — + HMRC MTD, AI assistant, API\n"
            "- **Business £30/mo ex VAT** — team seats, marketplace, white-label\n\n"
            "All paid plans include a 14-day free trial."
        ),
    },
    {
        "id": "password",
        "keywords": [
            "password",
            "forgot",
            "reset",
            "login",
            "sign in",
            "access",
            "locked",
        ],
        "question": "I forgot my password / can't log in.",
        "answer": (
            "Click **Forgot password** on the login page and enter your email. "
            "You'll receive a reset link within 2 minutes (check spam). "
            "If you still can't access your account, create a support ticket below"
            " and we'll help within 1 business day."
        ),
    },
    {
        "id": "team",
        "keywords": [
            "team",
            "invite",
            "member",
            "colleague",
            "accountant",
            "business plan",
        ],
        "question": "How do I invite a team member?",
        "answer": (
            "Team members are available on the **Business plan**. "
            "Go to **Profile → Team Members → Invite**, enter their email, and set their permissions. "
            "They'll receive a secure sign-up link."
        ),
    },
]

GREETINGS = [
    "hello",
    "hi",
    "hey",
    "hiya",
    "good morning",
    "good afternoon",
]
THANKS = ["thanks", "thank you", "thx", "cheers"]
GOODBYES = ["bye", "goodbye", "cya", "see you"]


def search_kb(query: str, top_k: int = 2) -> list[dict[str, Any]]:
    """Simple keyword-based retrieval. Replace with vector search later."""
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in FAQ:
        score = sum(1 for kw in item["keywords"] if kw in q)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]
