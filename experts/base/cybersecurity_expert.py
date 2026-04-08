"""Cybersecurity & Network Security Expert Module.

Provides comprehensive knowledge on network security, penetration testing,
vulnerability assessment, defensive strategies, and ethical hacking practices.
"""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Optional


@dataclass
class SecurityConcept:
    """Security concept with explanation and examples."""
    name: str
    category: str
    description: str
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    defense_strategy: str
    detection_method: str
    best_practices: list[str]


class CybersecurityKnowledgeBase:
    """Comprehensive cybersecurity knowledge base."""
    
    CONCEPTS = [
        SecurityConcept(
            name="SQL Injection",
            category="Web Vulnerability",
            description="Attacker inserts malicious SQL code into input fields to manipulate database queries",
            risk_level="CRITICAL",
            defense_strategy="Use parameterized queries, prepared statements, input validation",
            detection_method="WAF rules, query monitoring, input pattern analysis",
            best_practices=[
                "Always use parameterized queries",
                "Validate and sanitize all user input",
                "Use ORM frameworks when possible",
                "Implement principle of least privilege for database accounts",
                "Regular security testing and code reviews",
            ]
        ),
        SecurityConcept(
            name="Cross-Site Scripting (XSS)",
            category="Web Vulnerability",
            description="Attacker injects malicious JavaScript into web pages viewed by other users",
            risk_level="HIGH",
            defense_strategy="HTML encoding, Content Security Policy, input validation",
            detection_method="Security headers analysis, JavaScript sandboxing, content inspection",
            best_practices=[
                "Implement Content Security Policy (CSP)",
                "HTML-encode all user output",
                "Use security-focused templating engines",
                "Maintain XSS prevention in all input points",
            ]
        ),
        SecurityConcept(
            name="Man-in-the-Middle (MITM)",
            category="Network Attack",
            description="Attacker intercepts communication between two parties without their knowledge",
            risk_level="CRITICAL",
            defense_strategy="TLS/SSL encryption, certificate pinning, secure key exchange",
            detection_method="Certificate monitoring, traffic analysis, anomaly detection",
            best_practices=[
                "Enforce HTTPS/TLS 1.3 or higher",
                "Implement certificate pinning for critical connections",
                "Use strong key exchange algorithms (ECDHE)",
                "Validate certificate chains properly",
                "Monitor for invalid certificates",
            ]
        ),
        SecurityConcept(
            name="DDoS Attack",
            category="Network Attack",
            description="Attacker floods target with requests to make service unavailable",
            risk_level="HIGH",
            defense_strategy="Rate limiting, traffic filtering, CDN, load balancing",
            detection_method="Traffic analysis, anomaly detection, pattern recognition",
            best_practices=[
                "Implement rate limiting and throttling",
                "Use CDN for DDoS mitigation",
                "Configure firewalls with SYN flood protection",
                "Monitor bandwidth and connection patterns",
                "Have incident response plan",
            ]
        ),
        SecurityConcept(
            name="Brute Force Attack",
            category="Authentication Attack",
            description="Attacker tries many password combinations to gain unauthorized access",
            risk_level="MEDIUM",
            defense_strategy="Strong passwords, account lockout, MFA, rate limiting",
            detection_method="Failed login monitoring, IP reputation, behavioral analysis",
            best_practices=[
                "Enforce strong password policies",
                "Implement account lockout after failed attempts",
                "Use multi-factor authentication (MFA)",
                "Rate limit login attempts",
                "Monitor for suspicious login patterns",
            ]
        ),
    ]
    
    DEFENSIVE_MEASURES = [
        {
            "layer": "Network Layer",
            "measures": [
                "Firewalls (stateful packet filtering)",
                "Intrusion Detection Systems (IDS)",
                "Intrusion Prevention Systems (IPS)",
                "DDoS protection services",
                "Network segmentation and VLANs",
                "VPN for encrypted tunnels",
            ]
        },
        {
            "layer": "Application Layer",
            "measures": [
                "Web Application Firewall (WAF)",
                "Input validation and sanitization",
                "Secure coding practices",
                "Security testing (SAST, DAST)",
                "API security controls",
                "Rate limiting and throttling",
            ]
        },
        {
            "layer": "Data Layer",
            "measures": [
                "Encryption at rest (AES-256)",
                "Encryption in transit (TLS 1.3)",
                "Database access controls",
                "Data masking and tokenization",
                "Secure key management",
                "Regular backups with encryption",
            ]
        },
        {
            "layer": "Access Control",
            "measures": [
                "Multi-factor authentication (MFA)",
                "Role-based access control (RBAC)",
                "Principle of least privilege",
                "Strong password policies",
                "Regular access reviews",
                "Session management and timeouts",
            ]
        },
    ]
    
    PENETRATION_TESTING_STAGES = [
        {
            "stage": "Reconnaissance",
            "activities": [
                "Passive information gathering",
                "Domain enumeration",
                "DNS reconnaissance",
                "WHOIS lookups",
                "Port scanning preparation",
            ],
            "tools": ["OSINT", "whois", "nslookup", "theHarvester"],
        },
        {
            "stage": "Scanning",
            "activities": [
                "Port scanning",
                "Service enumeration",
                "Banner grabbing",
                "Vulnerability detection",
            ],
            "tools": ["nmap", "Nessus", "OpenVAS"],
        },
        {
            "stage": "Enumeration",
            "activities": [
                "Service version detection",
                "User enumeration",
                "Share enumeration",
                "Resource discovery",
            ],
            "tools": ["enum4linux", "smbclient"],
        },
        {
            "stage": "Exploitation",
            "activities": [
                "Vulnerability testing",
                "Payload delivery",
                "Access establishment",
                "Escalation attempts",
            ],
            "tools": ["Metasploit", "Exploit-DB"],
        },
        {
            "stage": "Post-Exploitation",
            "activities": [
                "Maintaining access",
                "Data collection",
                "Lateral movement",
                "Privilege escalation",
            ],
            "tools": ["meterpreter", "mimikatz"],
        },
        {
            "stage": "Reporting",
            "activities": [
                "Vulnerability documentation",
                "Risk assessment",
                "Remediation recommendations",
                "Executive summary",
            ],
            "tools": ["Report templates"],
        },
    ]
    
    ENCRYPTION_STANDARDS = [
        {
            "name": "AES-256",
            "type": "Symmetric encryption",
            "use_case": "Data at rest encryption",
            "strength": "256-bit keys, NIST approved",
        },
        {
            "name": "RSA-2048+",
            "type": "Asymmetric encryption",
            "use_case": "Key exchange, digital signatures",
            "strength": "2048-bit minimum, 4096-bit recommended",
        },
        {
            "name": "TLS 1.3",
            "type": "Transport security",
            "use_case": "Secure communication",
            "strength": "Cipher suites with forward secrecy",
        },
        {
            "name": "SHA-256/SHA-3",
            "type": "Hashing",
            "use_case": "Data integrity, password hashing",
            "strength": "Cryptographically secure",
        },
    ]
    
    COMPLIANCE_FRAMEWORKS = [
        {
            "name": "OWASP Top 10",
            "focus": "Web application security",
            "critical_items": [
                "Injection attacks",
                "Authentication flaws",
                "Sensitive data exposure",
                "XML external entities",
                "Access control violations",
            ]
        },
        {
            "name": "NIST Cybersecurity Framework",
            "focus": "Holistic security approach",
            "functions": ["Identify", "Protect", "Detect", "Respond", "Recover"],
        },
        {
            "name": "ISO/IEC 27001",
            "focus": "Information security management",
            "domains": ["Asset management", "Access control", "Incident management"],
        },
    ]
    
    def get_vulnerability_details(self, vuln_name: str) -> Optional[SecurityConcept]:
        """Get details about a specific vulnerability."""
        for concept in self.CONCEPTS:
            if concept.name.lower() == vuln_name.lower():
                return concept
        return None
    
    def get_defenses_for_layer(self, layer: str) -> Optional[dict]:
        """Get defensive measures for a specific layer."""
        for measure_set in self.DEFENSIVE_MEASURES:
            if measure_set["layer"].lower() == layer.lower():
                return measure_set
        return None
    
    def get_penetration_test_guide(self) -> list[dict]:
        """Get complete pentest methodology."""
        return self.PENETRATION_TESTING_STAGES


