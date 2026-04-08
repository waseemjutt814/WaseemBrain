"""Cryptography & Mathematical Algorithms Expert Module.

Provides comprehensive knowledge on encryption, cryptographic algorithms,
mathematical foundations, and secure communication protocols.
"""

from dataclasses import dataclass
from types import SimpleNamespace


@dataclass
class CryptographicAlgorithm:
    """Cryptographic algorithm specification."""
    name: str
    category: str  # Symmetric, Asymmetric, Hashing, Key Derivation
    key_size: str
    use_case: str
    security_strength: str
    pros: list[str]
    cons: list[str]


class CryptographyKnowledgeBase:
    """Comprehensive cryptography knowledge base."""
    
    SYMMETRIC_ALGORITHMS = [
        CryptographicAlgorithm(
            name="AES (Advanced Encryption Standard)",
            category="Symmetric",
            key_size="128, 192, 256 bits",
            use_case="Data at rest encryption, NIST approved",
            security_strength="NIST approved, no known practical attacks",
            pros=[
                "Very fast software implementation",
                "Efficient hardware implementation",
                "Widely supported",
                "NIST standard",
                "256-bit variant resistant to quantum attacks",
            ],
            cons=["Requires secure key management", "No built-in authentication"],
        ),
        CryptographicAlgorithm(
            name="ChaCha20",
            category="Symmetric",
            key_size="256 bits",
            use_case="Stream encryption, DTLS, TLS",
            security_strength="Not broken, modern design",
            pros=[
                "Faster on non-AES hardware",
                "No patent restrictions",
                "Simple and elegant design",
                "Good performance on mobile",
            ],
            cons=["Less tested than AES", "Smaller security margin"],
        ),
    ]
    
    ASYMMETRIC_ALGORITHMS = [
        CryptographicAlgorithm(
            name="RSA",
            category="Asymmetric",
            key_size="2048 bits minimum (4096 recommended)",
            use_case="Key exchange, digital signatures",
            security_strength="Secure if key size ≥ 2048 bits",
            pros=[
                "Well understood mathematically",
                "Widely implemented",
                "Good for digital signatures",
            ],
            cons=[
                "Slower than symmetric",
                "Key size growing due to attacks",
                "Vulnerable to quantum computers",
                "Padding required",
            ],
        ),
        CryptographicAlgorithm(
            name="Elliptic Curve Cryptography (ECC)",
            category="Asymmetric",
            key_size="256 bits equivalent to 3072-bit RSA",
            use_case="Modern key exchange, signatures, TLS",
            security_strength="256-bit ECC = 128-bit symmetric security",
            pros=[
                "Smaller key sizes",
                "Faster computation",
                "Better security per bit",
                "Modern standard",
            ],
            cons=[
                "More complex mathematics",
                "Implementation pitfalls",
                "Patent concerns (mostly resolved)",
            ],
        ),
    ]
    
    HASHING_ALGORITHMS = [
        CryptographicAlgorithm(
            name="SHA-256",
            category="Hashing",
            key_size="256-bit output",
            use_case="Data integrity, password hashing (with salt)",
            security_strength="Cryptographically secure, NIST approved",
            pros=[
                "Well analyzed",
                "No known attacks",
                "Fast",
                "NIST standard",
            ],
            cons=["Vulnerable to rainbow tables without salt"],
        ),
        CryptographicAlgorithm(
            name="SHA-3 (Keccak)",
            category="Hashing",
            key_size="256-bit output",
            use_case="Data integrity, future-proofing",
            security_strength="Different design from SHA-2, modern",
            pros=[
                "Different design from SHA-2",
                "Can squeeze arbitrary length output",
                "Future-proof choice",
            ],
            cons=["Less widely deployed than SHA-256"],
        ),
        CryptographicAlgorithm(
            name="bcrypt",
            category="Key Derivation",
            key_size="Variable",
            use_case="Password hashing",
            security_strength="Deliberately slow to resist brute force",
            pros=[
                "Slow (good for passwords)",
                "Salted by default",
                "Adjustable work factor",
                "Simple API",
            ],
            cons=["Slower than optimal for non-password use"],
        ),
    ]
    
    KEY_EXCHANGE_PROTOCOLS = [
        {
            "protocol": "ECDHE (Elliptic Curve Diffie-Hellman Ephemeral)",
            "category": "Key Exchange",
            "properties": {
                "forward_secrecy": True,
                "post_quantum_resistant": False,
                "performance": "Fast",
            },
            "use_in": "TLS 1.3, modern protocols",
            "recommendation": "Use with TLS 1.3",
        },
        {
            "protocol": "DH (Diffie-Hellman)",
            "category": "Key Exchange",
            "properties": {
                "forward_secrecy": False,
                "post_quantum_resistant": False,
                "performance": "Slower",
            },
            "use_in": "Legacy protocols",
            "recommendation": "Deprecated, use ECDHE",
        },
    ]
    
    AUTHENTICATION_METHODS = [
        {
            "method": "HMAC-SHA256",
            "purpose": "Message authentication codes",
            "properties": ["Fast", "Deterministic", "Requires shared key"],
            "use_case": "API authentication, integrity checking",
        },
        {
            "method": "Digital Signatures (RSA, ECDSA)",
            "purpose": "Non-repudiation and authentication",
            "properties": ["Public key verification", "Cannot deny later"],
            "use_case": "Document signing, certificate authority",
        },
        {
            "method": "Certificates (X.509)",
            "purpose": "Public key infrastructure",
            "properties": ["Trusted third party", "Chain of trust"],
            "use_case": "TLS/SSL, code signing",
        },
    ]
    
    MATHEMATICAL_FOUNDATIONS = [
        {
            "concept": "Prime Numbers",
            "importance": "Foundation of RSA",
            "algorithm": "Generate large cryptographic primes",
            "property": "Used to create one-way functions",
        },
        {
            "concept": "Elliptic Curves",
            "importance": "Foundation of ECC",
            "algorithm": "Points on curve y²=x³+ax+b (mod p)",
            "property": "Discrete log problem is hard",
        },
        {
            "concept": "Discrete Logarithm Problem",
            "importance": "Security of DH and ECC",
            "algorithm": "Given g, a, find n where a = g^n mod p",
            "property": "Computationally infeasible with large numbers",
        },
        {
            "concept": "Random Number Generation",
            "importance": "Critical for all cryptography",
            "algorithm": "Cryptographically secure RNG",
            "property": "Must be truly random, not pseudo-random",
        },
    ]
    
    SECURE_PROTOCOL_RECOMMENDATIONS = [
        {
            "protocol": "TLS 1.3",
            "recommendation": "MUST use for HTTPS",
            "configuration": {
                "cipher_suites": ["TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256"],
                "key_exchange": "ECDHE",
                "minimum_key_size": "256 bits",
            },
            "disabled": ["TLS 1.0", "TLS 1.1", "TLS 1.2 without AEAD"],
        },
        {
            "protocol": "SSH",
            "recommendation": "Use SSH-2 only",
            "configuration": {
                "key_exchange": "ECDH, Diffie-Hellman-Group16",
                "authentication": "ED25519 keys preferred",
                "encryption": "AES-256-GCM, ChaCha20",
            },
        },
    ]
    
    def get_algorithm_by_use_case(self, use_case: str) -> dict:
        """Get recommended algorithms for use case.
        
        Args:
            use_case: Type of encryption needed
            
        Returns:
            Recommended algorithms
        """
        recommendations = {
            "data_at_rest": {
                "algorithm": "AES-256-GCM",
                "key_derivation": "PBKDF2 or Argon2",
                "reason": "Fast, NIST approved, authenticated encryption",
            },
            "data_in_transit": {
                "algorithm": "TLS 1.3 with ECDHE-ECDSA",
                "cipher": "AES-256-GCM or ChaCha20-Poly1305",
                "reason": "Forward secrecy, authenticated, modern",
            },
            "password_storage": {
                "algorithm": "bcrypt or Argon2",
                "parameters": "Work factor ≥ 12",
                "reason": "Slow, salted, resistant to brute force",
            },
            "digital_signatures": {
                "algorithm": "ECDSA with SHA-256 or EdDSA",
                "key_size": "256 bits minimum",
                "reason": "Fast verification, good security",
            },
        }
        
        return recommendations.get(use_case.lower(), {
            "error": f"Unknown use case: {use_case}",
            "available": list(recommendations.keys()),
        })
    
    def get_quantum_resistant_options(self) -> dict:
        """Get post-quantum cryptography recommendations.
        
        Returns:
            Quantum-resistant algorithms and approaches
        """
        return {
            "current_status": "Quantum computers not yet practical for cryptanalysis",
            "recommendations": [
                "Use 256-bit symmetric keys (resistant to Grover's algorithm)",
                "Avoid RSA and ECC (vulnerable to Shor's algorithm)",
                "Research NIST PQC candidates: CRYSTALS-Kyber, CRYSTALS-Dilithium",
                "Plan migration timeline for post-quantum crypto",
            ],
            "timeline": "Expected standardization by 2024-2025",
        }


