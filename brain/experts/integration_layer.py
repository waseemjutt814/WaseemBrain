"""
Phase 4: Real Expert Integration Layer
Integrates all 5 specialized experts (Cybersecurity, Cryptography, Algorithms, 
Engineering, Advanced Security) with the WaseemBrainCoordinator.

This is a working integration layer that routes queries to appropriate experts
and collects their responses for unified processing.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import re


class ExpertDomain(Enum):
    """Expert specialization domains."""
    CYBERSECURITY = "cybersecurity"
    CRYPTOGRAPHY = "cryptography"
    ALGORITHMS = "algorithms"
    ENGINEERING = "engineering"
    ADVANCED_SECURITY = "advanced_security"


@dataclass
class ExpertQuery:
    """Query routed to specific expert."""
    text: str
    domain: ExpertDomain
    context: Optional[Dict] = None
    confidence: float = 0.0


@dataclass
class ExpertResponse:
    """Response from expert."""
    expert_domain: ExpertDomain
    content: str
    method_used: str
    confidence: float
    citations: List[str] = None
    
    def __post_init__(self):
        if self.citations is None:
            self.citations = []


class ExpertRouter:
    """Routes queries to appropriate experts based on content analysis."""
    
    # Domain keywords mapping for intelligent routing
    DOMAIN_KEYWORDS = {
        ExpertDomain.CYBERSECURITY: {
            "keywords": [
                "sql injection", "xss", "vulnerability", "attack", "defense",
                "penetration", "pentest", "network security",
                "owasp", "breach", "compromise", "exploit", "malware"
            ],
            "confidence_boost": ["security", "hack", "threat", "vulnerable"]
        },
        ExpertDomain.CRYPTOGRAPHY: {
            "keywords": [
                "aes", "rsa", "encryption", "cipher", "algorithm", "hash",
                "tls", "ssl", "key", "crypto", "sha256", "bcrypt",
                "quantum", "post-quantum", "protocol", "certificate"
            ],
            "confidence_boost": ["encrypt", "decrypt", "secure communication", "key management"]
        },
        ExpertDomain.ALGORITHMS: {
            "keywords": [
                "sort", "search", "complexity", "big-o", "algorithm", "data structure",
                "graph", "dynamic programming", "recursion", "optimization",
                "bfs", "dfs", "dijkstra", "binary search", "quicksort"
            ],
            "confidence_boost": ["efficient", "performance", "time complexity"]
        },
        ExpertDomain.ENGINEERING: {
            "keywords": [
                "architecture", "design", "scalability", "microservices", "system",
                "database", "deployment", "load balancing", "caching",
                "distributed", "kubernetes", "docker", "monitoring"
            ],
            "confidence_boost": ["scale", "production", "infrastructure", "devops"]
        },
        ExpertDomain.ADVANCED_SECURITY: {
            "keywords": [
                "threat modeling", "zero trust", "sandbox", "incident response",
                "compliance", "gdpr", "pci-dss", "hipaa", "automation",
                "suspicious", "detection", "response", "containment", "firewall",
                "access control", "security audit"
            ],
            "confidence_boost": ["advanced", "threat", "compliance", "automation"]
        }
    }
    
    def route_query(self, query: str) -> List[ExpertQuery]:
        """
        Analyze query and route to appropriate expert(s).
        Returns list of expert queries for single or multiple experts.
        """
        query_lower = query.lower()
        scored_domains: Dict[ExpertDomain, float] = {}
        
        # Score each domain based on keyword matches
        for domain, config in self.DOMAIN_KEYWORDS.items():
            score = 0.0
            matches = 0
            
            # Check keyword matches
            for keyword in config["keywords"]:
                if keyword in query_lower:
                    matches += 1
                    # Check if confidence boost keywords present
                    for boost_keyword in config["confidence_boost"]:
                        if boost_keyword in query_lower:
                            score += 1.5
                        else:
                            score += 1.0
            
            if matches > 0:
                score = min(score / max(1, len(config["keywords"])), 1.0)
                scored_domains[domain] = score
        
        # If no high confidence match, return multi-expert approach
        if not scored_domains:
            # Default to algorithms for general problem-solving
            return [ExpertQuery(text=query, domain=ExpertDomain.ALGORITHMS, confidence=0.5)]
        
        # Return top matched experts (single or dual expert approach)
        sorted_domains = sorted(scored_domains.items(), key=lambda x: x[1], reverse=True)
        
        # If highest confidence > 0.7, use single expert
        if sorted_domains[0][1] > 0.7:
            return [ExpertQuery(
                text=query,
                domain=sorted_domains[0][0],
                confidence=sorted_domains[0][1]
            )]
        
        # If confidence moderate, use top 2 experts
        if len(sorted_domains) > 1 and sorted_domains[1][1] > 0.3:
            return [
                ExpertQuery(text=query, domain=sorted_domains[0][0], confidence=sorted_domains[0][1]),
                ExpertQuery(text=query, domain=sorted_domains[1][0], confidence=sorted_domains[1][1])
            ]
        
        return [ExpertQuery(text=query, domain=sorted_domains[0][0], confidence=sorted_domains[0][1])]


class ExpertIntegrator:
    """Integrates all 5 experts and coordinates their responses."""
    
    def __init__(self):
        from experts.base.cybersecurity_expert import CybersecurityExpert
        from experts.base.cryptography_expert import CryptographyExpert
        from experts.base.algorithms_expert import AlgorithmsExpert
        from experts.base.engineering_expert import SystemEngineeringExpert
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        # Initialize all experts
        self.experts = {
            ExpertDomain.CYBERSECURITY: CybersecurityExpert(),
            ExpertDomain.CRYPTOGRAPHY: CryptographyExpert(),
            ExpertDomain.ALGORITHMS: AlgorithmsExpert(),
            ExpertDomain.ENGINEERING: SystemEngineeringExpert(),
            ExpertDomain.ADVANCED_SECURITY: AdvancedSecurityExpert(),
        }
        self.router = ExpertRouter()
    
    def query_expert(self, expert_query: ExpertQuery) -> ExpertResponse:
        """Query a specific expert and get structured response."""
        expert = self.experts.get(expert_query.domain)
        
        if not expert:
            return ExpertResponse(
                expert_domain=expert_query.domain,
                content=f"Expert not found for domain: {expert_query.domain}",
                method_used="none",
                confidence=0.0
            )
        
        # Route to appropriate method based on domain and query
        response_content = ""
        method_used = ""
        
        if expert_query.domain == ExpertDomain.CYBERSECURITY:
            if "vulnerability" in expert_query.text.lower():
                response_content = str(expert.analyze_vulnerability(
                    self._extract_vuln_name(expert_query.text)
                ))
                method_used = "analyze_vulnerability"
            elif "defense" in expert_query.text.lower():
                response_content = str(expert.recommend_defenses(
                    self._extract_attack_type(expert_query.text)
                ))
                method_used = "recommend_defenses"
            elif "pentest" in expert_query.text.lower():
                response_content = str(expert.get_pentesting_methodology())
                method_used = "get_pentesting_methodology"
            elif "compliance" in expert_query.text.lower():
                response_content = str(expert.get_compliance_guide())
                method_used = "get_compliance_guide"
            else:
                response_content = str(expert.analyze_vulnerability("SQL Injection"))
                method_used = "default_vulnerability"
        
        elif expert_query.domain == ExpertDomain.CRYPTOGRAPHY:
            if "algorithm" in expert_query.text.lower():
                response_content = str(expert.analyze_algorithm(
                    self._extract_algorithm(expert_query.text)
                ))
                method_used = "analyze_algorithm"
            elif "protocol" in expert_query.text.lower():
                response_content = str(expert.get_protocol_security_config("TLS-1.3"))
                method_used = "get_protocol_security_config"
            elif "quantum" in expert_query.text.lower():
                response_content = str(expert.get_quantum_readiness())
                method_used = "get_quantum_readiness"
            elif "key" in expert_query.text.lower():
                response_content = str(expert.get_key_sizes())
                method_used = "get_key_sizes"
            else:
                response_content = str(expert.recommend_encryption("data-protection"))
                method_used = "recommend_encryption"
        
        elif expert_query.domain == ExpertDomain.ALGORITHMS:
            if "sort" in expert_query.text.lower():
                response_content = str(expert.recommend_algorithm("sorting"))
                method_used = "recommend_algorithm_sorting"
            elif "search" in expert_query.text.lower():
                response_content = str(expert.recommend_algorithm("searching"))
                method_used = "recommend_algorithm_searching"
            elif "complexity" in expert_query.text.lower():
                response_content = str(expert.get_complexity_guide())
                method_used = "get_complexity_guide"
            elif "data structure" in expert_query.text.lower():
                response_content = str(expert.select_data_structure("search"))
                method_used = "select_data_structure"
            elif "dynamic" in expert_query.text.lower():
                response_content = str(expert.get_dynamic_programming_help())
                method_used = "get_dynamic_programming_help"
            else:
                response_content = str(expert.recommend_algorithm("general"))
                method_used = "recommend_algorithm_general"
        
        elif expert_query.domain == ExpertDomain.ENGINEERING:
            if "architecture" in expert_query.text.lower():
                response_content = str(expert.recommend_architecture("scalability"))
                method_used = "recommend_architecture"
            elif "database" in expert_query.text.lower():
                response_content = str(expert.design_database("transactional"))
                method_used = "design_database"
            elif "scale" in expert_query.text.lower():
                response_content = str(expert.scaling_strategy("database"))
                method_used = "scaling_strategy"
            elif "deploy" in expert_query.text.lower():
                response_content = str(expert.deployment_strategy("production"))
                method_used = "deployment_strategy"
            elif "monitor" in expert_query.text.lower():
                response_content = str(expert.get_monitoring_guide())
                method_used = "get_monitoring_guide"
            else:
                response_content = str(expert.get_design_principles())
                method_used = "get_design_principles"
        
        elif expert_query.domain == ExpertDomain.ADVANCED_SECURITY:
            if "firewall" in expert_query.text.lower():
                response_content = str(expert.firewall_design("enterprise"))
                method_used = "firewall_design"
            elif "sandbox" in expert_query.text.lower():
                response_content = str(expert.sandbox_selection("untrusted-code"))
                method_used = "sandbox_selection"
            elif "threat" in expert_query.text.lower():
                response_content = str(expert.threat_model_system("web-app"))
                method_used = "threat_model_system"
            elif "automation" in expert_query.text.lower():
                response_content = str(expert.security_automation_roadmap())
                method_used = "security_automation_roadmap"
            elif "zero trust" in expert_query.text.lower():
                response_content = str(expert.zero_trust_assessment())
                method_used = "zero_trust_assessment"
            elif "incident" in expert_query.text.lower():
                response_content = str(expert.incident_response_plan("data-breach"))
                method_used = "incident_response_plan"
            elif "compliance" in expert_query.text.lower():
                response_content = str(expert.compliance_checklist("GDPR"))
                method_used = "compliance_checklist"
            else:
                response_content = str(expert.firewall_design("default"))
                method_used = "firewall_design_default"
        
        return ExpertResponse(
            expert_domain=expert_query.domain,
            content=response_content,
            method_used=method_used,
            confidence=expert_query.confidence,
            citations=[f"Expert {expert_query.domain.value}"]
        )
    
    def process_query(self, query: str) -> List[ExpertResponse]:
        """Process query through router and get responses from appropriate experts."""
        expert_queries = self.router.route_query(query)
        responses = []
        
        for expert_query in expert_queries:
            response = self.query_expert(expert_query)
            responses.append(response)
        
        return responses
    
    @staticmethod
    def _extract_vuln_name(text: str) -> str:
        """Extract vulnerability name from query."""
        vulns = ["sql injection", "xss", "mitm", "ddos", "brute force"]
        text_lower = text.lower()
        for vuln in vulns:
            if vuln in text_lower:
                return vuln.title()
        return "SQL Injection"
    
    @staticmethod
    def _extract_attack_type(text: str) -> str:
        """Extract attack type from query."""
        attacks = ["web", "network", "application", "social"]
        text_lower = text.lower()
        for attack in attacks:
            if attack in text_lower:
                return attack.title()
        return "Web Attack"
    
    @staticmethod
    def _extract_algorithm(text: str) -> str:
        """Extract algorithm name from query."""
        algos = ["aes", "rsa", "ecc", "sha256", "bcrypt"]
        text_lower = text.lower()
        for algo in algos:
            if algo in text_lower:
                return algo.upper()
        return "AES-256"


class CoordinatorExpertBridge:
    """Bridge between WaseemBrainCoordinator and expert system."""
    
    def __init__(self):
        self.integrator = ExpertIntegrator()
    
    def process_through_experts(self, query: str) -> Dict[str, Any]:
        """
        Process query through expert system and return structured response.
        
        Returns:
            {
                "query": original query,
                "responses": [expert responses],
                "primary_expert": domain of primary expert,
                "confidence": overall confidence,
                "combined_response": merged response text
            }
        """
        responses = self.integrator.process_query(query)
        
        if not responses:
            return {
                "query": query,
                "responses": [],
                "primary_expert": None,
                "confidence": 0.0,
                "combined_response": "No expert could answer this query."
            }
        
        # Use highest confidence response as primary
        primary = max(responses, key=lambda r: r.confidence)
        
        # Combine all responses
        combined = self._combine_responses(responses)
        
        return {
            "query": query,
            "responses": responses,
            "primary_expert": primary.expert_domain.value,
            "confidence": primary.confidence,
            "combined_response": combined
        }
    
    @staticmethod
    def _combine_responses(responses: List[ExpertResponse]) -> str:
        """Combine multiple expert responses into single narrative."""
        if len(responses) == 1:
            return responses[0].content
        
        combined = []
        for i, resp in enumerate(responses, 1):
            combined.append(f"\n[Expert {i}: {resp.expert_domain.value}]")
            combined.append(f"Method: {resp.method_used}")
            combined.append(f"Response:\n{resp.content}\n")
        
        return "".join(combined)


if __name__ == "__main__":
    # Test the integration
    bridge = CoordinatorExpertBridge()
    
    test_queries = [
        "What is SQL injection and how to prevent it?",
        "Which encryption algorithm should I use for sensitive data?",
        "How do I optimize sorting large datasets?",
        "Design a scalable microservices architecture",
        "Implement zero trust security model"
    ]
    
    print("="*70)
    print("PHASE 4: COORDINATOR EXPERT INTEGRATION TEST")
    print("="*70)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = bridge.process_through_experts(query)
        print(f"Primary Expert: {result['primary_expert']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Response Preview: {result['combined_response'][:200]}...")
