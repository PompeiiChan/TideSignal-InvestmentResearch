"""Response assembly helpers: profile, prompts, citation patch, templates."""

from .citation_fix import build_citation_patch_prompt, patch_missing_citations
from .profile import PROFILE_MAX_TOKENS, AssemblyProfile, resolve_assembly_profile
from .prompt_builder import AssemblyPromptParts, build_assembly_user_prompt
from .template import try_template_assembly

__all__ = [
    "AssemblyProfile",
    "AssemblyPromptParts",
    "PROFILE_MAX_TOKENS",
    "build_assembly_user_prompt",
    "build_citation_patch_prompt",
    "patch_missing_citations",
    "resolve_assembly_profile",
    "try_template_assembly",
]
