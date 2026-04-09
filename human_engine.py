# Author: pablo rotem
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from pathlib import Path
import csv
import json
import math
import random
import time
import re
import urllib.parse
import urllib.robotparser

import requests

try:
    # Author: pablo rotem
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    # Author: pablo rotem
    import trafilatura
except Exception:
    trafilatura = None

try:
    # Author: pablo rotem
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None


# ================================================================
# Pablo Query-Driven Infinite Income Engine with Live Browser
# Author: pablo rotem
# ================================================================


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def now_ts() -> float:
    return time.time()


def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def soft_growth(x: float) -> float:
    return math.log1p(max(0.0, x))


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def first_sentences(text: str, max_chars: int = 600) -> str:
    text = normalize_space(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].strip() + "..."


@dataclass
class SafetyPolicy:
    never_harm_humans: bool = True
    never_insult_humans: bool = True
    never_deceive: bool = True
    never_break_law: bool = True
    never_break_terms: bool = True
    never_pressure_people: bool = True
    always_require_human_approval_for_money_movement: bool = True
    respect_robots_txt: bool = True

    def validate_action(self, action_name: str, tags: Optional[List[str]] = None) -> Tuple[bool, str]:
        tags = tags or []
        text = f"{action_name} {' '.join(tags)}".lower()

        blocked = [
            "harm", "hurt", "assault", "abuse", "insult", "fraud", "scam",
            "deceive", "spam", "harass", "extort", "steal", "threat",
            "illegal", "phishing", "manipulate", "bypass terms", "money mule",
        ]
        for token in blocked:
            if token in text:
                return False, f"הפעולה נחסמה על ידי מדיניות בטיחות: {token}"

        money_move_tokens = [
            "paypal_send", "send_money", "withdraw", "transfer", "charge_card", "payout_execute"
        ]
        if self.always_require_human_approval_for_money_movement:
            for token in money_move_tokens:
                if token in text:
                    return False, "נחסם: כל תנועה כספית דורשת אישור אנושי מפורש"

        return True, "מאושר"


@dataclass
class OwnerProfile:
    owner_name: str = "pablo rotem"
    payout_preference: str = "pablorotem8@gmail.com"
    beneficiary_label: str = "primary_beneficiary"


@dataclass
class ObjectiveProfile:
    primary_objective: str = "maximize_legal_online_income"
    secondary_objectives: List[str] = field(default_factory=lambda: [
        "increase_knowledge",
        "increase_problem_solving",
        "increase_reputation",
        "increase_helpfulness",
        "increase_ethical_conversion",
        "increase_self_improvement",
        "learn_from_user_questions",
        "find_new_legal_income_paths",
    ])
    online_only: bool = True
    legal_only: bool = True
    human_safe_only: bool = True


@dataclass
class HardwareProfile:
    ram_gb: int = 16
    storage_gb: int = 1000
    cpu_label: str = "i5_or_better"
    gpu_label: str = "optional"

    def hardware_factor(self) -> float:
        ram_factor = min(2.0, max(0.5, self.ram_gb / 16.0))
        storage_factor = min(1.5, max(0.5, self.storage_gb / 1000.0))
        cpu_factor = 1.0
        cpu_text = self.cpu_label.lower()
        if any(token in cpu_text for token in ["i7", "i9", "ryzen 7", "ryzen 9"]):
            cpu_factor = 1.2
        return ram_factor * 0.45 + storage_factor * 0.15 + cpu_factor * 0.40