class CryptographyExpert:
    """Expert module for cryptography and mathematical algorithms."""

    def __init__(self):
        self.kb = CryptographyKnowledgeBase()
        self.knowledge_base = SimpleNamespace(
            symmetric_algorithms=list(self.kb.SYMMETRIC_ALGORITHMS),
            asymmetric_algorithms=list(self.kb.ASYMMETRIC_ALGORITHMS),
            hashing_algorithms=list(self.kb.HASHING_ALGORITHMS),
        )
        self.name = "Cryptography Expert"
        self.specialties = [
            "Encryption Algorithms",
            "Key Management",
            "Secure Protocols",
            "Digital Signatures",
            "Mathematical Foundations",
            "Post-Quantum Cryptography",
        ]

    def _normalize_algorithm_name(self, algorithm_name: str) -> str:
        normalized = algorithm_name.lower().replace('-', ' ').replace('(', ' ').replace(')', ' ')
        return ' '.join(normalized.split())

    def recommend_encryption_details(self, use_case: str) -> dict[str, object]:
        aliases = {
            'data': 'data_at_rest',
            'storage': 'data_at_rest',
            'rest': 'data_at_rest',
            'transit': 'data_in_transit',
            'network': 'data_in_transit',
            'password': 'password_storage',
            'signatures': 'digital_signatures',
        }
        normalized = aliases.get(use_case.lower(), use_case.lower())
        return self.kb.get_algorithm_by_use_case(normalized)

    def recommend_encryption(self, use_case: str, security_level: str | None = None) -> str:
        details = self.recommend_encryption_details(use_case)
        if 'error' in details:
            return f"Unknown encryption use case: {use_case}."
        level_text = f" for {security_level} security" if security_level else ''
        algorithm = details.get('algorithm', 'a modern authenticated cipher suite')
        reason = details.get('reason', 'it is a strong modern choice')
        return f"Recommended encryption{level_text}: {algorithm}. Reason: {reason}."

    def analyze_algorithm_details(self, algorithm_name: str) -> dict[str, object]:
        normalized = self._normalize_algorithm_name(algorithm_name)
        all_algorithms = self.kb.SYMMETRIC_ALGORITHMS + self.kb.ASYMMETRIC_ALGORITHMS + self.kb.HASHING_ALGORITHMS
        for algo in all_algorithms:
            candidate = self._normalize_algorithm_name(algo.name)
            if normalized == candidate or normalized in candidate or candidate in normalized:
                return {
                    'name': algo.name,
                    'category': algo.category,
                    'key_size': algo.key_size,
                    'use_case': algo.use_case,
                    'security_strength': algo.security_strength,
                    'advantages': algo.pros,
                    'disadvantages': algo.cons,
                }
        return {
            'error': f"Algorithm not found: {algorithm_name}",
            'available_symmetric': [a.name for a in self.kb.SYMMETRIC_ALGORITHMS],
            'available_asymmetric': [a.name for a in self.kb.ASYMMETRIC_ALGORITHMS],
        }

    def analyze_algorithm(self, algorithm_name: str) -> str:
        details = self.analyze_algorithm_details(algorithm_name)
        if 'error' in details:
            examples = ', '.join(details['available_symmetric'][:2])
            return f"Algorithm not found: {algorithm_name}. Available symmetric options include {examples}."
        return (
            f"{details['name']} is a {details['category']} algorithm with {details['key_size']} keys/output. "
            f"Typical use: {details['use_case']}. Security posture: {details['security_strength']}."
        )

    def get_quantum_readiness_details(self) -> dict[str, object]:
        return self.kb.get_quantum_resistant_options()

    def get_quantum_readiness(self) -> str:
        details = self.get_quantum_readiness_details()
        recommendations = '; '.join(details['recommendations'][:3])
        return f"Quantum readiness status: {details['current_status']}. Post-quantum guidance: {recommendations}."

    def get_summary(self) -> str:
        return (
            f"Cryptography Expert covering {len(self.knowledge_base.symmetric_algorithms)} symmetric, "
            f"{len(self.knowledge_base.asymmetric_algorithms)} asymmetric, and "
            f"{len(self.knowledge_base.hashing_algorithms)} hashing algorithms."
        )

    def answer_query(self, query: str) -> str:
        lowered = query.lower()
        if 'quantum' in lowered or 'post-quantum' in lowered:
            return self.get_quantum_readiness()
        if 'tls' in lowered or 'ssh' in lowered:
            return self.recommend_encryption('data_in_transit')
        if 'password' in lowered:
            return self.recommend_encryption('password_storage')
        for algo in self.kb.SYMMETRIC_ALGORITHMS + self.kb.ASYMMETRIC_ALGORITHMS + self.kb.HASHING_ALGORITHMS:
            if algo.name.lower().split()[0] in lowered:
                return self.analyze_algorithm(algo.name)
        return self.get_summary()
