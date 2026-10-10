"""
SEC EDGAR Document and XBRL Parser
Extracts structured financial facts, filings metadata, insider transactions,
risk factors, management commentary, and major events from SEC EDGAR disclosures.
"""

import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class SECExtractedFact(BaseModel):
    """Structured fact extracted from an official SEC filing."""
    company: str = Field(description="Official company name")
    ticker: str = Field(description="Stock ticker symbol")
    claim: str = Field(description="Description of the financial claim or fact")
    value: Optional[str] = Field(default=None, description="Reported or computed numerical/text value")
    filing_type: str = Field(description="Form type: 10-K, 10-Q, 8-K, 20-F, 4")
    filing_date: str = Field(description="Date the filing was officially submitted to SEC (YYYY-MM-DD)")
    accession_number: str = Field(description="SEC EDGAR unique accession number")
    source_url: str = Field(description="Direct URL to filing on SEC EDGAR")
    source_snippet: Optional[str] = Field(default=None, description="Direct text snippet from SEC disclosure")
    confidence: float = Field(default=1.0, description="Extraction confidence score (0.0 to 1.0)")


class SECFilingMeta(BaseModel):
    """Metadata for an individual SEC filing."""
    form: str
    filing_date: str
    report_date: Optional[str] = None
    accession_number: str
    primary_doc: str
    source_url: str
    description: Optional[str] = None


class SECInsiderTransaction(BaseModel):
    """Structured record of an insider transaction from Form 4."""
    reporting_owner: str
    officer_title: Optional[str] = None
    transaction_date: str
    transaction_type: str
    shares: Optional[float] = None
    price_per_share: Optional[float] = None
    total_value: Optional[float] = None
    filing_date: str
    accession_number: str
    source_url: str


def format_currency_amount(val: Any) -> str:
    """Formats raw numbers into clean human-readable representation ($T, $B, $M)."""
    if val is None:
        return "N/A"
    try:
        num = float(val)
        abs_v = abs(num)
        sign = "-" if num < 0 else ""
        if abs_v >= 1e12:
            return f"{sign}${abs_v / 1e12:.2f}T"
        elif abs_v >= 1e9:
            return f"{sign}${abs_v / 1e9:.2f}B"
        elif abs_v >= 1e6:
            return f"{sign}${abs_v / 1e6:.2f}M"
        return f"{sign}${num:,.2f}"
    except (ValueError, TypeError):
        return str(val)


