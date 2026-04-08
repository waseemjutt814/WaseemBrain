"""
Security Audit & Compliance Expert Module
Phase 6: Extended Domain Experts

Expert in security auditing, vulnerability assessment, compliance frameworks,
security testing methodologies, and security governance.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum


class ComplianceFramework(Enum):
    """Major compliance frameworks."""
    GDPR = "General Data Protection Regulation (EU)"
    HIPAA = "Health Insurance Portability and Accountability Act (USA)"
    PCI_DSS = "Payment Card Industry Data Security Standard"
    SOC2 = "Service Organization Control 2 (USA)"
    ISO27001 = "Information Security Management System"
    NIST = "National Institute of Standards & Technology Cybersecurity Framework"
    CIS = "Center for Internet Security Controls"


@dataclass
class SecurityControl:
    """Security control definition."""
    name: str
    category: str
    description: str
    implementation_effort: str  # Low, Medium, High
    effectiveness: str  # Category coverage percentage
    frameworks: List[str]
    verification_methods: List[str]


class SecurityAuditKnowledgeBase:
    """Security audit knowledge base."""
    
    VULNERABILITY_CATEGORIES = [
        {
            "name": "OWASP Top 10 2024",
            "vulnerabilities": [
                "Broken Access Control",
                "Cryptographic Failures",
                "Injection",
                "Insecure Design",
                "Security Misconfiguration",
                "Vulnerable and Outdated Components",
                "Authentication Failures",
                "Software and Data Integrity Failures",
                "Logging and Monitoring Failures",
                "Server-Side Request Forgery (SSRF)"
            ]
        },
        {
            "name": "CWE Top 25 (2023)",
            "categories": [
                "Out-of-bounds Write",
                "Cross-site Scripting (XSS)",
                "Improper Input Validation",
                "Path Traversal",
                "Cross-Site Request Forgery",
                "Unrestricted Upload of File",
                "Broken Authentication",
                "XML External Entities (XXE)",
                "Server-Side Template Injection",
                "Insecure Deserialization"
            ]
        }
    ]
    
    AUDIT_PROCEDURES = [
        {
            "name": "Network Security Audit",
            "scope": ["Firewall rules", "Network segmentation", "VPN configuration", "Intrusion detection"],
            "tools": ["Nessus", "OpenVAS", "Wireshark", "nmap", "Metasploit"],
            "duration": "3-5 days",
            "report_sections": ["Findings", "Risk ratings", "Remediation timeline"]
        },
        {
            "name": "Application Security Audit",
            "scope": ["OWASP Top 10", "Code quality", "API security", "Authentication/Authorization"],
            "tools": ["Burp Suite", "OWASP ZAP", "SonarQube", "Checkmarx"],
            "duration": "5-10 days",
            "report_sections": ["Vulnerability findings", "Code review", "Recommendations"]
        },
        {
            "name": "Database Security Audit",
            "scope": ["Access controls", "Data encryption", "SQL injection", "Backup/Recovery"],
            "tools": ["SQL Injection testers", "Database scanners", "Encryption validators"],
            "duration": "2-4 days",
            "report_sections": ["Database security posture", "Data protection", "Access review"]
        },
        {
            "name": "Infrastructure Audit",
            "scope": ["Patch management", "Server hardening", "Cloud configuration", "Secrets management"],
            "tools": ["Cloud auditing tools", "Configuration scanners", "Compliance checkers"],
            "duration": "3-7 days",
            "report_sections": ["Infrastructure findings", "Compliance gaps", "Hardening steps"]
        },
        {
            "name": "Compliance Audit",
            "scope": ["Policy enforcement", "Documentation", "Training records", "Access logs"],
            "tools": ["Compliance management platforms", "Document review"],
            "duration": "7-14 days",
            "report_sections": ["Compliance status", "Policy gaps", "Action plan"]
        }
    ]
    
    SECURITY_CONTROLS = [
        SecurityControl(
            name="Multi-Factor Authentication (MFA)",
            category="Access Control",
            description="Require multiple verification methods (password + device token)",
            implementation_effort="Medium",
            effectiveness="90% reduction in account compromise",
            frameworks=["GDPR", "HIPAA", "PCI-DSS", "SOC2", "NIST"],
            verification_methods=["Review MFA deployment logs", "Test MFA enrollment"]
        ),
        SecurityControl(
            name="End-to-End Encryption",
            category="Data Protection",
            description="Encrypt data at rest and in transit using strong algorithms",
            implementation_effort="Medium",
            effectiveness="Protects confidentiality of all data",
            frameworks=["GDPR", "HIPAA", "PCI-DSS", "SOC2"],
            verification_methods=["Check encryption configuration", "Test data in transit"]
        ),
        SecurityControl(
            name="Intrusion Detection/Prevention (IDS/IPS)",
            category="Threat Detection",
            description="Monitor and block suspicious network traffic patterns",
            implementation_effort="Medium",
            effectiveness="80% detection of network attacks",
            frameworks=["NIST", "CIS", "SOC2"],
            verification_methods=["Review IDS/IPS logs", "Test attack detection"]
        ),
        SecurityControl(
            name="Web Application Firewall (WAF)",
            category="Application Security",
            description="Block malicious requests to web applications (SQL injection, XSS, etc.)",
            implementation_effort="Low",
            effectiveness="95% of OWASP Top 10 attacks blocked",
            frameworks=["PCI-DSS", "SOC2", "NIST"],
            verification_methods=["Configuration review", "WAF rule testing"]
        ),
        SecurityControl(
            name="Security Information & Event Management (SIEM)",
            category="Logging & Monitoring",
            description="Centralize, correlate, and analyze security logs for anomalies",
            implementation_effort="High",
            effectiveness="Early detection of security incidents",
            frameworks=["HIPAA", "PCI-DSS", "SOC2", "NIST"],
            verification_methods=["Review SIEM dashboards", "Test alert generation"]
        ),
        SecurityControl(
            name="Vulnerability Management Program",
            category="Vulnerability Management",
            description="Regular scanning, prioritization, and remediation of vulnerabilities",
            implementation_effort="Medium",
            effectiveness="Reduces exploitable vulnerabilities by 70%",
            frameworks=["NIST", "CIS", "SOC2"],
            verification_methods=["Review scan reports", "Track remediation timeline"]
        ),
        SecurityControl(
            name="Security Awareness Training",
            category="Personnel & Training",
            description="Annual training on security policies, phishing, and incident reporting",
            implementation_effort="Low",
            effectiveness="Reduces human security errors by 40%",
            frameworks=["GDPR", "HIPAA", "PCI-DSS", "SOC2", "NIST"],
            verification_methods=["Review training records", "Test knowledge via assessments"]
        ),
        SecurityControl(
            name="Incident Response Plan",
            category="Incident Management",
            description="Documented procedures for detection, containment, and recovery from incidents",
            implementation_effort="Medium",
            effectiveness="Reduces incident impact and recovery time",
            frameworks=["HIPAA", "NIST", "SOC2"],
            verification_methods=["Review plan documentation", "Conduct incident simulation"]
        )
    ]
    
    KNOWLEDGE = VULNERABILITY_CATEGORIES + AUDIT_PROCEDURES + SECURITY_CONTROLS


class SecurityAuditExpert:
    """Security Audit & Compliance Expert."""
    
    def __init__(self):
        self.kb = SecurityAuditKnowledgeBase()
        self.name = "Security Audit & Compliance Expert"
        self.specialties = [
            "Vulnerability Assessment",
            "Penetration Testing",
            "Compliance Frameworks",
            "Security Auditing",
            "Risk Assessment",
            "Incident Response",
            "Security Governance"
        ]
    
    def plan_security_audit(self, organization_type: str, scale: str) -> Dict[str, Any]:
        """Plan comprehensive security audit for organization."""
        audit_plans = {
            "fintech-large": {
                "duration_days": 30,
                "phases": [
                    "Phase 1: Scope & Planning (Days 1-2)",
                    "Phase 2: Network Security Audit (Days 3-7)",
                    "Phase 3: Application Security Audit (Days 8-15)",
                    "Phase 4: Database & Data Security (Days 16-19)",
                    "Phase 5: Compliance Review (Days 20-26)",
                    "Phase 6: Reporting & Remediation Planning (Days 27-30)"
                ],
                "frameworks": ["PCI-DSS", "SOC2", "NIST", "GDPR"],
                "key_areas": [
                    "Payment processing security",
                    "Customer data protection",
                    "Fraud prevention systems",
                    "Access control review",
                    "Audit logging completeness"
                ],
                "required_team": [
                    "Network security specialist",
                    "Application security engineer",
                    "Database security expert",
                    "Compliance officer"
                ]
            },
            "healthcare-medium": {
                "duration_days": 14,
                "phases": [
                    "Phase 1: Planning & Kickoff (Days 1)",
                    "Phase 2: Infrastructure Security (Days 2-4)",
                    "Phase 3: Application & Data Security (Days 5-10)",
                    "Phase 4: HIPAA Compliance Check (Days 11-13)",
                    "Phase 5: Reporting (Day 14)"
                ],
                "frameworks": ["HIPAA", "NIST"],
                "key_areas": [
                    "Protected Health Information (PHI) security",
                    "Encryption of patient data at rest and in transit",
                    "Access control for patient records",
                    "Audit trail completeness",
                    "Business associate compliance"
                ],
                "required_team": [
                    "Healthcare IT security specialist",
                    "HIPAA compliance auditor"
                ]
            },
            "saas-small": {
                "duration_days": 5,
                "phases": [
                    "Phase 1: Kickoff (1 day)",
                    "Phase 2: Application & API Security (2 days)",
                    "Phase 3: Infrastructure & Compliance (1.5 days)",
                    "Phase 4: Reporting (0.5 days)"
                ],
                "frameworks": ["SOC2", "GDPR"],
                "key_areas": [
                    "API security",
                    "Customer data isolation",
                    "Access control review",
                    "Monitoring and logging",
                    "Incident response procedures"
                ],
                "required_team": [
                    "Application security engineer"
                ]
            }
        }
        
        key = f"{organization_type}-{scale}"
        return audit_plans.get(key, audit_plans["saas-small"])
    
    def compliance_readiness_assessment(self, framework: str) -> Dict[str, Any]:
        """Assess compliance readiness for specific framework."""
        assessments = {
            "GDPR": {
                "critical_areas": [
                    "Data Protection Officer (DPO) designation",
                    "Data Processing Agreements with vendors",
                    "Privacy Impact Assessment (DPIA) process",
                    "Data retention and deletion procedures",
                    "Breach notification procedures (72 hours)",
                    "Right to access, rectification, erasure processes"
                ],
                "timeline": "3-12 months for implementation",
                "penalties": "€10M or 2% of global revenue (whichever is higher)",
                "key_assurance": "Regular audits and documentation review"
            },
            "HIPAA": {
                "critical_areas": [
                    "Business Associate Agreements (BAAs)",
                    "ePHI encryption (AES-256)",
                    "Access control and role-based access",
                    "Audit controls (logging and monitoring)",
                    "Incident response and breach notification",
                    "Workforce security and training"
                ],
                "timeline": "6-12 months for comprehensive implementation",
                "penalties": "$100-$50,000 per violation per year",
                "key_assurance": "Annual compliance certification and OCR audits"
            },
            "PCI_DSS": {
                "critical_areas": [
                    "Network segmentation (card data isolated)",
                    "Encryption of cardholder data at rest and in transit",
                    "Access control and role identification",
                    "Regular security testing and vulnerability scanning",
                    "Firewall configuration and testing",
                    "Strong cryptography and key management"
                ],
                "timeline": "3-6 months for remediation",
                "penalties": "$5,000-$100,000 per month non-compliance",
                "key_assurance": "Annual Qualified Security Assessor (QSA) audit or Self-Assessment"
            },
            "SOC2": {
                "critical_areas": [
                    "Access control policies and procedures",
                    "Change management process",
                    "System availability and sustainability",
                    "Logical and physical security",
                    "Monitoring and incident management",
                    "Security configuration standards"
                ],
                "timeline": "3-6 months of operations pre-audit, then annual attestation",
                "penalties": "Loss of customer trust and contract cancellation",
                "key_assurance": "Annual SOC2 Type II audit by independent auditor"
            }
        }
        
        return assessments.get(framework, {"status": "Framework not found"})
    
    def vulnerability_prioritization(self, vulnerabilities: List[Dict]) -> List[Dict]:
        """Prioritize vulnerabilities based on risk scoring."""
        prioritized = []
        
        for vuln in vulnerabilities:
            # Calculate risk score based on CVSS-like scoring
            severity = {"critical": 9, "high": 7, "medium": 5, "low": 3}.get(
                vuln.get("severity", "medium").lower(), 5
            )
            exploitability = 1.0 if vuln.get("exploitable") else 0.5
            business_impact = 1.0 if vuln.get("affects_production") else 0.5
            
            risk_score = severity * exploitability * business_impact
            
            vuln_with_score = {
                **vuln,
                "risk_score": risk_score,
                "remediation_timeline": self._get_remediation_timeline(severity)
            }
            prioritized.append(vuln_with_score)
        
        return sorted(prioritized, key=lambda x: x.get("risk_score", 0), reverse=True)
    
    @staticmethod
    def _get_remediation_timeline(severity: int) -> str:
        if severity >= 9:
            return "Immediate (0-24 hours)"
        elif severity >= 7:
            return "Urgent (1-7 days)"
        elif severity >= 5:
            return "Important (1-30 days)"
        else:
            return "Standard (30+ days)"
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get key security metrics for tracking."""
        return {
            "vulnerability_metrics": {
                "total_vulnerabilities": "Track by severity level",
                "mean_time_to_remediate": "Average days to fix vulnerabilities",
                "vulnerability_density": "Vulnerabilities per 1000 lines of code",
                "remediation_rate": "% of identified vulnerabilities fixed"
            },
            "compliance_metrics": {
                "compliance_coverage": "% of required controls implemented",
                "control_effectiveness": "% of controls functioning properly",
                "audit_findings": "Number of audit findings",
                "remediation_effectiveness": "% of audit findings resolved"
            },
            "incident_metrics": {
                "mean_time_to_detect": "Average time to discover incident",
                "mean_time_to_respond": "Average time to take action on incident",
                "mean_time_to_contain": "Average time to contain incident",
                "incident_recurrence": "% of similar incidents recurring"
            },
            "security_awareness": {
                "phishing_click_rate": "% of employees clicking phishing emails",
                "training_completion": "% of employees completing security training",
                "policy_violations": "Number of documented policy violations",
                "incident_reporting_rate": "% of incidents reported by employees"
            }
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get expert summary."""
        return {
            "expert": self.name,
            "specialties": self.specialties,
            "audit_procedures": len(self.kb.AUDIT_PROCEDURES),
            "security_controls": len(self.kb.SECURITY_CONTROLS),
            "vulnerability_categories": sum(
                len(cat.get("vulnerabilities", [])) + len(cat.get("categories", []))
                for cat in self.kb.VULNERABILITY_CATEGORIES
            ),
            "compliance_frameworks": len(ComplianceFramework),
        }


if __name__ == "__main__":
    expert = SecurityAuditExpert()
    print(f"\n{expert.name}")
    print(f"Specialties: {', '.join(expert.specialties)}")
    
    print("\nAudit Plan for FinTech Organization (Large):")
    plan = expert.plan_security_audit("fintech", "large")
    print(f"Duration: {plan['duration_days']} days")
    print(f"Frameworks: {', '.join(plan['frameworks'])}")
    print(f"Phases: {len(plan['phases'])} phases")
    
    print("\nGDPR Compliance Readiness:")
    gdpr = expert.compliance_readiness_assessment("GDPR")
    print(f"Timeline: {gdpr['timeline']}")
    print(f"Critical areas: {len(gdpr['critical_areas'])}")
    
    print("\nExpert Summary:")
    summary = expert.get_summary()
    print(f"Audit procedures: {summary['audit_procedures']}")
    print(f"Security controls: {summary['security_controls']}")
    print(f"Compliance frameworks: {summary['compliance_frameworks']}")