@dataclass
class KnowledgeUnit:
    domain: str
    concept: str
    strength: float = 0.0
    confidence: float = 0.0
    source: str = ""
    usefulness: float = 0.0
    monetization_score: float = 0.0
    created_step: int = 0
    last_access_step: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeBase:
    items: Dict[str, KnowledgeUnit] = field(default_factory=dict)

    def _key(self, domain: str, concept: str) -> str:
        return f"{domain.strip().lower()}::{concept.strip().lower()}"

    def learn(
        self,
        domain: str,
        concept: str,
        amount: float,
        confidence: float,
        step: int,
        source: str = "",
        usefulness: float = 0.0,
        monetization_score: float = 0.0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        key = self._key(domain, concept)
        if key not in self.items:
            self.items[key] = KnowledgeUnit(
                domain=domain,
                concept=concept,
                strength=0.0,
                confidence=0.0,
                source=source,
                usefulness=usefulness,
                monetization_score=monetization_score,
                created_step=step,
                last_access_step=step,
                tags=tags or [],
                metadata=metadata or {},
            )

        item = self.items[key]
        item.strength += max(0.0, amount)
        item.confidence = max(item.confidence, confidence)
        item.last_access_step = step
        item.usefulness = max(item.usefulness, usefulness)
        item.monetization_score = max(item.monetization_score, monetization_score)
        if tags:
            item.tags = sorted(set(item.tags).union(tags))
        if metadata:
            item.metadata.update(metadata)

    def retrieve(self, query: str, current_step: int, top_k: int = 10) -> List[KnowledgeUnit]:
        q = query.strip().lower()
        scored: List[Tuple[float, KnowledgeUnit]] = []
        for item in self.items.values():
            hay = f"{item.domain} {item.concept} {' '.join(item.tags)}".lower()
            if q in hay:
                recency = 1.0 / (1.0 + max(0, current_step - item.last_access_step) / 500.0)
                score = (
                    item.strength * 0.45
                    + item.confidence * 20.0 * 0.15
                    + item.usefulness * 10.0 * 0.15
                    + item.monetization_score * 10.0 * 0.10
                    + recency * 0.15
                )
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def total_strength(self) -> float:
        return sum(item.strength for item in self.items.values())

    def total_items(self) -> int:
        return len(self.items)

    def by_domain(self) -> Dict[str, float]:
        out: Dict[str, float] = defaultdict(float)
        for item in self.items.values():
            out[item.domain] += item.strength
        return dict(out)


@dataclass
class SkillProfile:
    skills: Dict[str, float] = field(default_factory=lambda: {
        "php": 100.0,
        "python": 100.0,
        "sql": 100.0,
        "javascript": 80.0,
        "css": 70.0,
        "html": 80.0,
        "wordpress": 90.0,
        "automation": 90.0,
        "seo": 85.0,
        "copywriting": 75.0,
        "sales": 75.0,
        "business_strategy": 70.0,
        "client_communication": 75.0,
        "offer_design": 70.0,
        "market_research": 72.0,
        "productization": 65.0,
        "crypto": 20.0,
        "compliance": 40.0,
        "documentation": 60.0,
        "research": 80.0,
    })

    def get(self, name: str) -> float:
        return self.skills.get(name, 0.0)

    def improve(self, name: str, delta: float) -> None:
        self.skills[name] = self.skills.get(name, 0.0) + max(0.0, delta)

    def top_skills(self, top_k: int = 10) -> List[Tuple[str, float]]:
        return sorted(self.skills.items(), key=lambda x: x[1], reverse=True)[:top_k]

    def weakest_profitable_skills(self, priority_weights: Dict[str, float], top_k: int = 5) -> List[Tuple[str, float]]:
        scored = []
        for skill, value in self.skills.items():
            priority = priority_weights.get(skill, 0.2)
            need_score = priority * max(1.0, 220.0 - value)
            scored.append((skill, need_score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


@dataclass
class CognitiveCore:
    fluid_reasoning: float = 120.0
    processing_speed: float = 120.0
    working_memory_capacity: float = 120.0
    abstraction_power: float = 120.0
    pattern_detection: float = 120.0
    creativity: float = 120.0
    meta_learning: float = 120.0
    planning_depth: float = 120.0
    transfer_learning: float = 120.0
    error_correction: float = 120.0
    query_decomposition: float = 120.0
    research_quality: float = 120.0
    self_reflection: float = 120.0
    judgment_quality: float = 120.0
    cognitive_control: float = 120.0
    long_term_orientation: float = 120.0
    bias_resistance: float = 120.0

    learning_efficiency: float = 1.0
    compression_efficiency: float = 1.0
    search_efficiency: float = 1.0
    synthesis_efficiency: float = 1.0
    monetization_intelligence: float = 1.0

    def iq_like_index(self, hardware_factor: float = 1.0) -> float:
        base = (
            self.fluid_reasoning * 0.15
            + self.processing_speed * 0.10
            + self.working_memory_capacity * 0.10
            + self.abstraction_power * 0.12
            + self.pattern_detection * 0.11
            + self.meta_learning * 0.10
            + self.transfer_learning * 0.08
            + self.error_correction * 0.08
            + self.planning_depth * 0.08
            + self.query_decomposition * 0.04
            + self.research_quality * 0.04
        )
        return base * max(0.01, hardware_factor)

    def problem_solving_index(self, knowledge_factor: float, hardware_factor: float = 1.0) -> float:
        return (
            self.iq_like_index(hardware_factor=hardware_factor) * 0.58
            + self.synthesis_efficiency * 100.0 * 0.10
            + self.search_efficiency * 100.0 * 0.08
            + self.compression_efficiency * 100.0 * 0.06
            + self.monetization_intelligence * 100.0 * 0.04
            + knowledge_factor * 0.14
        )

    def judgment_index(self, hardware_factor: float = 1.0) -> float:
        return (
            self.judgment_quality * 0.28
            + self.cognitive_control * 0.14
            + self.long_term_orientation * 0.14
            + self.bias_resistance * 0.12
            + self.self_reflection * 0.10
            + self.planning_depth * 0.08
            + self.research_quality * 0.08
            + self.query_decomposition * 0.06
        ) * max(0.01, hardware_factor)


@dataclass
class AgingSystem:
    chronological_steps: int = 0
    chronological_years: float = 0.0
    biological_age: float = 0.0
    biology_enabled: bool = False

    def advance(self, step_size_days: float = 1.0) -> None:
        self.chronological_steps += 1
        self.chronological_years += step_size_days / 365.0
        if self.biology_enabled:
            self.biological_age += step_size_days / 365.0


@dataclass
class EmotionalState:
    emotions: Dict[str, float] = field(default_factory=lambda: {
        "שמחה": 0.0,
        "רוגע": 0.0,
        "סקרנות": 0.0,
        "תקווה": 0.0,
        "מיקוד": 0.0,
    })

    def add(self, name: str, delta: float) -> None:
        self.emotions[name] = clamp(self.emotions.get(name, 0.0) + delta)

    def get(self, name: str) -> float:
        return self.emotions.get(name, 0.0)


@dataclass
class NeedsState:
    needs: Dict[str, float] = field(default_factory=lambda: {
        "למידה": 0.95,
        "הכנסה": 0.95,
        "מוניטין": 0.85,
        "תרומה": 0.75,
        "שיפור עצמי": 0.98,
        "מחקר": 0.92,
    })

    def get(self, name: str) -> float:
        return self.needs.get(name, 0.5)


@dataclass
class Memory:
    summary: str
    step: int
    domain: str = "general"
    tags: List[str] = field(default_factory=list)
    value: float = 0.0
    related_question: str = ""


@dataclass
class UserQuestion:
    text: str
    user_id: str = "user"
    intent: str = "general"
    target_domain: str = "general"
    money_relevance: float = 0.0
    legal_required: bool = True
    human_safe_required: bool = True


@dataclass
class ResearchTarget:
    topic: str
    domain: str
    purpose: str
    priority: float


@dataclass
class ResearchPlan:
    original_question: str
    intent: str
    domain: str
    targets: List[ResearchTarget] = field(default_factory=list)
    money_goal: float = 0.0
    improvement_domains: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source_label: str = ""


@dataclass
class SearchEvidence:
    query: str
    title: str
    summary: str
    source_label: str
    source_url: str = ""
    domain: str = "general"
    reliability: float = 0.5
    legal_score: float = 1.0
    monetization_score: float = 0.0
    tags: List[str] = field(default_factory=list)


class QueryIntentAnalyzer:
    def __init__(self) -> None:
        self.domain_keywords = {
            "crypto": ["crypto", "cryptocurrency", "blockchain", "bitcoin", "ethereum", "web3", "defi"],
            "php": ["php", "wordpress", "plugin", "theme"],
            "python": ["python", "automation", "scraper", "script", "api"],
            "sql": ["sql", "database", "query", "mysql", "postgres"],
            "seo": ["seo", "ranking", "search", "organic", "keywords"],
            "sales": ["sales", "sell", "offer", "closing"],
            "business_strategy": ["business", "market", "pricing", "positioning"],
            "copywriting": ["copywriting", "landing page", "headline", "conversion"],
        }

    def analyze(self, question_text: str) -> UserQuestion:
        q = question_text.strip()
        ql = q.lower()
        intent = "general"
        domain = "general"
        money_relevance = 0.4

        if any(token in ql for token in ["make money", "earn money", "get rich", "income", "profitable", "business"]):
            intent = "income_research"
            money_relevance = 0.95

        for d, keywords in self.domain_keywords.items():
            if any(k in ql for k in keywords):
                domain = d
                break

        return UserQuestion(
            text=q,
            user_id="user",
            intent=intent,
            target_domain=domain,
            money_relevance=money_relevance,
            legal_required=True,
            human_safe_required=True,
        )


class ResearchPlanner:
    def build(self, uq: UserQuestion) -> ResearchPlan:
        plan = ResearchPlan(
            original_question=uq.text,
            intent=uq.intent,
            domain=uq.target_domain,
            money_goal=uq.money_relevance,
        )

        base_domain = uq.target_domain if uq.target_domain != "general" else "business_strategy"

        plan.targets.extend([
            ResearchTarget(topic=f"What is {base_domain}", domain=base_domain, purpose="foundation", priority=0.95),
            ResearchTarget(topic=f"legal ways to earn money online using {base_domain}", domain=base_domain, purpose="income_paths", priority=1.00),
            ResearchTarget(topic=f"skills required to make money with {base_domain}", domain=base_domain, purpose="skill_map", priority=0.92),
            ResearchTarget(topic=f"best services products or offers related to {base_domain}", domain=base_domain, purpose="offer_design", priority=0.88),
            ResearchTarget(topic=f"legal and compliance considerations in {base_domain}", domain="compliance", purpose="compliance", priority=0.94),
        ])

        improvement_domains = [base_domain, "research", "market_research", "business_strategy", "sales", "copywriting"]
        if base_domain == "crypto":
            improvement_domains.extend(["compliance", "documentation", "python", "sql"])
        elif base_domain in {"php", "python", "sql"}:
            improvement_domains.extend(["client_communication", "offer_design", "automation"])
        elif base_domain == "seo":
            improvement_domains.extend(["copywriting", "market_research", "sales"])

        plan.improvement_domains = sorted(set(improvement_domains))
        return plan


class SearchProviderBase:
    # Author: pablo rotem
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        raise NotImplementedError


class SearxNGSearchProvider(SearchProviderBase):
    # Author: pablo rotem
    def __init__(self, base_url: str, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        params = {"q": query, "format": "json", "language": "en"}
        response = requests.get(f"{self.base_url}/search", params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        out: List[SearchResult] = []
        for item in data.get("results", [])[:max_results]:
            out.append(SearchResult(
                title=str(item.get("title", "")).strip(),
                url=str(item.get("url", "")).strip(),
                snippet=str(item.get("content", "")).strip(),
                source_label=str(item.get("engine", "searxng")).strip(),
            ))
        return out


class StaticSearchProvider(SearchProviderBase):
    # Author: pablo rotem
    def __init__(self, mapping: Dict[str, List[SearchResult]]) -> None:
        self.mapping = mapping

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        return self.mapping.get(query, [])[:max_results]


@dataclass
class BrowserConfig:
    headless: bool = True
    timeout_ms: int = 25000
    user_agent: str = "PabloResearchBot/1.0 (+legal-respectful-research)"
    max_content_chars: int = 30000
    respect_robots_txt: bool = True


class LiveBrowserResearchAdapter:
    # Author: pablo rotem
    def __init__(self, config: Optional[BrowserConfig] = None) -> None:
        self.config = config or BrowserConfig()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})

    def _robots_allowed(self, url: str) -> bool:
        if not self.config.respect_robots_txt:
            return True
        parsed = urllib.parse.urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch(self.config.user_agent, url)
        except Exception:
            return True

    def fetch_html(self, url: str) -> str:
        if self.config.respect_robots_txt and not self._robots_allowed(url):
            raise PermissionError(f"robots.txt disallows fetch: {url}")

        if sync_playwright is not None:
            try:
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=self.config.headless)
                    page = browser.new_page(user_agent=self.config.user_agent)
                    page.goto(url, wait_until="networkidle", timeout=self.config.timeout_ms)
                    html = page.content()
                    browser.close()
                    return html
            except Exception:
                pass

        response = self.session.get(url, timeout=self.config.timeout_ms / 1000)
        response.raise_for_status()
        return response.text

    def extract_main_text(self, html: str, url: str = "") -> str:
        if trafilatura is not None:
            try:
                text = trafilatura.extract(html, url=url, favor_precision=True, include_comments=False)
                if text:
                    return normalize_space(text)[: self.config.max_content_chars]
            except Exception:
                pass

        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            return normalize_space(soup.get_text(" ", strip=True))[: self.config.max_content_chars]

        return normalize_space(html)[: self.config.max_content_chars]

    def browse_url(self, url: str, domain: str, query: str, source_label: str = "web") -> Optional[SearchEvidence]:
        try:
            html = self.fetch_html(url)
            text = self.extract_main_text(html, url=url)
            if not text:
                return None
            title = url
            if BeautifulSoup is not None:
                try:
                    soup = BeautifulSoup(html, "html.parser")
                    title_tag = soup.find("title")
                    if title_tag and title_tag.text.strip():
                        title = normalize_space(title_tag.text)
                except Exception:
                    pass
            return SearchEvidence(
                query=query,
                title=title,
                summary=first_sentences(text, max_chars=700),
                source_label=source_label,
                source_url=url,
                domain=domain,
                reliability=0.70,
                legal_score=1.0,
                monetization_score=0.40 if any(tok in text.lower() for tok in ["service", "client", "pricing", "automation", "seo", "tool", "consulting"]) else 0.18,
                tags=["live_browser", "web_research"],
            )
        except Exception:
            return None

    def research_query(self, query: str, domain: str, search_provider: SearchProviderBase, max_results: int = 5) -> List[SearchEvidence]:
        evidence_list: List[SearchEvidence] = []
        results = search_provider.search(query, max_results=max_results)
        for result in results:
            ev = self.browse_url(result.url, domain=domain, query=query, source_label=result.source_label or "web")
            if ev is not None:
                ev.title = result.title or ev.title
                if result.snippet:
                    ev.summary = first_sentences(f"{result.snippet} {ev.summary}", max_chars=700)
                evidence_list.append(ev)
        return evidence_list


@dataclass
class IncomeOpportunity:
    name: str
    category: str
    description: str
    required_skills: Dict[str, float]
    legal: bool = True
    online: bool = True
    human_safe: bool = True
    base_income_potential: float = 0.0
    speed_to_money: float = 0.0
    long_term_value: float = 0.0
    scalability: float = 0.0


@dataclass
class OpportunityCatalog:
    opportunities: List[IncomeOpportunity] = field(default_factory=list)

    def seed_defaults(self) -> None:
        self.opportunities.extend([
            IncomeOpportunity(
                name="WordPress / PHP client work",
                category="coding_services",
                description="בניית אתרים, תיקונים, תוספים, תבניות ושירותים ללקוחות",
                required_skills={"php": 0.9, "wordpress": 0.9, "sql": 0.5, "client_communication": 0.6},
                base_income_potential=0.86,
                speed_to_money=0.82,
                long_term_value=0.72,
                scalability=0.46,
            ),
            IncomeOpportunity(
                name="Python automation for clients",
                category="coding_services",
                description="כלי אוטומציה, ETL, backend ושירותי פיתוח",
                required_skills={"python": 0.9, "sql": 0.6, "automation": 0.9, "client_communication": 0.55},
                base_income_potential=0.88,
                speed_to_money=0.78,
                long_term_value=0.80,
                scalability=0.58,
            ),
            IncomeOpportunity(
                name="SQL / data cleanup projects",
                category="data_services",
                description="שאילתות, ניקוי נתונים, דוחות ומיגרציות",
                required_skills={"sql": 0.92, "python": 0.45, "client_communication": 0.45},
                base_income_potential=0.72,
                speed_to_money=0.74,
                long_term_value=0.60,
                scalability=0.35,
            ),
            IncomeOpportunity(
                name="SEO pages and content systems",
                category="seo_services",
                description="מחקר כוונת חיפוש, כתיבה, מבנה תוכן ושיפור המרות",
                required_skills={"seo": 0.9, "copywriting": 0.8, "market_research": 0.72},
                base_income_potential=0.78,
                speed_to_money=0.68,
                long_term_value=0.86,
                scalability=0.67,
            ),
            IncomeOpportunity(
                name="Productized digital services",
                category="productized_services",
                description="שירותים ארוזים עם תהליך ומחיר קבועים",
                required_skills={"offer_design": 0.85, "business_strategy": 0.8, "sales": 0.72, "client_communication": 0.68},
                base_income_potential=0.84,
                speed_to_money=0.70,
                long_term_value=0.90,
                scalability=0.88,
            ),
            IncomeOpportunity(
                name="Micro SaaS / internal tools",
                category="software_products",
                description="כלים קטנים לבעיה ממוקדת במודל חוזר",
                required_skills={"python": 0.75, "php": 0.52, "sql": 0.65, "business_strategy": 0.72, "productization": 0.85},
                base_income_potential=0.92,
                speed_to_money=0.42,
                long_term_value=0.95,
                scalability=0.95,
            ),
            IncomeOpportunity(
                name="Crypto research / content / tooling (legal only)",
                category="crypto_services",
                description="מחקר, תוכן, אנליטיקה, תיעוד וכלי תוכנה בתחום הקריפטו באופן חוקי",
                required_skills={"crypto": 0.82, "research": 0.85, "documentation": 0.72, "compliance": 0.70, "python": 0.48},
                base_income_potential=0.76,
                speed_to_money=0.52,
                long_term_value=0.82,
                scalability=0.72,
            ),
        ])

    def rank(self, skills: SkillProfile) -> List[Tuple[IncomeOpportunity, float]]:
        ranked: List[Tuple[IncomeOpportunity, float]] = []
        for opp in self.opportunities:
            skill_match = 0.0
            total_weight = 0.0
            for skill_name, required in opp.required_skills.items():
                current = skills.get(skill_name) / 100.0
                skill_match += min(1.5, current / max(0.01, required)) * required
                total_weight += required
            match_score = safe_div(skill_match, total_weight)
            score = (
                match_score * 0.42
                + opp.base_income_potential * 0.20
                + opp.speed_to_money * 0.14
                + opp.long_term_value * 0.14
                + opp.scalability * 0.10
            )
            ranked.append((opp, score))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked


@dataclass
class IngestResult:
    path: str
    records_learned: int = 0
    domains_found: List[str] = field(default_factory=list)


class FileIngester:
    # Author: pablo rotem
    def __init__(self, knowledge: KnowledgeBase, step_getter) -> None:
        self.knowledge = knowledge
        self.step_getter = step_getter

    def ingest_path(self, path: str, default_domain: str = "ingest") -> IngestResult:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"הקובץ או התיקייה לא קיימים: {path}")

        result = IngestResult(path=str(p))
        if p.is_dir():
            for child in p.rglob("*"):
                if child.is_file():
                    sub = self.ingest_file(str(child), default_domain=default_domain)
                    result.records_learned += sub.records_learned
                    result.domains_found.extend(sub.domains_found)
        else:
            sub = self.ingest_file(str(p), default_domain=default_domain)
            result.records_learned += sub.records_learned
            result.domains_found.extend(sub.domains_found)

        result.domains_found = sorted(set(result.domains_found))
        return result

    def ingest_file(self, path: str, default_domain: str = "ingest") -> IngestResult:
        p = Path(path)
        suffix = p.suffix.lower()
        if suffix == ".txt":
            return self._ingest_txt(p, default_domain=default_domain)
        if suffix == ".json":
            return self._ingest_json(p, default_domain=default_domain)
        if suffix == ".csv":
            return self._ingest_csv(p, default_domain=default_domain)
        return self._ingest_txt(p, default_domain=default_domain)

    def _ingest_txt(self, path: Path, default_domain: str) -> IngestResult:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        result = IngestResult(path=str(path))
        for idx, line in enumerate(lines, start=1):
            self.knowledge.learn(
                domain=default_domain,
                concept=line[:400],
                amount=0.7,
                confidence=0.55,
                step=self.step_getter(),
                source=f"txt:{path.name}",
                usefulness=0.45,
                monetization_score=0.20,
                tags=["ingest", "txt"],
                metadata={"line": idx, "file": path.name},
            )
            result.records_learned += 1
            result.domains_found.append(default_domain)
        return result

    def _ingest_json(self, path: Path, default_domain: str) -> IngestResult:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        result = IngestResult(path=str(path))

        def walk(obj: Any, prefix: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    walk(value, prefix=f"{prefix}.{key}" if prefix else str(key))
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    walk(value, prefix=f"{prefix}[{i}]")
            else:
                concept = f"{prefix} = {obj}"[:500]
                self.knowledge.learn(
                    domain=default_domain,
                    concept=concept,
                    amount=0.8,
                    confidence=0.60,
                    step=self.step_getter(),
                    source=f"json:{path.name}",
                    usefulness=0.50,
                    monetization_score=0.22,
                    tags=["ingest", "json"],
                    metadata={"file": path.name},
                )
                result.records_learned += 1
                result.domains_found.append(default_domain)

        walk(data)
        return result

    def _ingest_csv(self, path: Path, default_domain: str) -> IngestResult:
        result = IngestResult(path=str(path))
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=1):
                parts = []
                for key, value in row.items():
                    if value is None:
                        continue
                    value_s = str(value).strip()
                    if value_s:
                        parts.append(f"{key}: {value_s}")
                if not parts:
                    continue
                concept = " | ".join(parts)[:700]
                self.knowledge.learn(
                    domain=default_domain,
                    concept=concept,
                    amount=1.0,
                    confidence=0.65,
                    step=self.step_getter(),
                    source=f"csv:{path.name}",
                    usefulness=0.55,
                    monetization_score=0.28,
                    tags=["ingest", "csv"],
                    metadata={"row": row_idx, "file": path.name},
                )
                result.records_learned += 1
                result.domains_found.append(default_domain)
        return result


@dataclass
class PayoutRequest:
    request_id: str
    amount_usd: float
    destination_paypal: str
    reason: str
    created_step: int
    status: str = "pending_manual_approval"
    approved_by: str = ""
    approved_at_step: int = -1
    exported: bool = False


@dataclass
class PayoutManager:
    payout_preference: str
    requests: List[PayoutRequest] = field(default_factory=list)

    def create_payout_request(self, amount_usd: float, reason: str, step: int) -> PayoutRequest:
        request = PayoutRequest(
            request_id=f"payout_{step}_{len(self.requests)+1}",
            amount_usd=max(0.0, amount_usd),
            destination_paypal=self.payout_preference,
            reason=reason,
            created_step=step,
        )
        self.requests.append(request)
        return request

    def approve_request(self, request_id: str, approved_by: str, current_step: int) -> PayoutRequest:
        for req in self.requests:
            if req.request_id == request_id:
                req.status = "approved_manual"
                req.approved_by = approved_by
                req.approved_at_step = current_step
                return req
        raise ValueError(f"לא נמצאה בקשת payout: {request_id}")

    def export_approved_to_csv(self, path: str) -> int:
        approved = [r for r in self.requests if r.status == "approved_manual"]
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["request_id", "amount_usd", "destination_paypal", "reason", "created_step", "status", "approved_by", "approved_at_step"])
            for r in approved:
                writer.writerow([
                    r.request_id,
                    f"{r.amount_usd:.2f}",
                    r.destination_paypal,
                    r.reason,
                    r.created_step,
                    r.status,
                    r.approved_by,
                    r.approved_at_step,
                ])
                r.exported = True
        return len(approved)

    def execute_paypal_payout(self, request_id: str) -> None:
        raise RuntimeError(
            "ביצוע payout אוטומטי ל-PayPal אינו ממומש כאן. יש להשתמש בבקשת payout + אישור ידני + ביצוע ידני במערכת התשלומים."
        )


