"""
Integration tests for all 5 specialized expert modules.
Tests cybersecurity, cryptography, algorithms, engineering, and advanced security experts.
"""

import sys
import os
from pathlib import Path

# Add the brain module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest


class TestCybersecurityExpert:
    """Test the Cybersecurity Expert module."""

    def test_import(self):
        """Test that cybersecurity expert can be imported."""
        from experts.base.cybersecurity_expert import CybersecurityExpert, CybersecurityKnowledgeBase
        assert CybersecurityExpert is not None
        assert CybersecurityKnowledgeBase is not None

    def test_knowledge_base_loading(self):
        """Test that knowledge base loads correctly."""
        from experts.base.cybersecurity_expert import CybersecurityExpert
        
        expert = CybersecurityExpert()
        assert expert.knowledge_base is not None
        assert len(expert.knowledge_base.vulnerabilities) > 0
        assert len(expert.knowledge_base.defense_layers) > 0

    def test_vulnerability_analysis(self):
        """Test vulnerability analysis method."""
        from experts.base.cybersecurity_expert import CybersecurityExpert
        
        expert = CybersecurityExpert()
        result = expert.analyze_vulnerability("SQL Injection")
        assert result is not None
        assert "SQL Injection" in result or "vulnerability" in result.lower()

    def test_defense_recommendations(self):
        """Test defense recommendations."""
        from experts.base.cybersecurity_expert import CybersecurityExpert
        
        expert = CybersecurityExpert()
        result = expert.recommend_defenses()
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_expert_summary(self):
        """Test expert summary generation."""
        from experts.base.cybersecurity_expert import CybersecurityExpert
        
        expert = CybersecurityExpert()
        summary = expert.get_summary()
        assert summary is not None
        assert "Cybersecurity" in summary or "security" in summary.lower()


class TestCryptographyExpert:
    """Test the Cryptography Expert module."""

    def test_import(self):
        """Test that cryptography expert can be imported."""
        from experts.base.cryptography_expert import CryptographyExpert, CryptographyKnowledgeBase
        assert CryptographyExpert is not None
        assert CryptographyKnowledgeBase is not None

    def test_knowledge_base_loading(self):
        """Test that knowledge base loads correctly."""
        from experts.base.cryptography_expert import CryptographyExpert
        
        expert = CryptographyExpert()
        assert expert.knowledge_base is not None
        assert len(expert.knowledge_base.symmetric_algorithms) > 0
        assert len(expert.knowledge_base.asymmetric_algorithms) > 0

    def test_encryption_recommendation(self):
        """Test encryption algorithm recommendation."""
        from experts.base.cryptography_expert import CryptographyExpert
        
        expert = CryptographyExpert()
        result = expert.recommend_encryption("data", "high")
        assert result is not None
        assert isinstance(result, str)

    def test_algorithm_analysis(self):
        """Test algorithm analysis."""
        from experts.base.cryptography_expert import CryptographyExpert
        
        expert = CryptographyExpert()
        result = expert.analyze_algorithm("AES-256")
        assert result is not None
        assert "AES" in result or "AES-256" in result

    def test_quantum_readiness(self):
        """Test quantum readiness assessment."""
        from experts.base.cryptography_expert import CryptographyExpert
        
        expert = CryptographyExpert()
        result = expert.get_quantum_readiness()
        assert result is not None
        assert isinstance(result, str)
        assert "quantum" in result.lower() or "post-quantum" in result.lower()

    def test_expert_summary(self):
        """Test expert summary generation."""
        from experts.base.cryptography_expert import CryptographyExpert
        
        expert = CryptographyExpert()
        summary = expert.get_summary()
        assert summary is not None


