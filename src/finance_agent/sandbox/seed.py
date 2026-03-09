"""Algorithmic synthetic data generator — pushes seed data to Salesforce."""

from __future__ import annotations

import random
from datetime import date, timedelta

from simple_salesforce import Salesforce

from finance_agent.sandbox.storage import add_client, add_interaction

# ---------------------------------------------------------------------------
# Name & occupation pools
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "James",
    "Mary",
    "Robert",
    "Patricia",
    "John",
    "Jennifer",
    "Michael",
    "Linda",
    "David",
    "Elizabeth",
    "William",
    "Barbara",
    "Richard",
    "Susan",
    "Joseph",
    "Jessica",
    "Thomas",
    "Sarah",
    "Charles",
    "Karen",
    "Christopher",
    "Lisa",
    "Daniel",
    "Nancy",
    "Matthew",
    "Betty",
    "Anthony",
    "Margaret",
    "Mark",
    "Sandra",
    "Donald",
    "Ashley",
    "Steven",
    "Dorothy",
    "Paul",
    "Kimberly",
    "Andrew",
    "Emily",
    "Joshua",
    "Donna",
    "Kenneth",
    "Michelle",
    "Kevin",
    "Carol",
    "Brian",
    "Amanda",
    "George",
    "Melissa",
    "Timothy",
    "Deborah",
    "Ronald",
    "Stephanie",
    "Edward",
    "Rebecca",
    "Jason",
    "Sharon",
    "Jeffrey",
    "Laura",
    "Ryan",
    "Cynthia",
    "Jacob",
    "Kathleen",
    "Gary",
    "Amy",
    "Nicholas",
    "Angela",
    "Eric",
    "Shirley",
    "Jonathan",
    "Anna",
    "Stephen",
    "Brenda",
    "Larry",
    "Pamela",
    "Justin",
    "Emma",
    "Scott",
    "Nicole",
    "Brandon",
    "Helen",
    "Benjamin",
    "Samantha",
    "Samuel",
    "Katherine",
    "Raymond",
    "Christine",
    "Gregory",
    "Debra",
    "Frank",
    "Rachel",
    "Alexander",
    "Carolyn",
    "Patrick",
    "Janet",
    "Jack",
    "Catherine",
    "Dennis",
    "Maria",
    "Jerry",
    "Heather",
]

LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
    "Ramirez",
    "Lewis",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Torres",
    "Nguyen",
    "Hill",
    "Flores",
    "Green",
    "Adams",
    "Nelson",
    "Baker",
    "Hall",
    "Rivera",
    "Campbell",
    "Mitchell",
    "Carter",
    "Roberts",
    "Gomez",
    "Phillips",
    "Evans",
    "Turner",
    "Diaz",
    "Parker",
    "Cruz",
    "Edwards",
    "Collins",
    "Reyes",
    "Stewart",
    "Morris",
    "Morales",
    "Murphy",
    "Cook",
    "Rogers",
    "Gutierrez",
    "Ortiz",
    "Morgan",
    "Cooper",
    "Peterson",
    "Bailey",
    "Reed",
    "Kelly",
    "Howard",
    "Ramos",
    "Kim",
    "Cox",
    "Ward",
    "Richardson",
    "Watson",
    "Brooks",
    "Chavez",
    "Wood",
    "James",
    "Bennett",
    "Gray",
    "Mendoza",
    "Ruiz",
    "Hughes",
    "Price",
    "Alvarez",
    "Castillo",
    "Sanders",
    "Patel",
    "Myers",
    "Long",
    "Ross",
    "Foster",
    "Jimenez",
]

OCCUPATIONS = [
    "Software Engineer",
    "Physician",
    "Attorney",
    "Business Owner",
    "Professor",
    "Dentist",
    "Pharmacist",
    "Architect",
    "Financial Analyst",
    "Marketing Director",
    "Sales Executive",
    "Real Estate Developer",
    "Consultant",
    "Nurse Practitioner",
    "Veterinarian",
    "Civil Engineer",
    "IT Director",
    "Operations Manager",
    "Portfolio Manager",
    "Pilot",
    "Surgeon",
    "Executive Vice President",
    "Chief Technology Officer",
    "Regional Manager",
    "Senior Partner",
    "Retired Military",
    "Retired Teacher",
    "Small Business Owner",
    "Investment Banker",
    "Corporate Counsel",
]

INVESTMENT_GOALS_BY_RISK = {
    "conservative": [
        "Capital preservation",
        "Stable income",
        "Wealth protection",
        "Fixed income focus",
        "Low-volatility portfolio",
    ],
    "moderate": [
        "Balanced growth and income",
        "College fund savings",
        "Retirement planning",
        "Diversified portfolio",
        "Steady wealth building",
    ],
    "growth": [
        "Long-term capital appreciation",
        "Technology sector growth",
        "Aggressive growth with diversification",
        "Maximize total returns",
        "Growth-oriented ETF portfolio",
    ],
    "aggressive": [
        "Maximum growth",
        "Concentrated sector bets",
        "Options trading",
        "High-risk high-reward",
        "Startup and venture investments",
    ],
}

INTERACTION_TYPES = ["Call", "Meeting", "Email", "Other"]