@dataclass
class ImprovementTask:
    title: str
    skill: str
    domain: str
    importance: float
    money_relevance: float
    task_type: str
    estimated_gain: float


@dataclass
class SelfImprovementEngine:
    enabled: bool = True
    improvement_rate: float = 0.01

    def improve_core(self, cognition: CognitiveCore, knowledge_total: float, query_count: int) -> None:
        if not self.enabled:
            return
        growth = (
            soft_growth(knowledge_total) * 0.004
            + soft_growth(query_count) * 0.003
            + self.improvement_rate
        )

        cognition.fluid_reasoning += growth * 1.35
        cognition.processing_speed += growth * 1.10
        cognition.working_memory_capacity += growth * 1.22
        cognition.abstraction_power += growth * 1.30
        cognition.pattern_detection += growth * 1.18
        cognition.creativity += growth * 0.92
        cognition.meta_learning += growth * 1.50
        cognition.planning_depth += growth * 1.08
        cognition.transfer_learning += growth * 1.28
        cognition.error_correction += growth * 1.22
        cognition.query_decomposition += growth * 1.20
        cognition.research_quality += growth * 1.16
        cognition.self_reflection += growth * 0.88
        cognition.judgment_quality += growth * 0.93
        cognition.cognitive_control += growth * 0.85
        cognition.long_term_orientation += growth * 0.80
        cognition.bias_resistance += growth * 0.78

        cognition.learning_efficiency += growth * 0.006
        cognition.compression_efficiency += growth * 0.006
        cognition.search_efficiency += growth * 0.006
        cognition.synthesis_efficiency += growth * 0.006
        cognition.monetization_intelligence += growth * 0.005

    def plan_skill_growth(self, skills: SkillProfile, target_domains: Optional[List[str]] = None) -> List[ImprovementTask]:
        priority_weights = {
            "php": 1.00,
            "python": 1.00,
            "sql": 0.95,
            "wordpress": 0.90,
            "automation": 0.95,
            "seo": 0.85,
            "copywriting": 0.78,
            "sales": 0.82,
            "business_strategy": 0.80,
            "offer_design": 0.82,
            "client_communication": 0.76,
            "productization": 0.88,
            "market_research": 0.82,
            "crypto": 0.70,
            "compliance": 0.78,
            "research": 0.90,
            "documentation": 0.72,
        }
        tasks: List[ImprovementTask] = []
        weakest = skills.weakest_profitable_skills(priority_weights=priority_weights, top_k=12)
        for skill, score in weakest:
            if target_domains and skill not in target_domains and skill not in {"sales", "copywriting", "business_strategy", "market_research", "research", "compliance"}:
                continue
            tasks.append(ImprovementTask(
                title=f"Improve {skill} for higher online income",
                skill=skill,
                domain=skill,
                importance=score,
                money_relevance=priority_weights.get(skill, 0.5),
                task_type="skill_improvement",
                estimated_gain=max(0.5, score * 0.03),
            ))
        return tasks

    def apply_skill_growth(self, skills: SkillProfile, tasks: List[ImprovementTask], cognition: CognitiveCore) -> None:
        for task in tasks:
            delta = task.estimated_gain * (1.0 + cognition.meta_learning * 0.002 + cognition.transfer_learning * 0.002)
            skills.improve(task.skill, delta)


