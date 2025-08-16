"""
Verification package for the node editor.

This package contains all verification-specific logic including:
- Verification scene and workflow models
- Verification workflow generators
- Verification-specific block types

"""

from .model import VerificationScene, VerificationSocket, VerificationEdge
from .workflow import VerificationWorkflowGenerator
from .blocks import PropertyBlock, QueryBlock, WitnessBlock

__all__ = [
    'VerificationScene',
    'VerificationSocket', 
    'VerificationEdge',
    'VerificationWorkflowGenerator',
    'PropertyBlock',
    'QueryBlock',
    'WitnessBlock'
]
