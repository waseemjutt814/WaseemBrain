from __future__ import annotations

import re

# High-frequency Roman Urdu/Hindi stop words and verbs
_URDU_KEYWORDS = {
    "hai", "hain", "ho", "tha", "thi", "thay", "hoon",
    "kya", "kiya", "kyu", "kyun", "kaise", "kese", "kab", "kahan", "kab", "konsa",
    "main", "mera", "meri", "mere", "mujhe", "hum", "hamara", "hamari", "humein",
    "tum", "tumhara", "tumhari", "tumhare", "aap", "aapka", "aapki", "aapke",
    "karo", "karein", "karain", "kar", "diya", "dena", "do", "karna", "kardo",
    "bhai", "yar", "yaara", "yaaro", "dost", "sir", "janab",
    "batao", "suno", "dekho", "samjhao", "likho", "dekhao", "dikhao",
    "bohat", "bhut", "zyada", "ziyada", "kam", "thora",
    "nahi", "koi", "kuch", "sab", "sirf", "bhi", "tou", "to",
    "aur", "ya", "magar", "lekin", "par",
    "jese", "jaise", "wese", "waise",
    "bat", "baat", "awaz", "jawab", "sawal",
}

_TEMPLATES = {
    "en": {
        "grounded_answer_lead": "Based on the workspace and memory, here is the verified insight:",
        "grounded_plan_lead": "Proposed plan based on your request:",
        "clarification_prompt": "I need one detail to focus: which file, function, or error should I look at for '{query}'?",
        "code_expert_lead": "I found these matching blocks in your code:",
        "code_expert_next_step": "Recommended next check:",
        "no_evidence": "No matching evidence found in memory or workspace.",
        "no_workspace_matches": "No relevant code found for this query.",
        "query_focus": "Context:",
        "matched_symbols": "Symbols:",
        "offline_capital": "{country}'s capital is {capital} ({region}).",
        "offline_dataset_error": "Data not found offline.",
    },
    "ur": {
        "grounded_answer_lead": "Workspace aur memory se ye verified info mili he:",
        "grounded_plan_lead": "Aap ki request ke mutabiq mera implementation plan:",
        "clarification_prompt": "Mujhe thora aur context chahiye: '{query}' ke liye kis file ya function par focus karun?",
        "code_expert_lead": "Code base me ye matches mile hain:",
        "code_expert_next_step": "Is ke baad yahan check karein:",
        "no_evidence": "Is bare me koi verified data nahi mila.",
        "no_workspace_matches": "Workspace me koi relevant code nahi mila.",
        "query_focus": "Sawal:",
        "matched_symbols": "Funs/Classes:",
        "offline_capital": "{country} ka capital {capital} he ({region}).",
        "offline_dataset_error": "Ye data offline mojood nahi he.",
    }
}

class LocaleEngine:
    @staticmethod
    def detect_locale(query: str) -> str:
        """
        Detects if the query contains a high threshold of Roman Urdu/Hindi words.
        Returns 'ur' if it does, else 'en'.
        """
        words = re.findall(r"[a-zA-Z]{2,}", query.lower())
        if not words:
            return "en"
        
        urdu_word_count = sum(1 for word in words if word in _URDU_KEYWORDS)
        
        # If at least 2 Roman Urdu words are identified, or it makes up 20% of the small sentence length
        if urdu_word_count >= 2 or (urdu_word_count >= 1 and len(words) <= 4):
            return "ur"
            
        return "en"
    
    @staticmethod
    def t(locale: str, key: str, **kwargs: str) -> str:
        """
        Translates a given key based on the locale. Falls back to English.
        """
        # Default to English if locale is missing
        lang_dict = _TEMPLATES.get(locale, _TEMPLATES["en"])
        template = lang_dict.get(key, _TEMPLATES["en"].get(key, ""))
        
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError:
                return template
        return template