class SECParser:
    """Parser for SEC submissions, XBRL company facts, and HTML/XML filing documents."""

    @staticmethod
    def parse_recent_filings(
        submissions: Dict[str, Any], cik: str, client: Any, max_per_type: int = 5
    ) -> Dict[str, List[SECFilingMeta]]:
        """
        Parses submissions JSON and groups recent filings by form type:
        10-K, 10-Q, 8-K, 20-F, Form 4.
        """
        result: Dict[str, List[SECFilingMeta]] = {
            "10-K": [],
            "10-Q": [],
            "8-K": [],
            "20-F": [],
            "4": [],
        }

        if not submissions or "filings" not in submissions:
            return result

        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        accns = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])

        total = len(forms)
        for i in range(total):
            form = forms[i]
            if form in result and len(result[form]) < max_per_type:
                accn = accns[i] if i < len(accns) else ""
                pdoc = primary_docs[i] if i < len(primary_docs) else ""
                f_date = dates[i] if i < len(dates) else ""
                r_date = report_dates[i] if i < len(report_dates) else None
                desc = descriptions[i] if i < len(descriptions) else None

                doc_url = client.build_document_url(cik, accn, pdoc)
                meta = SECFilingMeta(
                    form=form,
                    filing_date=f_date,
                    report_date=r_date,
                    accession_number=accn,
                    primary_doc=pdoc,
                    source_url=doc_url,
                    description=desc,
                )
                result[form].append(meta)

        return result

    @staticmethod
    def parse_xbrl_facts(
        company_facts: Dict[str, Any],
        cik: str,
        ticker: str,
        company_name: str,
        client: Any,
    ) -> Tuple[List[SECExtractedFact], Dict[str, Any]]:
        """
        Extracts fundamental financial metrics from standardized XBRL facts:
        Revenue, Net Income, EPS, Operating Income, Cash, Debt, and Derives Free Cash Flow.
        Every fact is attributed with exact source URL and filing date.
        """
        facts_list: List[SECExtractedFact] = []
        metrics_summary: Dict[str, Any] = {}

        if not company_facts or "facts" not in company_facts:
            return facts_list, metrics_summary

        gaap = company_facts.get("facts", {}).get("us-gaap", {})
        if not gaap:
            # Check IFRS if foreign filer
            gaap = company_facts.get("facts", {}).get("ifrs-full", {})

        def get_latest_item(concept_keys: List[str], forms: Tuple[str, ...] = ("10-K", "10-Q")) -> Optional[Dict[str, Any]]:
            """Finds the most recent 10-K or 10-Q filing entry across all provided candidate concept keys."""
            candidates = []
            for key in concept_keys:
                if key in gaap and isinstance(gaap[key], dict):
                    units = gaap[key].get("units", {})
                    if isinstance(units, dict):
                        for u_key, pts in units.items():
                            if isinstance(pts, list):
                                form_pts = [p for p in pts if isinstance(p, dict) and p.get("form") in forms]
                                if form_pts:
                                    form_pts.sort(key=lambda x: (str(x.get("filed", "")), str(x.get("end", ""))))
                                    best_pt = form_pts[-1].copy()
                                    best_pt["_concept"] = key
                                    best_pt["_unit"] = u_key
                                    candidates.append(best_pt)

            if not candidates:
                return None

            # Sort all candidates by filed date, then period end date
            candidates.sort(key=lambda x: (str(x.get("filed", "")), str(x.get("end", ""))))
            return candidates[-1]

        # 1. Revenue
        rev_entry = get_latest_item([
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
        ])
        if rev_entry:
            val = rev_entry.get("val")
            f_date = rev_entry.get("filed", "")
            accn = rev_entry.get("accn", "")
            form = rev_entry.get("form", "10-Q")
            url = client.build_filing_detail_url(cik, accn)
            formatted = format_currency_amount(val)
            metrics_summary["revenue"] = {"raw": val, "formatted": formatted, "form": form, "date": f_date}
            facts_list.append(
                SECExtractedFact(
                    company=company_name,
                    ticker=ticker,
                    claim=f"Total Revenue ({form} Period Ended {rev_entry.get('end', '')})",
                    value=formatted,
                    filing_type=form,
                    filing_date=f_date,
                    accession_number=accn,
                    source_url=url,
                    source_snippet=f"Reported {rev_entry.get('_concept')} of {formatted} in Form {form} (Accession: {accn}).",
                    confidence=1.0,
                )
            )

        # 2. Net Income
        ni_entry = get_latest_item(["NetIncomeLoss", "ProfitLoss"])
        if ni_entry:
            val = ni_entry.get("val")
            f_date = ni_entry.get("filed", "")
            accn = ni_entry.get("accn", "")
            form = ni_entry.get("form", "10-Q")
            url = client.build_filing_detail_url(cik, accn)
            formatted = format_currency_amount(val)
            metrics_summary["net_income"] = {"raw": val, "formatted": formatted, "form": form, "date": f_date}
            facts_list.append(
                SECExtractedFact(
                    company=company_name,
                    ticker=ticker,
                    claim=f"Net Income ({form} Period Ended {ni_entry.get('end', '')})",
                    value=formatted,
                    filing_type=form,
                    filing_date=f_date,
                    accession_number=accn,
                    source_url=url,
                    source_snippet=f"Reported {ni_entry.get('_concept')} of {formatted} in Form {form}.",
                    confidence=1.0,
                )
            )

        # 3. Diluted EPS
        eps_entry = get_latest_item(["EarningsPerShareDiluted", "DilutedEarningsLossPerShare"])
        if eps_entry:
            val = eps_entry.get("val")
            f_date = eps_entry.get("filed", "")
            accn = eps_entry.get("accn", "")
            form = eps_entry.get("form", "10-Q")
            url = client.build_filing_detail_url(cik, accn)
            formatted = f"${val:.2f}" if isinstance(val, (int, float)) else str(val)
            metrics_summary["diluted_eps"] = {"raw": val, "formatted": formatted, "form": form, "date": f_date}
            facts_list.append(
                SECExtractedFact(
                    company=company_name,
                    ticker=ticker,
                    claim=f"Diluted EPS ({form} Period Ended {eps_entry.get('end', '')})",
                    value=formatted,
                    filing_type=form,
                    filing_date=f_date,
                    accession_number=accn,
                    source_url=url,
                    source_snippet=f"Reported Diluted EPS of {formatted} in Form {form}.",
                    confidence=1.0,
                )
            )

        # 4. Operating Income
        op_entry = get_latest_item(["OperatingIncomeLoss"])
        if op_entry:
            val = op_entry.get("val")
            f_date = op_entry.get("filed", "")
            accn = op_entry.get("accn", "")
            form = op_entry.get("form", "10-Q")
            url = client.build_filing_detail_url(cik, accn)
            formatted = format_currency_amount(val)
            metrics_summary["operating_income"] = {"raw": val, "formatted": formatted, "form": form, "date": f_date}
            facts_list.append(
                SECExtractedFact(
                    company=company_name,
                    ticker=ticker,
                    claim=f"Operating Income ({form} Period Ended {op_entry.get('end', '')})",
                    value=formatted,
                    filing_type=form,
                    filing_date=f_date,
                    accession_number=accn,
                    source_url=url,
                    source_snippet=f"Reported Operating Income of {formatted} in Form {form}.",
                    confidence=1.0,
                )
            )

        # 5. Cash & Cash Equivalents
        cash_entry = get_latest_item(["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"])
        if cash_entry:
            val = cash_entry.get("val")
            f_date = cash_entry.get("filed", "")
            accn = cash_entry.get("accn", "")
            form = cash_entry.get("form", "10-Q")
            url = client.build_filing_detail_url(cik, accn)
            formatted = format_currency_amount(val)
            metrics_summary["cash"] = {"raw": val, "formatted": formatted, "form": form, "date": f_date}
            facts_list.append(
                SECExtractedFact(
                    company=company_name,
                    ticker=ticker,
                    claim=f"Cash & Cash Equivalents ({form} as of {cash_entry.get('end', '')})",
                    value=formatted,
                    filing_type=form,
                    filing_date=f_date,
                    accession_number=accn,
                    source_url=url,
                    source_snippet=f"Balance sheet cash & cash equivalents balance of {formatted} in Form {form}.",
                    confidence=1.0,
                )
            )

        # 6. Total Debt
        lt_debt = get_latest_item(["LongTermDebtNoncurrent", "LongTermDebt"])
        curr_debt = get_latest_item(["DebtCurrent", "LongTermDebtCurrent", "ShortTermBorrowings"])
        total_debt_val = 0.0
        debt_f_date = ""
        debt_accn = ""
        debt_form = "10-Q"
        if lt_debt:
            total_debt_val += lt_debt.get("val", 0.0)
            debt_f_date = lt_debt.get("filed", "")
            debt_accn = lt_debt.get("accn", "")
            debt_form = lt_debt.get("form", "10-Q")
        if curr_debt:
            total_debt_val += curr_debt.get("val", 0.0)
            debt_f_date = debt_f_date or curr_debt.get("filed", "")
            debt_accn = debt_accn or curr_debt.get("accn", "")

        if total_debt_val > 0:
            formatted = format_currency_amount(total_debt_val)
            url = client.build_filing_detail_url(cik, debt_accn)
            metrics_summary["debt"] = {"raw": total_debt_val, "formatted": formatted, "form": debt_form, "date": debt_f_date}
            facts_list.append(
                SECExtractedFact(
                    company=company_name,
                    ticker=ticker,
                    claim=f"Total Debt ({debt_form})",
                    value=formatted,
                    filing_type=debt_form,
                    filing_date=debt_f_date,
                    accession_number=debt_accn,
                    source_url=url,
                    source_snippet=f"Combined current and noncurrent debt obligations of {formatted} in Form {debt_form}.",
                    confidence=1.0,
                )
            )

        # 7. Derivable Free Cash Flow (Operating Cash Flow - CapEx)
        ocf_entry = get_latest_item(["NetCashProvidedByUsedInOperatingActivities"])
        capex_entry = get_latest_item([
            "PaymentsToAcquireProductiveAssets",
            "PaymentsToAcquirePropertyPlantAndEquipment",
        ])

        if ocf_entry and capex_entry:
            ocf_val = ocf_entry.get("val", 0.0)
            capex_val = capex_entry.get("val", 0.0)
            fcf_val = ocf_val - capex_val
            f_date = ocf_entry.get("filed", "")
            accn = ocf_entry.get("accn", "")
            form = ocf_entry.get("form", "10-Q")
            url = client.build_filing_detail_url(cik, accn)
            formatted_fcf = format_currency_amount(fcf_val)
            metrics_summary["free_cash_flow"] = {
                "raw": fcf_val,
                "formatted": formatted_fcf,
                "operating_cash_flow": format_currency_amount(ocf_val),
                "capex": format_currency_amount(capex_val),
                "form": form,
                "date": f_date,
            }
            facts_list.append(
                SECExtractedFact(
                    company=company_name,
                    ticker=ticker,
                    claim=f"Derived Free Cash Flow ({form})",
                    value=formatted_fcf,
                    filing_type=form,
                    filing_date=f_date,
                    accession_number=accn,
                    source_url=url,
                    source_snippet=(
                        f"Derived from Cash Flow Statement in Form {form}: "
                        f"Operating Cash Flow ({format_currency_amount(ocf_val)}) "
                        f"minus Capital Expenditures ({format_currency_amount(capex_val)}) = {formatted_fcf}."
                    ),
                    confidence=1.0,
                )
            )

        return facts_list, metrics_summary

    @staticmethod
    def parse_form4_xml(
        xml_content: str,
        cik: str,
        accession_number: str,
        filing_date: str,
        ticker: str,
        company_name: str,
        source_url: str,
    ) -> List[SECInsiderTransaction]:
        """
        Parses Form 4 XML document to extract insider transactions.
        """
        transactions: List[SECInsiderTransaction] = []
        if not xml_content:
            return transactions

        try:
            root = ET.fromstring(xml_content)
        except Exception:
            # If not valid XML, skip
            return transactions

        owner_name = "Insider"
        owner_elem = root.find(".//rptOwnerName")
        if owner_elem is not None and owner_elem.text:
            owner_name = owner_elem.text.strip()

        title_elem = root.find(".//officerTitle")
        officer_title = title_elem.text.strip() if title_elem is not None and title_elem.text else None

        # Check non-derivative transactions
        for trans in root.findall(".//nonDerivativeTransaction"):
            t_date_elem = trans.find(".//transactionDate/value")
            t_date = t_date_elem.text.strip() if t_date_elem is not None and t_date_elem.text else filing_date

            code_elem = trans.find(".//transactionCode")
            raw_code = code_elem.text.strip() if code_elem is not None and code_elem.text else "T"
            code_labels = {
                "S": "Sale (S)",
                "P": "Purchase (P)",
                "M": "Option Exercise (M)",
                "A": "Grant/Award (A)",
                "F": "Tax Withholding (F)",
            }
            trans_type = code_labels.get(raw_code, f"Transaction ({raw_code})")

            shares_elem = trans.find(".//transactionShares/value")
            shares = float(shares_elem.text.strip()) if shares_elem is not None and shares_elem.text else None

            price_elem = trans.find(".//transactionPricePerShare/value")
            price = float(price_elem.text.strip()) if price_elem is not None and price_elem.text else None

            total_val = None
            if shares and price:
                total_val = shares * price

            transactions.append(
                SECInsiderTransaction(
                    reporting_owner=owner_name,
                    officer_title=officer_title,
                    transaction_date=t_date,
                    transaction_type=trans_type,
                    shares=shares,
                    price_per_share=price,
                    total_value=total_val,
                    filing_date=filing_date,
                    accession_number=accession_number,
                    source_url=source_url,
                )
            )

        return transactions

    @staticmethod
    def parse_8k_events(
        html_content: str, filing: SECFilingMeta, ticker: str, company: str
    ) -> List[SECExtractedFact]:
        """
        Extracts material events from Form 8-K filings based on Item disclosures.
        """
        facts: List[SECExtractedFact] = []
        if not html_content:
            return facts

        clean_text = re.sub(r"<[^<]+?>", " ", html_content)
        clean_text = " ".join(clean_text.split())

        item_descriptions = {
            "1.01": "Entry into a Material Definitive Agreement",
            "1.02": "Termination of a Material Definitive Agreement",
            "2.01": "Completion of Acquisition or Disposition of Assets",
            "2.02": "Results of Operations and Financial Condition",
            "3.02": "Unregistered Sales of Equity Securities",
            "5.01": "Changes in Control of Registrant",
            "5.02": "Departure of Directors or Principal Officers / Election of Directors",
            "7.01": "Regulation FD Disclosure",
            "8.01": "Other Events",
        }

        # Find items mentioned
        matches = re.finditer(r"Item\s+(\d+\.\d+)", clean_text, re.IGNORECASE)
        found_items = set()

        for match in matches:
            item_num = match.group(1)
            if item_num in item_descriptions and item_num not in found_items:
                found_items.add(item_num)
                item_title = item_descriptions[item_num]

                # Extract surrounding snippet (up to 300 chars)
                start_idx = match.start()
                snippet = clean_text[start_idx:start_idx + 350]
                if len(snippet) > 300:
                    snippet = snippet[:297] + "..."

                facts.append(
                    SECExtractedFact(
                        company=company,
                        ticker=ticker,
                        claim=f"Material Event: Item {item_num} - {item_title}",
                        value=f"Item {item_num}",
                        filing_type="8-K",
                        filing_date=filing.filing_date,
                        accession_number=filing.accession_number,
                        source_url=filing.source_url,
                        source_snippet=snippet,
                        confidence=1.0,
                    )
                )

        return facts

    @staticmethod
    def parse_risk_factors(
        html_content: str, filing: SECFilingMeta, ticker: str, company: str
    ) -> Optional[SECExtractedFact]:
        """
        Extracts Item 1A Risk Factors summary / excerpt from Form 10-K or 10-Q.
        """
        if not html_content:
            return None

        clean_text = re.sub(r"<[^<]+?>", " ", html_content)
        clean_text = " ".join(clean_text.split())

        # Look for the last / body occurrence of Item 1A
        pos = clean_text.rfind("Item 1A. Risk Factors")
        if pos == -1:
            pos = clean_text.rfind("ITEM 1A. RISK FACTORS")
        if pos == -1:
            pos = clean_text.rfind("Item 1A.")

        if pos != -1:
            snippet = clean_text[pos:pos + 700]
            if len(snippet) > 650:
                snippet = snippet[:647] + "..."
            return SECExtractedFact(
                company=company,
                ticker=ticker,
                claim=f"Risk Factors Disclosure (Item 1A, Form {filing.form})",
                value="Item 1A Disclosure",
                filing_type=filing.form,
                filing_date=filing.filing_date,
                accession_number=filing.accession_number,
                source_url=filing.source_url,
                source_snippet=snippet,
                confidence=1.0,
            )

        return None

    @staticmethod
    def parse_management_commentary(
        html_content: str, filing: SECFilingMeta, ticker: str, company: str
    ) -> Optional[SECExtractedFact]:
        """
        Extracts MD&A (Management's Discussion & Analysis) excerpt from Form 10-K or 10-Q.
        """
        if not html_content:
            return None

        clean_text = re.sub(r"<[^<]+?>", " ", html_content)
        clean_text = " ".join(clean_text.split())

        # In 10-K it's Item 7; in 10-Q it's Item 2
        search_terms = [
            "Item 7. Management's Discussion and Analysis",
            "ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS",
            "Item 2. Management's Discussion and Analysis",
            "ITEM 2. MANAGEMENT'S DISCUSSION AND ANALYSIS",
        ]

        for term in search_terms:
            pos = clean_text.rfind(term)
            if pos != -1:
                snippet = clean_text[pos:pos + 700]
                if len(snippet) > 650:
                    snippet = snippet[:647] + "..."
                return SECExtractedFact(
                    company=company,
                    ticker=ticker,
                    claim=f"Management Commentary (MD&A, Form {filing.form})",
                    value="MD&A Commentary",
                    filing_type=filing.form,
                    filing_date=filing.filing_date,
                    accession_number=filing.accession_number,
                    source_url=filing.source_url,
                    source_snippet=snippet,
                    confidence=1.0,
                )

        return None
