"""
SSH Tunnel Module - Gestión de túneles SSH a AWS

Este módulo contiene herramientas para crear y gestionar túneles SSH:
- aws_tunnel: Cliente para túneles SSH usando AWS Systems Manager
- Scripts shell para automatización de túneles
"""

from .aws_tunnel import AWSSSMTunnel

__all__ = [
    'AWSSSMTunnel'
]