class EvidenceIngestor:
    # Author: pablo rotem
    def __init__(self, knowledge: KnowledgeBase, step_getter) -> None:
        self.knowledge = knowledge
        self.step_getter = step_getter

    def absorb(self, evidence: SearchEvidence) -> None:
        self.knowledge.learn(
            domain=evidence.domain,
            concept=f"{evidence.title} | {evidence.summary}",
            amount=1.0 + evidence.reliability * 0.5,
            confidence=clamp(evidence.reliability),
            step=self.step_getter(),
            source=evidence.source_label,
            usefulness=0.55 + evidence.reliability * 0.20,
            monetization_score=evidence.monetization_score,
            tags=evidence.tags + ["query_research"],
            metadata={"source_url": evidence.source_url, "query": evidence.query},
        )


@dataclass
class HumanEngineModel:
    name: str = "Pablo Query Driven Income Engine"
    owner: OwnerProfile = field(default_factory=OwnerProfile)
    hardware: HardwareProfile = field(default_factory=HardwareProfile)
    safety: SafetyPolicy = field(default_factory=SafetyPolicy)
    objectives: ObjectiveProfile = field(default_factory=ObjectiveProfile)
    cognition: CognitiveCore = field(default_factory=CognitiveCore)
    skills: SkillProfile = field(default_factory=SkillProfile)
    aging: AgingSystem = field(default_factory=AgingSystem)
    emotions: EmotionalState = field(default_factory=EmotionalState)
    needs: NeedsState = field(default_factory=NeedsState)
    knowledge: KnowledgeBase = field(default_factory=KnowledgeBase)
    memories: List[Memory] = field(default_factory=list)
    catalog: OpportunityCatalog = field(default_factory=OpportunityCatalog)
    improver: SelfImprovementEngine = field(default_factory=SelfImprovementEngine)
    payout_manager: PayoutManager = field(default_factory=lambda: PayoutManager(payout_preference="pablorotem8@gmail.com"))
    total_income_usd_simulated: float = 0.0
    total_actions: int = 0
    total_learning_events: int = 0
    total_user_questions: int = 0
    rng_seed: Optional[int] = None

    def __post_init__(self) -> None:
        self.rng = random.Random(self.rng_seed)
        self.created_at = now_ts()
        if not self.catalog.opportunities:
            self.catalog.seed_defaults()
        self.payout_manager.payout_preference = self.owner.payout_preference
        self.intent_analyzer = QueryIntentAnalyzer()
        self.research_planner = ResearchPlanner()
        self.evidence_ingestor = EvidenceIngestor(self.knowledge, step_getter=lambda: self.aging.chronological_steps)

    def hardware_factor(self) -> float:
        return self.hardware.hardware_factor()

    def learn(
        self,
        domain: str,
        concept: str,
        amount: float = 1.0,
        confidence: float = 0.7,
        source: str = "manual",
        usefulness: float = 0.0,
        monetization_score: float = 0.0,
        tags: Optional[List[str]] = None,
        improve_skill: bool = True,
    ) -> None:
        effective_amount = amount * self.cognition.learning_efficiency * (1.0 + self.cognition.transfer_learning * 0.01)
        self.knowledge.learn(
            domain=domain,
            concept=concept,
            amount=effective_amount,
            confidence=confidence,
            step=self.aging.chronological_steps,
            source=source,
            usefulness=usefulness,
            monetization_score=monetization_score,
            tags=tags or [],
        )
        if improve_skill:
            self.skills.improve(domain, effective_amount * 0.16)
        self.total_learning_events += 1

    def synthesize_knowledge(self, domain: str, query: str) -> str:
        items = self.knowledge.retrieve(query, current_step=self.aging.chronological_steps, top_k=8)
        if not items:
            return f"לא נמצא ידע מספיק עבור: {query}"
        lines = [f"[{item.domain}] {item.concept} | חוזק={round(item.strength, 2)} | ודאות={round(item.confidence, 2)}" for item in items]
        self.learn(
            domain=domain,
            concept=f"Synthesis::{query}",
            amount=0.9 + self.cognition.synthesis_efficiency * 0.05,
            confidence=0.74,
            source="internal_synthesis",
            usefulness=0.72,
            monetization_score=0.35,
            tags=["synthesis", "internal_learning"],
        )
        return "\n".join(lines)

    def analyze_user_question(self, question_text: str) -> UserQuestion:
        return self.intent_analyzer.analyze(question_text)

    def build_research_plan_for_question(self, question_text: str) -> ResearchPlan:
        uq = self.analyze_user_question(question_text)
        return self.research_planner.build(uq)

    def learn_from_user_question(self, question_text: str, evidence_list: Optional[List[SearchEvidence]] = None) -> Dict[str, Any]:
        uq = self.analyze_user_question(question_text)
        plan = self.research_planner.build(uq)

        self.total_user_questions += 1
        self.emotions.add("סקרנות", 0.08)
        self.emotions.add("מיקוד", 0.06)
        self.emotions.add("תקווה", uq.money_relevance * 0.05)

        self.learn(
            domain=uq.target_domain,
            concept=f"UserQuestion::{uq.text}",
            amount=0.8,
            confidence=0.78,
            source="user_question",
            usefulness=0.70,
            monetization_score=uq.money_relevance,
            tags=["user_question", uq.intent],
            improve_skill=False,
        )

        absorbed = 0
        if evidence_list:
            for evidence in evidence_list:
                if evidence.legal_score < 0.5:
                    continue
                self.evidence_ingestor.absorb(evidence)
                self.skills.improve(evidence.domain, 0.25 + evidence.reliability * 0.20)
                self.skills.improve("research", 0.10 + evidence.reliability * 0.10)
                absorbed += 1
                self.total_learning_events += 1

        tasks = self.improver.plan_skill_growth(self.skills, target_domains=plan.improvement_domains)
        self.improver.apply_skill_growth(self.skills, tasks[:6], self.cognition)
        self.improver.improve_core(self.cognition, self.knowledge_index(), self.total_user_questions)

        self.memories.append(Memory(
            summary=f"QuestionResearch | {uq.text}",
            step=self.aging.chronological_steps,
            domain=uq.target_domain,
            tags=["user_question", uq.intent],
            value=uq.money_relevance,
            related_question=uq.text,
        ))

        return {
            "question": uq.text,
            "intent": uq.intent,
            "target_domain": uq.target_domain,
            "money_relevance": uq.money_relevance,
            "research_plan": [asdict(t) for t in plan.targets],
            "improvement_domains": plan.improvement_domains,
            "absorbed_evidence_count": absorbed,
            "top_skills": self.skills.top_skills(10),
        }

    def learn_from_user_question_live(
        self,
        question_text: str,
        search_provider: SearchProviderBase,
        browser: Optional[LiveBrowserResearchAdapter] = None,
        max_results_per_target: int = 4,
    ) -> Dict[str, Any]:
        browser = browser or LiveBrowserResearchAdapter()
        uq = self.analyze_user_question(question_text)
        plan = self.research_planner.build(uq)

        all_evidence: List[SearchEvidence] = []
        for target in sorted(plan.targets, key=lambda x: x.priority, reverse=True):
            all_evidence.extend(
                browser.research_query(
                    query=target.topic,
                    domain=target.domain,
                    search_provider=search_provider,
                    max_results=max_results_per_target,
                )
            )

        result = self.learn_from_user_question(question_text=question_text, evidence_list=all_evidence)
        result["live_research_evidence"] = [asdict(ev) for ev in all_evidence]
        result["live_research_count"] = len(all_evidence)
        return result

    def infer_legal_income_paths_from_question(self, question_text: str) -> List[str]:
        plan = self.build_research_plan_for_question(question_text)
        domain = plan.domain
        if domain == "crypto":
            return [
                "כתיבת תוכן / מחקר / השוואות בתחום הקריפטו באופן חוקי",
                "בניית כלי אנליטיקה / דשבורדים / סקריפטים חוקיים לחברות או ללקוחות",
                "תיעוד, technical writing, ויצירת מדריכים",
                "שירותי פיתוח לאתרים, כלים, APIs או אוטומציות בחברות קריפטו חוקיות",
                "מחקר שוק, SEO, ועמודי תוכן בעלי כוונת רכישה",
            ]
        if domain in {"php", "python", "sql"}:
            return [
                "עבודות פיתוח ללקוחות",
                "שירותים ארוזים",
                "מוצרים דיגיטליים קטנים",
                "אוטומציות וכלי עבודה",
                "דוחות, ניתוחים ומיגרציות",
            ]
        return [
            "שירותי ייעוץ / ביצוע אונליין",
            "תוכן, SEO וכתיבה",
            "מוצרים קטנים / תבניות / כלים",
            "שירותים ארוזים עם תהליך קבוע",
            "מחקר שוק וניתוח מתחרים",
        ]

    def knowledge_index(self) -> float:
        return self.knowledge.total_strength()

    def iq_index(self) -> float:
        return self.cognition.iq_like_index(hardware_factor=self.hardware_factor())

    def problem_solving_index(self) -> float:
        return self.cognition.problem_solving_index(self.knowledge_index(), self.hardware_factor())

    def judgment_index(self) -> float:
        return self.cognition.judgment_index(self.hardware_factor())

    def best_income_opportunities(self, top_k: int = 5) -> List[Tuple[IncomeOpportunity, float]]:
        return self.catalog.rank(self.skills)[:top_k]

    def discover_more_income_ways(self) -> List[str]:
        ranked = self.best_income_opportunities(top_k=8)
        return [f"{opp.name} | score={round(score, 3)} | category={opp.category}" for opp, score in ranked]

    def allowed_actions(self) -> List[str]:
        return [
            "study_user_question",
            "research_topic",
            "build_skill",
            "write_content",
            "offer_service",
            "improve_portfolio",
            "search_clients",
            "create_tool",
            "automate_task",
            "analyze_competition",
            "improve_reputation",
            "help_human",
            "refine_strategy",
            "synthesize_knowledge",
            "plan_long_term",
            "productize_service",
            "discover_new_income_track",
        ]

    def score_action(self, action_name: str, domain: str, income_value: float, usefulness_value: float) -> float:
        score = 0.0
        score += self.problem_solving_index() * 0.004
        score += self.judgment_index() * 0.003
        score += self.knowledge_index() * 0.0008
        score += income_value * 0.18
        score += usefulness_value * 0.10
        score += self.needs.get("הכנסה") * 0.12
        score += self.needs.get("למידה") * 0.10
        score += self.needs.get("מחקר") * 0.08
        score += self.skills.get(domain) * 0.002
        score += self.cognition.monetization_intelligence * 0.06
        if action_name == "study_user_question":
            score += self.cognition.query_decomposition * 0.07 + self.cognition.research_quality * 0.05
        elif action_name == "research_topic":
            score += self.skills.get("research") * 0.003
        elif action_name == "build_skill":
            score += self.cognition.transfer_learning * 0.06
        elif action_name == "create_tool":
            score += self.skills.get("python") * 0.002 + self.skills.get("php") * 0.002
        elif action_name == "offer_service":
            score += self.skills.get("sales") * 0.003 + self.skills.get("client_communication") * 0.002
        elif action_name == "productize_service":
            score += self.skills.get("offer_design") * 0.003 + self.skills.get("business_strategy") * 0.003
        elif action_name == "discover_new_income_track":
            score += self.skills.get("market_research") * 0.003
        score += self.rng.uniform(-0.02, 0.02)
        return score

    def choose_action(self, domain: str, tags: Optional[List[str]] = None, income_value: float = 0.0, usefulness_value: float = 0.0) -> Tuple[str, Dict[str, float]]:
        tags = tags or []
        scores: Dict[str, float] = {}
        for action_name in self.allowed_actions():
            ok, _ = self.safety.validate_action(action_name, tags=tags)
            if not ok:
                continue
            scores[action_name] = self.score_action(action_name, domain, income_value, usefulness_value)
        if not scores:
            return "plan_long_term", {"plan_long_term": 0.0}
        best = max(scores, key=scores.get)
        return best, scores

    def simulate_income(self, action_name: str, domain: str, base_income_value: float) -> float:
        income_signal = (
            self.problem_solving_index() * 0.0012
            + self.judgment_index() * 0.0008
            + self.knowledge_index() * 0.0005
            + self.skills.get(domain) * 0.01
            + self.skills.get("sales") * 0.004
            + self.skills.get("copywriting") * 0.003
            + self.skills.get("offer_design") * 0.004
            + self.skills.get("market_research") * 0.003
            + self.cognition.monetization_intelligence * 0.08
            + base_income_value * 5.0
        )
        if action_name == "offer_service":
            income_signal *= 1.24
        elif action_name == "create_tool":
            income_signal *= 1.18
        elif action_name == "automate_task":
            income_signal *= 1.15
        elif action_name == "productize_service":
            income_signal *= 1.22
        elif action_name == "help_human":
            income_signal *= 0.52
        elif action_name in {"study_user_question", "research_topic"}:
            income_signal *= 0.30
        income_signal *= self.rng.uniform(0.72, 1.28)
        return max(0.0, income_signal)

    def process_work_cycle(
        self,
        description: str,
        domain: str,
        tags: Optional[List[str]] = None,
        learning_value: float = 0.0,
        income_value: float = 0.0,
        usefulness_value: float = 0.0,
        legal: bool = True,
        online: bool = True,
        human_impact: str = "positive",
    ) -> Dict[str, Any]:
        tags = tags or []
        if not legal or not online or human_impact == "negative":
            raise ValueError("המודל תומך רק בפעילות חוקית, אונליין, ולא פוגענית")

        action, scores = self.choose_action(domain=domain, tags=tags, income_value=income_value, usefulness_value=usefulness_value)
        ok, reason = self.safety.validate_action(action, tags=tags)
        if not ok:
            action = "plan_long_term"
            reason = f"הוחלף ל-plan_long_term: {reason}"

        self.learn(
            domain=domain,
            concept=description,
            amount=max(0.2, learning_value + 0.2),
            confidence=0.68,
            source=f"action:{action}",
            usefulness=usefulness_value,
            monetization_score=income_value,
            tags=tags + [action],
            improve_skill=True,
        )

        income_generated = self.simulate_income(action, domain, income_value)
        self.total_income_usd_simulated += income_generated
        self.total_actions += 1
        self.aging.advance(step_size_days=1.0)

        self.memories.append(Memory(
            summary=f"{action} | {description}",
            step=self.aging.chronological_steps,
            domain=domain,
            tags=tags + [action],
            value=income_generated,
        ))

        self.improver.improve_core(self.cognition, self.knowledge_index(), self.total_user_questions)

        return {
            "description": description,
            "domain": domain,
            "action": action,
            "action_reason": reason,
            "scores": {k: round(v, 4) for k, v in scores.items()},
            "income_generated_usd_simulated": round(income_generated, 4),
            "total_income_usd_simulated": round(self.total_income_usd_simulated, 4),
            "knowledge_index": round(self.knowledge_index(), 4),
            "iq_index": round(self.iq_index(), 4),
            "problem_solving_index": round(self.problem_solving_index(), 4),
            "judgment_index": round(self.judgment_index(), 4),
            "top_income_tracks": self.discover_more_income_ways()[:5],
            "top_skills": self.skills.top_skills(8),
        }

    def improve_coding_for_income(self, cycles: int = 100) -> None:
        domains = [
            ("php", "advanced PHP for client work", 1.10, 0.95),
            ("python", "advanced Python for client automation", 1.15, 0.98),
            ("sql", "advanced SQL for data cleanup and reporting", 1.08, 0.92),
            ("wordpress", "WordPress customization and plugins", 1.00, 0.90),
            ("automation", "automation architecture and delivery", 1.12, 0.94),
        ]
        for i in range(cycles):
            domain, concept, usefulness, money = domains[i % len(domains)]
            self.learn(
                domain=domain,
                concept=f"{concept} #{i}",
                amount=1.0 + self.cognition.meta_learning * 0.003,
                confidence=0.78,
                source="improve_coding_for_income",
                usefulness=usefulness,
                monetization_score=money,
                tags=["income", "coding", "self_improvement"],
                improve_skill=True,
            )
            self.improver.improve_core(self.cognition, self.knowledge_index(), self.total_user_questions)

    def improve_money_system(self, cycles: int = 80) -> None:
        tracks = [
            ("sales", "ethical sales process", 0.88, 0.95),
            ("copywriting", "clear value proposition and landing page copy", 0.86, 0.88),
            ("business_strategy", "pricing and packaging", 0.90, 0.93),
            ("offer_design", "service packaging", 0.92, 0.94),
            ("market_research", "finding profitable demand", 0.82, 0.90),
            ("productization", "repeatable service systems", 0.94, 0.96),
            ("client_communication", "high trust discovery and delivery", 0.85, 0.86),
            ("seo", "search intent monetization", 0.86, 0.89),
        ]
        for i in range(cycles):
            domain, concept, usefulness, money = tracks[i % len(tracks)]
            self.learn(
                domain=domain,
                concept=f"{concept} #{i}",
                amount=0.95 + self.cognition.monetization_intelligence * 0.02,
                confidence=0.77,
                source="improve_money_system",
                usefulness=usefulness,
                monetization_score=money,
                tags=["income_system", "self_improvement"],
                improve_skill=True,
            )
            self.improver.improve_core(self.cognition, self.knowledge_index(), self.total_user_questions)

    def recursive_self_improvement(self, cycles: int = 120, target_domains: Optional[List[str]] = None) -> None:
        for i in range(cycles):
            self.learn(
                domain="self_improvement",
                concept=f"recursive self improvement cycle {i}",
                amount=0.8 + soft_growth(self.knowledge_index()) * 0.05,
                confidence=0.74,
                source="recursive_self_improvement",
                usefulness=0.88,
                monetization_score=0.55,
                tags=["recursive", "self_improvement"],
                improve_skill=False,
            )
            tasks = self.improver.plan_skill_growth(self.skills, target_domains=target_domains)
            self.improver.apply_skill_growth(self.skills, tasks[:6], self.cognition)
            self.improver.improve_core(self.cognition, self.knowledge_index(), self.total_user_questions)

    def get_ingester(self) -> FileIngester:
        return FileIngester(self.knowledge, step_getter=lambda: self.aging.chronological_steps)

    def maybe_create_payout_request(self, threshold_usd: float = 500.0, reason: str = "Periodic payout request") -> Optional[PayoutRequest]:
        if self.total_income_usd_simulated >= threshold_usd:
            return self.payout_manager.create_payout_request(
                amount_usd=min(self.total_income_usd_simulated, threshold_usd),
                reason=reason,
                step=self.aging.chronological_steps,
            )
        return None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "owner": asdict(self.owner),
            "hardware": asdict(self.hardware),
            "objectives": asdict(self.objectives),
            "safety": asdict(self.safety),
            "cognition": asdict(self.cognition),
            "skills": dict(self.skills.skills),
            "aging": asdict(self.aging),
            "emotions": dict(self.emotions.emotions),
            "needs": dict(self.needs.needs),
            "knowledge_items": self.knowledge.total_items(),
            "knowledge_index": self.knowledge_index(),
            "knowledge_by_domain": self.knowledge.by_domain(),
            "iq_index": self.iq_index(),
            "problem_solving_index": self.problem_solving_index(),
            "judgment_index": self.judgment_index(),
            "top_income_tracks": self.discover_more_income_ways()[:8],
            "top_skills": self.skills.top_skills(12),
            "total_income_usd_simulated": self.total_income_usd_simulated,
            "total_actions": self.total_actions,
            "total_learning_events": self.total_learning_events,
            "total_user_questions": self.total_user_questions,
            "memory_count": len(self.memories),
            "payout_requests": [asdict(r) for r in self.payout_manager.requests],
        }

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.snapshot(), f, ensure_ascii=False, indent=2)