INTERACTION_SUMMARIES = [
    "Discussed portfolio allocation and rebalancing",
    "Annual financial review — updated investment goals",
    "Reviewed quarterly performance report",
    "Addressed questions about market volatility",
    "Discussed tax-loss harvesting opportunities",
    "Updated beneficiary information",
    "Reviewed insurance coverage needs",
    "Discussed retirement timeline and income planning",
    "Introduced new investment options",
    "Follow-up on account transfer request",
    "Estate planning discussion with family",
    "Reviewed risk tolerance after market correction",
    "Discussed college savings 529 plan options",
    "Onboarding call — established investment policy",
    "Checked in after major market event",
]

HOUSEHOLD_TEMPLATES = [
    None,
    '["Spouse"]',
    '["Spouse", "Child (12)"]',
    '["Spouse", "Child (8)", "Child (15)"]',
    '["Partner"]',
    '["Spouse", "Adult child"]',
]

NOTES_TEMPLATES = [
    "Prefers email communication over phone calls.",
    "Very detail-oriented, likes to see charts and data.",
    "Interested in ESG/sustainable investing.",
    "Concerned about inflation impact on fixed income.",
    "Recently received inheritance, needs allocation advice.",
    "Active trader, wants to discuss options strategies.",
    "Planning to sell business within 5 years.",
    "Relocating to a new state — needs tax planning.",
    "Wants to establish charitable giving strategy.",
    "First-generation wealth builder, values education.",
    None,
    None,
    None,
]


# ---------------------------------------------------------------------------
# Risk tolerance & life stage weights
# ---------------------------------------------------------------------------

RISK_WEIGHTS = {
    "conservative": 0.15,
    "moderate": 0.35,
    "growth": 0.35,
    "aggressive": 0.15,
}

LIFE_STAGE_AGE_RANGES = {
    "accumulation": (25, 45),
    "pre-retirement": (46, 60),
    "retirement": (61, 75),
    "legacy": (76, 90),
}

LIFE_STAGE_WEIGHTS = {
    "accumulation": 0.30,
    "pre-retirement": 0.30,
    "retirement": 0.25,
    "legacy": 0.15,
}


def _weighted_choice(weights: dict[str, float], rng: random.Random) -> str:
    """Pick a key from a {key: weight} dict using weighted random selection."""
    keys = list(weights.keys())
    vals = list(weights.values())
    return rng.choices(keys, weights=vals, k=1)[0]


def _generate_client(rng: random.Random) -> dict:
    """Generate a single synthetic client profile."""
    first = rng.choice(FIRST_NAMES)
    last = rng.choice(LAST_NAMES)

    life_stage = _weighted_choice(LIFE_STAGE_WEIGHTS, rng)
    age_min, age_max = LIFE_STAGE_AGE_RANGES[life_stage]
    age = rng.randint(age_min, age_max)

    risk = _weighted_choice(RISK_WEIGHTS, rng)

    # Log-normal distribution for account values, clipped to $50K-$5M
    raw_value = rng.lognormvariate(mu=12.2, sigma=1.0)
    account_value = round(max(50_000, min(5_000_000, raw_value)), 2)

    goals = rng.choice(INVESTMENT_GOALS_BY_RISK[risk])
    occupation = rng.choice(OCCUPATIONS)
    household = rng.choice(HOUSEHOLD_TEMPLATES)
    notes = rng.choice(NOTES_TEMPLATES)

    email = f"{first.lower()}.{last.lower()}@example.com"
    phone = f"555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}"

    return {
        "first_name": first,
        "last_name": last,
        "age": age,
        "occupation": occupation,
        "email": email,
        "phone": phone,
        "account_value": account_value,
        "risk_tolerance": risk,
        "investment_goals": goals,
        "life_stage": life_stage,
        "household_members": household,
        "notes": notes,
    }


def _generate_interactions(rng: random.Random, count: int) -> list[dict]:
    """Generate a list of synthetic interactions."""
    interactions = []
    base_date = date.today() - timedelta(days=365)

    for _ in range(count):
        day_offset = rng.randint(0, 365)
        int_date = base_date + timedelta(days=day_offset)

        interactions.append(
            {
                "interaction_date": int_date.isoformat(),
                "interaction_type": rng.choice(INTERACTION_TYPES),
                "summary": rng.choice(INTERACTION_SUMMARIES),
            }
        )

    return sorted(interactions, key=lambda x: x["interaction_date"])


def seed_clients(
    sf: Salesforce,
    count: int = 50,
    seed: int | None = None,
) -> int:
    """Generate and push synthetic client profiles to Salesforce.

    Returns number of clients created.
    """
    rng = random.Random(seed)
    created = 0

    for _ in range(count):
        client_data = _generate_client(rng)
        client_id = add_client(sf, client_data)

        num_interactions = rng.randint(1, 5)
        for interaction in _generate_interactions(rng, num_interactions):
            add_interaction(sf, client_id, interaction)

        created += 1

    return created


def reset_sandbox(sf: Salesforce) -> None:
    """Delete all sandbox Contacts (those with @example.com email) and their Tasks."""
    # Find sandbox contacts
    result = sf.query("SELECT Id FROM Contact WHERE Email LIKE '%@example.com'")
    contact_ids = [r["Id"] for r in result.get("records", [])]

    if not contact_ids:
        return

    # Delete related Tasks first
    ids_str = "','".join(contact_ids)
    tasks = sf.query(f"SELECT Id FROM Task WHERE WhoId IN ('{ids_str}')")
    for t in tasks.get("records", []):
        sf.Task.delete(t["Id"])

    # Delete Contacts
    for cid in contact_ids:
        sf.Contact.delete(cid)