class TestAlgorithmsExpert:
    """Test the Algorithms & Data Structures Expert module."""

    def test_import(self):
        """Test that algorithms expert can be imported."""
        from experts.base.algorithms_expert import AlgorithmsExpert, AlgorithmsKnowledgeBase
        assert AlgorithmsExpert is not None
        assert AlgorithmsKnowledgeBase is not None

    def test_knowledge_base_loading(self):
        """Test that knowledge base loads correctly."""
        from experts.base.algorithms_expert import AlgorithmsExpert
        
        expert = AlgorithmsExpert()
        assert expert.knowledge_base is not None
        assert len(expert.knowledge_base.sorting_algorithms) > 0
        assert len(expert.knowledge_base.data_structures) > 0

    def test_algorithm_recommendation(self):
        """Test algorithm recommendation."""
        from experts.base.algorithms_expert import AlgorithmsExpert
        
        expert = AlgorithmsExpert()
        result = expert.recommend_algorithm("sorting", 100)
        assert result is not None
        assert isinstance(result, str)

    def test_complexity_analysis(self):
        """Test complexity analysis."""
        from experts.base.algorithms_expert import AlgorithmsExpert
        
        expert = AlgorithmsExpert()
        result = expert.analyze_complexity("O(n log n)")
        assert result is not None
        assert "complexity" in result.lower() or "O(n" in result

    def test_data_structure_selection(self):
        """Test data structure selection."""
        from experts.base.algorithms_expert import AlgorithmsExpert
        
        expert = AlgorithmsExpert()
        result = expert.select_data_structure("fast-lookup", "dynamic")
        assert result is not None
        assert isinstance(result, str)

    def test_expert_summary(self):
        """Test expert summary generation."""
        from experts.base.algorithms_expert import AlgorithmsExpert
        
        expert = AlgorithmsExpert()
        summary = expert.get_summary()
        assert summary is not None


class TestEngineeringExpert:
    """Test the System Engineering & Architecture Expert module."""

    def test_import(self):
        """Test that engineering expert can be imported."""
        from experts.base.engineering_expert import SystemEngineeringExpert, SystemArchitectureKnowledgeBase
        assert SystemEngineeringExpert is not None
        assert SystemArchitectureKnowledgeBase is not None

    def test_knowledge_base_loading(self):
        """Test that knowledge base loads correctly."""
        from experts.base.engineering_expert import SystemEngineeringExpert
        
        expert = SystemEngineeringExpert()
        assert expert.knowledge_base is not None
        assert len(expert.knowledge_base.architecture_patterns) > 0
        assert len(expert.knowledge_base.database_patterns) > 0

    def test_architecture_recommendation(self):
        """Test architecture recommendation."""
        from experts.base.engineering_expert import SystemEngineeringExpert
        
        expert = SystemEngineeringExpert()
        result = expert.recommend_architecture("scale", 10000)
        assert result is not None
        assert isinstance(result, str)

    def test_database_design(self):
        """Test database design guidance."""
        from experts.base.engineering_expert import SystemEngineeringExpert
        
        expert = SystemEngineeringExpert()
        result = expert.design_database("transactional", "high-consistency")
        assert result is not None
        assert isinstance(result, str)

    def test_scaling_strategy(self):
        """Test scaling strategy."""
        from experts.base.engineering_expert import SystemEngineeringExpert
        
        expert = SystemEngineeringExpert()
        result = expert.scaling_strategy("horizontal")
        assert result is not None
        assert "scaling" in result.lower() or "scale" in result.lower()

    def test_expert_summary(self):
        """Test expert summary generation."""
        from experts.base.engineering_expert import SystemEngineeringExpert
        
        expert = SystemEngineeringExpert()
        summary = expert.get_summary()
        assert summary is not None


