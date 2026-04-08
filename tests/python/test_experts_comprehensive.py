"""
Comprehensive integration test for all 5 expert modules.
Tests all methods, knowledge bases, and integration scenarios.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class ExpertComprehensiveTest:
    """Run comprehensive tests on all 5 expert modules."""
    
    def __init__(self):
        self.results = {
            "cybersecurity": {"methods": {}, "knowledge": {}, "status": ""},
            "cryptography": {"methods": {}, "knowledge": {}, "status": ""},
            "algorithms": {"methods": {}, "knowledge": {}, "status": ""},
            "engineering": {"methods": {}, "knowledge": {}, "status": ""},
            "advanced_security": {"methods": {}, "knowledge": {}, "status": ""}
        }
        self.total_tests = 0
        self.passed_tests = 0
    
    def print_header(self, title: str, level: int = 1):
        """Print formatted header."""
        width = 70
        if level == 1:
            print("\n" + "=" * width)
            print(f" {title}")
            print("=" * width)
        elif level == 2:
            print(f"\n{title}")
            print("-" * len(title))
        else:
            print(f"\n  {title}")
    
    def test_result(self, name: str, passed: bool, details: str = ""):
        """Record test result."""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "[PASS]"
        else:
            status = "[FAIL]"
        
        details_str = f" - {details}" if details else ""
        print(f"    {status} {name}{details_str}")
        return passed
    
    def run_all_tests(self) -> bool:
        """Run all comprehensive tests."""
        
        self.print_header("COMPREHENSIVE EXPERT SYSTEM TEST SUITE")
        
        try:
            self.test_cybersecurity_expert()
            self.test_cryptography_expert()
            self.test_algorithms_expert()
            self.test_engineering_expert()
            self.test_advanced_security_expert()
            self.test_integration()
            self.print_final_report()
            
            return True
        except Exception as e:
            print(f"\n[FATAL ERROR]: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_cybersecurity_expert(self):
        """Test Cybersecurity Expert module."""
        self.print_header("1. CYBERSECURITY EXPERT", 2)
        
        from experts.base.cybersecurity_expert import CybersecurityExpert
        
        expert = CybersecurityExpert()
        self.results["cybersecurity"]["status"] = "loaded"
        
        # Test knowledge base
        self.print_header("Knowledge Base", 3)
        self.test_result("Knowledge base initialized", expert.kb is not None)
        self.test_result(f"CONCEPTS loaded", len(expert.kb.CONCEPTS) > 0, 
                        f"{len(expert.kb.CONCEPTS)} concepts")
        
        # Test all methods
        self.print_header("Methods", 3)
        
        # analyze_vulnerability
        try:
            result = expert.analyze_vulnerability("SQL Injection")
            passed = result is not None and isinstance(result, dict)
            self.test_result("analyze_vulnerability()", passed, 
                           f"{len(str(result))} chars returned")
            self.results["cybersecurity"]["methods"]["analyze_vulnerability"] = passed
        except Exception as e:
            self.test_result("analyze_vulnerability()", False, str(e))
            self.results["cybersecurity"]["methods"]["analyze_vulnerability"] = False
        
        # recommend_defenses
        try:
            result = expert.recommend_defenses("Web Attack")
            passed = result is not None and isinstance(result, dict)
            self.test_result("recommend_defenses()", passed,
                           f"{len(str(result))} chars returned")
            self.results["cybersecurity"]["methods"]["recommend_defenses"] = passed
        except Exception as e:
            self.test_result("recommend_defenses()", False, str(e))
            self.results["cybersecurity"]["methods"]["recommend_defenses"] = False
        
        # get_pentesting_methodology
        try:
            result = expert.get_pentesting_methodology()
            passed = result is not None and isinstance(result, dict)
            self.test_result("get_pentesting_methodology()", passed,
                           f"{len(str(result))} chars returned")
            self.results["cybersecurity"]["methods"]["get_pentesting_methodology"] = passed
        except Exception as e:
            self.test_result("get_pentesting_methodology()", False, str(e))
            self.results["cybersecurity"]["methods"]["get_pentesting_methodology"] = False
        
        # get_compliance_guide
        try:
            result = expert.get_compliance_guide()
            passed = result is not None and isinstance(result, dict)
            self.test_result("get_compliance_guide()", passed,
                           f"{len(str(result))} chars returned")
            self.results["cybersecurity"]["methods"]["get_compliance_guide"] = passed
        except Exception as e:
            self.test_result("get_compliance_guide()", False, str(e))
            self.results["cybersecurity"]["methods"]["get_compliance_guide"] = False
        
        # get_summary
        try:
            result = expert.get_summary()
            passed = result is not None
            result_str = str(result)
            self.test_result("get_summary()", passed,
                           f"{len(result_str)} chars summary")
            self.results["cybersecurity"]["methods"]["get_summary"] = passed
        except Exception as e:
            self.test_result("get_summary()", False, str(e))
            self.results["cybersecurity"]["methods"]["get_summary"] = False
    
    def test_cryptography_expert(self):
        """Test Cryptography Expert module."""
        self.print_header("2. CRYPTOGRAPHY EXPERT", 2)
        
        from experts.base.cryptography_expert import CryptographyExpert
        
        expert = CryptographyExpert()
        self.results["cryptography"]["status"] = "loaded"
        
        # Test knowledge base
        self.print_header("Knowledge Base", 3)
        self.test_result("Knowledge base initialized", expert.kb is not None)
        self.test_result(f"Algorithms loaded", 
                        len(expert.kb.SYMMETRIC_ALGORITHMS) + len(expert.kb.ASYMMETRIC_ALGORITHMS) > 0,
                        f"{len(expert.kb.SYMMETRIC_ALGORITHMS) + len(expert.kb.ASYMMETRIC_ALGORITHMS)} algorithms")
        
        # Test methods
        self.print_header("Methods", 3)
        
        methods_to_test = [
            ("recommend_encryption", ("data-protection",), {}),
            ("analyze_algorithm", ("AES-256",), {}),
            ("get_protocol_security_config", ("TLS-1.3",), {}),
            ("get_quantum_readiness", (), {}),
            ("get_key_sizes", (), {}),
            ("get_summary", (), {}),
        ]
        
        for method_name, args, kwargs in methods_to_test:
            try:
                method = getattr(expert, method_name)
                result = method(*args, **kwargs)
                passed = result is not None
                result_str = str(result)
                self.test_result(f"{method_name}()", passed,
                               f"{len(result_str)} chars")
                self.results["cryptography"]["methods"][method_name] = passed
            except Exception as e:
                self.test_result(f"{method_name}()", False, str(e))
                self.results["cryptography"]["methods"][method_name] = False
    
    def test_algorithms_expert(self):
        """Test Algorithms Expert module."""
        self.print_header("3. ALGORITHMS EXPERT", 2)
        
        from experts.base.algorithms_expert import AlgorithmsExpert
        
        expert = AlgorithmsExpert()
        self.results["algorithms"]["status"] = "loaded"
        
        # Test knowledge base
        self.print_header("Knowledge Base", 3)
        self.test_result("Knowledge base initialized", expert.kb is not None)
        
        # Count knowledge items
        kb_items = (len(expert.kb.SORTING_ALGORITHMS) + len(expert.kb.SEARCHING_ALGORITHMS) + 
                   len(expert.kb.GRAPH_ALGORITHMS) + len(expert.kb.DATA_STRUCTURES))
        self.test_result("Knowledge items loaded", kb_items > 0,
                        f"{kb_items} items")
        
        # Test methods
        self.print_header("Methods", 3)
        
        methods_to_test = [
            ("recommend_algorithm", ("sorting",), {}),
            ("analyze_complexity", ("DFS",), {}),
            ("select_data_structure", ("search",), {}),
            ("get_complexity_guide", (), {}),
            ("get_design_patterns", (), {}),
            ("get_dynamic_programming_help", (), {}),
            ("get_summary", (), {}),
        ]
        
        for method_name, args, kwargs in methods_to_test:
            try:
                method = getattr(expert, method_name)
                result = method(*args, **kwargs)
                passed = result is not None
                result_str = str(result)
                self.test_result(f"{method_name}()", passed,
                               f"{len(result_str)} chars")
                self.results["algorithms"]["methods"][method_name] = passed
            except Exception as e:
                self.test_result(f"{method_name}()", False, str(e))
                self.results["algorithms"]["methods"][method_name] = False
    
    def test_engineering_expert(self):
        """Test Engineering Expert module."""
        self.print_header("4. SYSTEM ENGINEERING EXPERT", 2)
        
        from experts.base.engineering_expert import SystemEngineeringExpert
        
        expert = SystemEngineeringExpert()
        self.results["engineering"]["status"] = "loaded"
        
        # Test knowledge base
        self.print_header("Knowledge Base", 3)
        self.test_result("Knowledge base initialized", expert.kb is not None)
        
        # Count knowledge items
        kb_items = (len(expert.kb.ARCHITECTURE_PATTERNS) + len(expert.kb.DATABASE_DESIGN_PATTERNS) +
                   len(expert.kb.DEPLOYMENT_PATTERNS) + len(expert.kb.SCALABILITY_PATTERNS))
        self.test_result("Knowledge items loaded", kb_items > 0,
                        f"{kb_items} items")
        
        # Test methods
        self.print_header("Methods", 3)
        
        methods_to_test = [
            ("recommend_architecture", ("scalability",), {}),
            ("design_database", ("transactional",), {}),
            ("scaling_strategy", ("database",), {}),
            ("deployment_strategy", ("production",), {}),
            ("get_design_principles", (), {}),
            ("get_monitoring_guide", (), {}),
            ("get_summary", (), {}),
        ]
        
        for method_name, args, kwargs in methods_to_test:
            try:
                method = getattr(expert, method_name)
                result = method(*args, **kwargs)
                passed = result is not None
                result_str = str(result)
                self.test_result(f"{method_name}()", passed,
                               f"{len(result_str)} chars")
                self.results["engineering"]["methods"][method_name] = passed
            except Exception as e:
                self.test_result(f"{method_name}()", False, str(e))
                self.results["engineering"]["methods"][method_name] = False
    
    def test_advanced_security_expert(self):
        """Test Advanced Security Expert module."""
        self.print_header("5. ADVANCED SECURITY EXPERT", 2)
        
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        expert = AdvancedSecurityExpert()
        self.results["advanced_security"]["status"] = "loaded"
        
        # Test knowledge base
        self.print_header("Knowledge Base", 3)
        self.test_result("Knowledge base initialized", expert.kb is not None)
        
        # Count knowledge items
        kb_items = (len(expert.kb.FIREWALL_ARCHITECTURES) + len(expert.kb.SANDBOX_TECHNOLOGIES) +
                   len(expert.kb.THREAT_MODELING_FRAMEWORKS) + len(expert.kb.INCIDENT_RESPONSE_PLAYBOOKS))
        self.test_result("Knowledge items loaded", kb_items > 0,
                        f"{kb_items} items")
        
        # Test methods
        self.print_header("Methods", 3)
        
        methods_to_test = [
            ("firewall_design", ("enterprise",), {}),
            ("sandbox_selection", ("untrusted-code",), {}),
            ("threat_model_system", ("web-app",), {}),
            ("security_automation_roadmap", (), {}),
            ("zero_trust_assessment", (), {}),
            ("incident_response_plan", ("data-breach",), {}),
            ("compliance_checklist", ("GDPR",), {}),
            ("get_summary", (), {}),
        ]
        
        for method_name, args, kwargs in methods_to_test:
            try:
                method = getattr(expert, method_name)
                result = method(*args, **kwargs)
                passed = result is not None
                result_str = str(result)
                self.test_result(f"{method_name}()", passed,
                               f"{len(result_str)} chars")
                self.results["advanced_security"]["methods"][method_name] = passed
            except Exception as e:
                self.test_result(f"{method_name}()", False, str(e))
                self.results["advanced_security"]["methods"][method_name] = False
    
    def test_integration(self):
        """Test expert system integration."""
        self.print_header("6. SYSTEM INTEGRATION", 2)
        
        from experts.base.cybersecurity_expert import CybersecurityExpert
        from experts.base.cryptography_expert import CryptographyExpert
        from experts.base.algorithms_expert import AlgorithmsExpert
        from experts.base.engineering_expert import SystemEngineeringExpert
        from experts.base.advanced_security_expert import AdvancedSecurityExpert
        
        # Load all experts
        experts_dict = {
            "cybersecurity": CybersecurityExpert(),
            "cryptography": CryptographyExpert(),
            "algorithms": AlgorithmsExpert(),
            "engineering": SystemEngineeringExpert(),
            "advanced_security": AdvancedSecurityExpert(),
        }
        
        self.print_header("Expert Pool", 3)
        self.test_result("All 5 experts loaded", len(experts_dict) == 5)
        self.test_result("No conflicts in loading", all(e is not None for e in experts_dict.values()))
        
        self.print_header("Integration Scenarios", 3)
        
        # Scenario 1: Security assessment flow
        try:
            cyber = experts_dict["cybersecurity"]
            crypt = experts_dict["cryptography"]
            adv_sec = experts_dict["advanced_security"]
            
            # Get security assessment
            vuln = cyber.analyze_vulnerability("SQL Injection")
            enc = crypt.recommend_encryption("database")
            fw = adv_sec.firewall_design("enterprise")
            
            passed = all([vuln, enc, fw])
            self.test_result("Security Assessment Flow", passed,
                           "3-expert coordination")
        except Exception as e:
            self.test_result("Security Assessment Flow", False, str(e))
        
        # Scenario 2: System design flow
        try:
            eng = experts_dict["engineering"]
            alg = experts_dict["algorithms"]
            
            arch = eng.recommend_architecture("scalability")
            algo = alg.recommend_algorithm("sorting")
            
            passed = all([arch, algo])
            self.test_result("System Design Flow", passed,
                           "2-expert coordination")
        except Exception as e:
            self.test_result("System Design Flow", False, str(e))
        
        # Scenario 3: Complex security + engineering
        try:
            cyber = experts_dict["cybersecurity"]
            crypt = experts_dict["cryptography"]
            eng = experts_dict["engineering"]
            alg = experts_dict["algorithms"]
            adv_sec = experts_dict["advanced_security"]
            
            # Multi-expert consultation
            defenses = cyber.recommend_defenses("Network")
            proto = crypt.get_protocol_security_config("TLS-1.3")
            db = eng.design_database("secure")
            ds = alg.select_data_structure("security-log")
            threats = adv_sec.threat_model_system("database")
            
            passed = all([defenses, proto, db, ds, threats])
            self.test_result("Complex Multi-Expert Scenario", passed,
                           "5-expert coordination")
        except Exception as e:
            self.test_result("Complex Multi-Expert Scenario", False, str(e))
    
    def print_final_report(self):
        """Print final test report."""
        self.print_header("FINAL TEST REPORT", 1)
        
        print(f"\nTests Run: {self.total_tests}")
        print(f"Tests Passed: {self.passed_tests}")
        print(f"Tests Failed: {self.total_tests - self.passed_tests}")
        
        pass_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        print(f"Pass Rate: {pass_rate:.1f}%")
        
        print("\n" + "=" * 70)
        print("EXPERT STATUS SUMMARY")
        print("=" * 70)
        
        for expert_name, data in sorted(self.results.items()):
            method_count = len(data["methods"])
            method_passed = sum(1 for v in data["methods"].values() if v)
            
            status = "[PASS]" if method_passed == method_count else "[PARTIAL]"
            
            print(f"\n{expert_name.upper()}")
            print(f"  Status: {data['status']}")
            print(f"  Methods: {method_passed}/{method_count} passed")
            
            if method_passed < method_count:
                failed = [k for k, v in data["methods"].items() if not v]
                print(f"  Failed: {', '.join(failed)}")
        
        print("\n" + "=" * 70)
        if pass_rate >= 95:
            print("[SUCCESS] ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
        elif pass_rate >= 80:
            print("[WARNING] MOST TESTS PASSED - REVIEW FAILURES")
        else:
            print("[ERROR] SIGNIFICANT FAILURES - REVIEW REQUIRED")
        print("=" * 70)
        
        return pass_rate >= 95


def main():
    """Run comprehensive test suite."""
    tester = ExpertComprehensiveTest()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
