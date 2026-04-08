"""Simple integration test for all 5 expert modules."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_experts() -> None:
    from experts.base.cybersecurity_expert import CybersecurityExpert
    from experts.base.cryptography_expert import CryptographyExpert
    from experts.base.algorithms_expert import AlgorithmsExpert
    from experts.base.engineering_expert import SystemEngineeringExpert
    from experts.base.advanced_security_expert import AdvancedSecurityExpert

    cs_expert = CybersecurityExpert()
    cr_expert = CryptographyExpert()
    al_expert = AlgorithmsExpert()
    eng_expert = SystemEngineeringExpert()
    adv_expert = AdvancedSecurityExpert()

    experts = [cs_expert, cr_expert, al_expert, eng_expert, adv_expert]
    assert len(experts) == 5
    assert all(expert.specialties for expert in experts)
    assert "SQL Injection" in cs_expert.analyze_vulnerability("SQL Injection")
    assert "Recommended encryption" in cr_expert.recommend_encryption("data")
    assert "Recommended algorithm" in al_expert.recommend_algorithm("sorting")
    assert "Recommended architecture" in eng_expert.recommend_architecture("scale")
    assert "firewall" in adv_expert.firewall_design("enterprise").lower()