class CybersecurityExpert:
    """Expert module for cybersecurity and network security."""

    def __init__(self):
        self.kb = CybersecurityKnowledgeBase()
        self.knowledge_base = SimpleNamespace(
            vulnerabilities=list(self.kb.CONCEPTS),
            defense_layers=list(self.kb.DEFENSIVE_MEASURES),
            pentest_stages=list(self.kb.PENETRATION_TESTING_STAGES),
            encryption_standards=list(self.kb.ENCRYPTION_STANDARDS),
            compliance_frameworks=list(self.kb.COMPLIANCE_FRAMEWORKS),
        )
        self.name = "Cybersecurity Expert"
        self.specialties = [
            "Network Security",
            "Penetration Testing",
            "Vulnerability Assessment",
            "Security Architecture",
            "Incident Response",
            "Ethical Hacking",
        ]

    def analyze_vulnerability_details(self, vuln_name: str) -> dict[str, object]:
        vuln = self.kb.get_vulnerability_details(vuln_name)
        if not vuln:
            return {
                "error": f"Unknown vulnerability: {vuln_name}",
                "available_vulnerabilities": [c.name for c in self.kb.CONCEPTS],
            }
        return {
            "vulnerability": vuln.name,
            "category": vuln.category,
            "description": vuln.description,
            "risk_level": vuln.risk_level,
            "defense_strategy": vuln.defense_strategy,
            "detection_method": vuln.detection_method,
            "best_practices": vuln.best_practices,
        }

    def analyze_vulnerability(self, vuln_name: str) -> str:
        details = self.analyze_vulnerability_details(vuln_name)
        if "error" in details:
            examples = ', '.join(details['available_vulnerabilities'][:3])
            return f"Unknown vulnerability: {vuln_name}. Known examples include {examples}."
        return (
            f"{details['vulnerability']} is a {str(details['risk_level']).lower()} risk {details['category']} vulnerability. "
            f"{details['description']}. Primary defense: {details['defense_strategy']}. "
            f"Detection: {details['detection_method']}."
        )

    def recommend_defenses_details(self, attack_type: str = "all") -> dict[str, object]:
        layers = []
        normalized = attack_type.lower()
        if normalized in {"network", "all"}:
            layers.append(self.kb.get_defenses_for_layer("Network Layer"))
        if normalized in {"application", "all"}:
            layers.append(self.kb.get_defenses_for_layer("Application Layer"))
        if normalized in {"data", "all"}:
            layers.append(self.kb.get_defenses_for_layer("Data Layer"))
        if normalized in {"access", "all"}:
            layers.append(self.kb.get_defenses_for_layer("Access Control"))
        return {
            "attack_type": attack_type,
            "defensive_measures": [layer for layer in layers if layer],
        }

    def recommend_defenses(self, attack_type: str = "all") -> str:
        details = self.recommend_defenses_details(attack_type)
        measures = [measure for layer in details['defensive_measures'] for measure in layer['measures'][:2]]
        if not measures:
            measures = ["Use defense-in-depth controls"]
        return f"Recommended defenses for {attack_type}: {', '.join(measures[:6])}."

    def get_summary(self) -> str:
        return (
            f"Cybersecurity Expert covering {len(self.knowledge_base.vulnerabilities)} vulnerabilities, "
            f"{len(self.knowledge_base.defense_layers)} defense layers, and "
            f"{len(self.knowledge_base.compliance_frameworks)} compliance frameworks."
        )

    def answer_query(self, query: str) -> str:
        lowered = query.lower()
        for concept in self.kb.CONCEPTS:
            if concept.name.lower() in lowered:
                return self.analyze_vulnerability(concept.name)
        if any(token in lowered for token in ["defense", "protect", "secure", "mitigation"]):
            return self.recommend_defenses("all")
        if "compliance" in lowered or "nist" in lowered or "owasp" in lowered:
            frameworks = ', '.join(item['name'] for item in self.kb.COMPLIANCE_FRAMEWORKS[:3])
            return f"Security compliance should start with {frameworks}, backed by defense-in-depth and regular review cycles."
        if "pentest" in lowered or "penetration" in lowered:
            stages = ', '.join(stage['stage'] for stage in self.kb.PENETRATION_TESTING_STAGES[:4])
            return f"A sound penetration-testing workflow covers {stages}, then reporting and remediation."
        return self.get_summary()