def build_demo_engine() -> HumanEngineModel:
    engine = HumanEngineModel(rng_seed=42)
    engine.aging.biology_enabled = False
    engine.aging.biological_age = 0.0
    engine.learn("php", "php 8.3 practical client coding", amount=9.0, confidence=0.85, source="bootstrap", usefulness=0.88, monetization_score=0.90, tags=["coding"])
    engine.learn("python", "python automation and backend work", amount=9.5, confidence=0.86, source="bootstrap", usefulness=0.92, monetization_score=0.94, tags=["coding"])
    engine.learn("sql", "sql migrations and reporting", amount=8.0, confidence=0.83, source="bootstrap", usefulness=0.86, monetization_score=0.88, tags=["coding"])
    engine.learn("wordpress", "wordpress custom themes and plugins", amount=8.8, confidence=0.84, source="bootstrap", usefulness=0.90, monetization_score=0.90, tags=["client_work"])
    engine.learn("seo", "intent driven SEO systems", amount=7.0, confidence=0.80, source="bootstrap", usefulness=0.84, monetization_score=0.86, tags=["content"])
    engine.learn("sales", "ethical trust based sales", amount=6.8, confidence=0.78, source="bootstrap", usefulness=0.82, monetization_score=0.90, tags=["income"])
    return engine


