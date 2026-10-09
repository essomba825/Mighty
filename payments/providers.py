"""Providers Mobile Money.

Mode par défaut : SIMULATION — les paiements sont marqués réussis immédiatement.
Pour passer en production, implémenter MTNMoMoProvider / OrangeMoneyProvider
avec les API officielles (clés dans les variables d'environnement) et définir
PAYMENT_SIMULATION = False dans les settings."""
import uuid

from django.conf import settings


class SimulatedProvider:
    """Simulation : succès immédiat. Utile en développement et démo."""

    def initiate(self, payment):
        return {'simulated': True, 'message': 'Paiement simulé accepté',
                'transaction_id': f'SIM-{uuid.uuid4().hex[:10].upper()}'}

    def is_success(self, response):
        return True

    def verify(self, payment, code):
        """Simulation : un code SMS d'au moins 4 caractères valide la transaction."""
        return bool(code and len(str(code).strip()) >= 4)


def get_provider(name):
    """Retourne le provider configuré (simulation sauf si clés API présentes)."""
    simulation = getattr(settings, 'PAYMENT_SIMULATION', True)
    if simulation:
        return SimulatedProvider()
    # TODO production : brancher ici MTNMoMoProvider() / OrangeMoneyProvider()
    raise NotImplementedError(f'Provider réel non configuré : {name}')
