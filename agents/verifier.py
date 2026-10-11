"""
Verifier Agent
Autonomous auditing agent that systematically evaluates every collected evidence item.
Ensures factual integrity, source credibility, and strict epistemic hygiene before
passing evidence to the Final Analyst.

Verifier checks:
1. Does the source support the claim?
2. Is the source trustworthy?
3. Is it current?
4. Is the numerical value correct?
5. Is the conclusion stronger than the evidence?
6. Are there conflicting sources?
7. Is this fact, inference or speculation?

Sets:
verified = true/false
verification_reason = "..."
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional

from agents.models import Evidence, VerifiedEvidence, VerificationCheck, VerificationReport

logger = logging.getLogger("agents.verifier")

TRUSTED_DOMAINS = [
    "sec.gov",
    "finance.yahoo.com",
    "openalex.org",
    "doi.org",
    "arxiv.org",
    "bloomberg.com",
    "reuters.com",
    "wsj.com",
    "ft.com",
    "cnbc.com",
    "prnewswire.com",
    "businesswire.com",
    "globenewswire.com",
    "nvidia.com",
    "apple.com",
    "microsoft.com",
    "google.com",
    "amazon.com",
    "tesla.com",
    "fda.gov",
    "uspto.gov",
]

UNTRUSTED_PATTERNS = [
    r"rumors?",
    r"leak(?:ed|s)?",
    r"gossip",
    r"speculat(?:ion|ive)?",
    r"unconfirmed",
    r"anonymous\s+sources?",
    r"unverified",
    r"clickbait",
    r"reddit\.com",
    r"twitter\.com",
    r"x\.com",
]

HYPERBOLIC_PATTERNS = [
    r"\bguaranteed\s+to\b",
    r"\bwill\s+10x\b",
    r"\brisk-free\b",
    r"\bcannot\s+fail\b",
    r"\bunbeatable\s+monopoly\b",
    r"\bproves\s+the\s+stock\s+will\b",
    r"\bwill\s+bankrupt\s+all\b",
    r"\bcompletely\s+destroyed\b",
]


class Verifier:
    """Rigorous audit agent that checks every candidate evidence item against 7 criteria."""

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def verify_all(self, evidence_items: List[Evidence]) -> VerificationReport:
        """
        Audits all candidate evidence items and segregates verified vs rejected evidence.
        """
        logger.info(f"[Verifier] Beginning audit of {len(evidence_items)} candidate evidence items...")
        verified_list: List[VerifiedEvidence] = []
        rejected_list: List[VerifiedEvidence] = []

        # Step 1: Detect cross-source conflicts across quantitative claims
        conflicts_map = self._detect_conflicts(evidence_items)

        # Step 2: Audit each item individually
        for ev in evidence_items:
            audit_item = self._audit_claim(ev, conflicts_map.get(ev.claim, []))
            if audit_item.verified:
                verified_list.append(audit_item)
                logger.info(f"[Verifier] [ACCEPTED] ({ev.agent_name}) {ev.claim[:70]} | Reason: {audit_item.verification_reason}")
            else:
                rejected_list.append(audit_item)
                logger.warning(
                    f"[Verifier] [REJECTED] ({ev.agent_name}) {ev.claim[:70]} | "
                    f"Reason: {audit_item.verification_reason}"
                )

        report = VerificationReport(
            total_claims=len(evidence_items),
            verified_count=len(verified_list),
            rejected_count=len(rejected_list),
            verified_items=verified_list,
            rejected_items=rejected_list,
        )
        logger.info(f"[Verifier] Audit completed: {report.summary()}")
        return report

    def _audit_claim(self, ev: Evidence, conflicting_claims: List[str]) -> VerifiedEvidence:
        """Applies the 7 mandatory verification checks to a single evidence item."""
        rejection_reasons = []

        # 1. Does the source support the claim?
        supports = bool(ev.evidence_text and len(ev.evidence_text.strip()) >= 5)
        # Check semantic consistency
        if supports:
            ev_words = set(re.findall(r"\w{4,}", ev.evidence_text.lower()))
            cl_words = set(re.findall(r"\w{4,}", ev.claim.lower()))
            if cl_words and not (ev_words & cl_words):
                # No common words between evidence text and claim
                supports = False
                rejection_reasons.append("Evidence snippet does not share substantive keywords with claim.")
        else:
            rejection_reasons.append("Missing supporting evidence text or citation snippet.")

        # 2. Is the source trustworthy?
        trustworthy = self._is_source_trustworthy(ev.source_url, ev.source_name, ev.source_type)
        if not trustworthy:
            rejection_reasons.append(f"Source '{ev.source_name}' ({ev.source_url}) does not meet institutional trust threshold.")

        # 3. Is it current?
        is_current = self._is_current(ev.source_date)
        if not is_current:
            rejection_reasons.append(f"Source date '{ev.source_date}' is stale or predates the relevant evaluation cycle.")

        # 4. Is the numerical value correct?
        num_ok = self._is_numerical_value_plausible(ev)
        if not num_ok:
            rejection_reasons.append("Numerical value is out of plausible bounds or conflicts with standard accounting definitions.")

        # 5. Is the conclusion stronger than the evidence?
        proportional = not any(re.search(pat, ev.claim, re.IGNORECASE) for pat in HYPERBOLIC_PATTERNS)
        if not proportional:
            rejection_reasons.append("Conclusion is hyperbolic or disproportionately stronger than the factual evidence.")

        # 6. Are there conflicting sources?
        no_conflicts = len(conflicting_claims) == 0
        if not no_conflicts:
            rejection_reasons.append(f"Contradicted by opposing source claim: '{conflicting_claims[0]}'.")

        # 7. Is this fact, inference or speculation?
        epistemic = self._audit_epistemic_integrity(ev)
        if epistemic == "SPECULATION" and ev.epistemic_status == "FACT":
            rejection_reasons.append("Speculation or unconfirmed rumor was improperly labeled as FACT.")
        elif epistemic == "SPECULATION" and self.strict_mode and ev.source_type != "NEWS":
            rejection_reasons.append("Unconfirmed speculation cannot be admitted as foundational evidence.")

        checks = VerificationCheck(
            source_supports_claim=supports,
            source_trustworthy=trustworthy,
            is_current=is_current,
            numerical_value_correct=num_ok,
            conclusion_proportional_to_evidence=proportional,
            no_unresolved_conflicts=no_conflicts,
            epistemic_status=epistemic,
            notes="; ".join(rejection_reasons) if rejection_reasons else "All 7 verification criteria passed.",
        )

        is_verified = (
            supports
            and trustworthy
            and is_current
            and num_ok
            and proportional
            and no_conflicts
            and not (epistemic == "SPECULATION" and ev.epistemic_status == "FACT")
        )

        if is_verified:
            reason = f"Verified: Supported by {ev.source_name} as {epistemic} with source corroboration."
        else:
            reason = f"Rejected: {'; '.join(rejection_reasons)}"

        return VerifiedEvidence(
            evidence=ev,
            verified=is_verified,
            verification_reason=reason,
            checks=checks,
        )

    def _is_source_trustworthy(self, url: str, name: str, source_type: str) -> bool:
        """Evaluates whether the origin of the claim is institutional and verifiable."""
        if source_type in ("SEC_FILING", "FINANCIAL_API", "ACADEMIC_PAPER"):
            return True

        text_to_audit = f"{url} {name}".lower()

        # Check for untrusted patterns
        for pat in UNTRUSTED_PATTERNS:
            if re.search(pat, text_to_audit):
                return False

        # If URL matches trusted domains
        for domain in TRUSTED_DOMAINS:
            if domain in text_to_audit:
                return True

        # If it has a legitimate HTTP URL and publisher name
        if url.startswith("http") and name and len(name) >= 3:
            return True

        return False

    def _is_current(self, date_str: str) -> bool:
        """Audits timeliness of the information."""
        if not date_str or date_str in ("Recent", "Current Market Data"):
            return True

        # Check year in date string
        years = re.findall(r"\b(19\d{2}|20\d{2})\b", date_str)
        if years:
            latest_year = max(int(y) for y in years)
            # Require data from 2022 onwards for contemporary analysis
            if latest_year < 2022:
                return False

        return True

    def _is_numerical_value_plausible(self, ev: Evidence) -> bool:
        """Verifies plausibility of reported quantitative metrics."""
        if ev.numerical_value is None:
            return True

        val = ev.numerical_value
        m_name = (ev.metric_name or "").lower()

        # Margin percentages check
        if "margin" in m_name:
            # Margins shouldn't exceed +100% or be below -500% under normal circumstances
            if val > 1.0 or val < -5.0:
                return False

        # Market cap or revenue checks
        if "market cap" in m_name or "revenue" in m_name:
            if val < 0:
                return False

        return True

    def _audit_epistemic_integrity(self, ev: Evidence) -> str:
        """
        Determines the true epistemic status of the evidence.
        Enforces: Speculation must NEVER be presented as fact.
        """
        lower_claim = ev.claim.lower()
        lower_evidence = ev.evidence_text.lower()
        combined = f"{lower_claim} {lower_evidence}"

        # Speculative keywords
        speculative_words = [
            "rumor", "speculat", "unconfirmed", "unverified", "might be",
            "could potentially", "predicted to", "hypothetical", "leak", "purported"
        ]
        if any(w in combined for w in speculative_words):
            return "SPECULATION"

        # Direct factual citations
        if ev.source_type in ("SEC_FILING", "FINANCIAL_API") or any(
            w in lower_claim for w in ["reported", "announced", "filed", "launched", "acquired", "is", "was"]
        ):
            return "FACT"

        if any(w in lower_claim for w in ["expects", "targets", "indicates", "suggests", "projected"]):
            return "INFERENCE"

        return ev.epistemic_status or "FACT"

    def _detect_conflicts(self, items: List[Evidence]) -> Dict[str, List[str]]:
        """Identifies direct numerical contradictions across claims on the same metric."""
        metric_groups: Dict[str, List[Evidence]] = {}
        conflicts: Dict[str, List[str]] = {}

        for item in items:
            if item.metric_name and item.numerical_value is not None:
                key = item.metric_name.strip().lower()
                metric_groups.setdefault(key, []).append(item)

        for metric, group in metric_groups.items():
            if len(group) > 1:
                # Compare numerical values
                base_val = group[0].numerical_value
                for other in group[1:]:
                    if base_val and other.numerical_value:
                        ratio = other.numerical_value / base_val
                        # If values diverge by more than 50% for the exact same metric
                        if ratio > 1.5 or ratio < 0.5:
                            conflicts.setdefault(group[0].claim, []).append(other.claim)
                            conflicts.setdefault(other.claim, []).append(group[0].claim)

        return conflicts