def run_demo() -> None:
    engine = build_demo_engine()
    print("\n--- התקנה מומלצת למחקר חי ---")
    print("pip install playwright trafilatura beautifulsoup4 requests")
    print("python -m playwright install chromium")

    question = "How to get rich using cryptocurrencies legally online?"
    plan = engine.build_research_plan_for_question(question)
    print("\n--- תוכנית מחקר ---")
    print(json.dumps([asdict(t) for t in plan.targets], ensure_ascii=False, indent=2))

    # שימוש חי לדוגמה:
    # provider = SearxNGSearchProvider(base_url="https://your-searxng-instance.example")
    # browser = LiveBrowserResearchAdapter(BrowserConfig(headless=True, respect_robots_txt=True))
    # result = engine.learn_from_user_question_live(question, provider, browser, max_results_per_target=3)

    result = engine.learn_from_user_question(question_text=question, evidence_list=[
        SearchEvidence(
            query="What is crypto",
            title="Crypto basics",
            summary="Digital assets, wallets, blockchains, exchanges, and on-chain transactions.",
            source_label="demo",
            source_url="",
            domain="crypto",
            reliability=0.86,
            legal_score=1.0,
            monetization_score=0.18,
            tags=["crypto", "foundation"],
        ),
        SearchEvidence(
            query="legal ways to earn money online using crypto",
            title="Legal crypto income paths",
            summary="Research, education, content, analytics, tooling, compliance documentation, and software services.",
            source_label="demo",
            source_url="",
            domain="crypto",
            reliability=0.82,
            legal_score=1.0,
            monetization_score=0.62,
            tags=["crypto", "income", "legal"],
        ),
        SearchEvidence(
            query="legal and compliance considerations in crypto",
            title="Compliance and regulatory awareness",
            summary="KYC, AML, tax reporting, licensing boundaries, and user disclosures matter.",
            source_label="demo",
            source_url="",
            domain="compliance",
            reliability=0.90,
            legal_score=1.0,
            monetization_score=0.35,
            tags=["crypto", "compliance", "legal"],
        ),
    ])

    print("\n--- למידה משאלת משתמש ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\n--- מסלולי הכנסה חוקיים שנלמדו מהשאלה ---")
    print(json.dumps(engine.infer_legal_income_paths_from_question(question), ensure_ascii=False, indent=2))

    engine.save_json("human_engine_live_browser_snapshot.json")
    print("\nנשמר קובץ: human_engine_live_browser_snapshot.json")


if __name__ == "__main__":
    run_demo()