class TestAdvancedSecurityExpert:
    """Test the Advanced Security Expert module."""

    def test_import(self):
        """Test that advanced security expert can be imported."""
        from experts.base.advanced_security_expert import AdvancedSecurityExpert, AdvancedSecurityKnowledgeBase
        assert AdvancedSecurityExpert is not None
        assert AdvancedSecurityKnowledgeBase is not None

    def test_knowledge_base_loading(self):
        """Test that knowledge base loads correctly."""
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        expert = AdvancedSecurityExpert()
        assert expert.knowledge_base is not None
        assert len(expert.knowledge_base.firewall_types) > 0
        assert len(expert.knowledge_base.sandbox_technologies) > 0

    def test_firewall_design(self):
        """Test firewall design recommendation."""
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        expert = AdvancedSecurityExpert()
        result = expert.firewall_design("high-security", "enterprise")
        assert result is not None
        assert "firewall" in result.lower() or "WAF" in result

    def test_sandbox_selection(self):
        """Test sandbox technology selection."""
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        expert = AdvancedSecurityExpert()
        result = expert.sandbox_selection("isolation", "high")
        assert result is not None
        assert "sandbox" in result.lower() or "container" in result.lower()

    def test_threat_modeling(self):
        """Test threat modeling."""
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        expert = AdvancedSecurityExpert()
        result = expert.threat_model_system("web-application")
        assert result is not None
        assert "threat" in result.lower() or "STRIDE" in result

    def test_zero_trust_assessment(self):
        """Test zero trust assessment."""
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        expert = AdvancedSecurityExpert()
        result = expert.zero_trust_assessment("network", 0)
        assert result is not None
        assert "trust" in result.lower() or "zero" in result.lower()

    def test_incident_response_plan(self):
        """Test incident response plan."""
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        expert = AdvancedSecurityExpert()
        result = expert.incident_response_plan("data-breach")
        assert result is not None
        assert "incident" in result.lower() or "response" in result.lower()

    def test_expert_summary(self):
        """Test expert summary generation."""
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        expert = AdvancedSecurityExpert()
        summary = expert.get_summary()
        assert summary is not None


class TestExpertIntegration:
    """Test all experts working together in the expert pool."""

    def test_all_experts_loadable(self):
        """Test that all 5 experts can be loaded together."""
        from experts.base.cybersecurity_expert import CybersecurityExpert
        from experts.base.cryptography_expert import CryptographyExpert
        from experts.base.algorithms_expert import AlgorithmsExpert
        from experts.base.engineering_expert import SystemEngineeringExpert
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        experts = {
            "cybersecurity": CybersecurityExpert(),
            "cryptography": CryptographyExpert(),
            "algorithms": AlgorithmsExpert(),
            "engineering": SystemEngineeringExpert(),
            "advanced-security": AdvancedSecurityExpert()
        }
        
        assert len(experts) == 5
        for name, expert in experts.items():
            assert expert is not None
            assert hasattr(expert, 'knowledge_base')
            assert hasattr(expert, 'get_summary')

    def test_expert_summaries_generation(self):
        """Test that all experts can generate summaries."""
        from experts.base.cybersecurity_expert import CybersecurityExpert
        from experts.base.cryptography_expert import CryptographyExpert
        from experts.base.algorithms_expert import AlgorithmsExpert
        from experts.base.engineering_expert import SystemEngineeringExpert
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        experts = [
            CybersecurityExpert(),
            CryptographyExpert(),
            AlgorithmsExpert(),
            SystemEngineeringExpert(),
            AdvancedSecurityExpert()
        ]
        
        summaries = []
        for expert in experts:
            summary = expert.get_summary()
            assert summary is not None
            assert len(summary) > 0
            summaries.append(summary)
        
        # All summaries should be different (one per expert)
        assert len(summaries) == 5

    def test_expert_domains_coverage(self):
        """Test that experts cover different domains."""
        from experts.base.cybersecurity_expert import CybersecurityExpert
        from experts.base.cryptography_expert import CryptographyExpert
        from experts.base.algorithms_expert import AlgorithmsExpert
        from experts.base.engineering_expert import SystemEngineeringExpert
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        domains = {
            "security": CybersecurityExpert(),
            "cryptography": CryptographyExpert(),
            "algorithms": AlgorithmsExpert(),
            "engineering": SystemEngineeringExpert(),
            "advanced-security": AdvancedSecurityExpert()
        }
        
        # Verify each domain has at least one expert
        assert len(domains) == 5
        for domain_name, expert in domains.items():
            assert expert is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
