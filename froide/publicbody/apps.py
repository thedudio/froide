from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class PublicBodyConfig(AppConfig):
    name = 'froide.publicbody'
    verbose_name = _('Public Body')

    def ready(self):
        from froide.account import account_merged
        from froide.account.export import registry
        from .utils import export_user_data

        registry.register(export_user_data)
        account_merged.connect(merge_user)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from froide.account.utils import move_ownership
    from .models import PublicBody, ProposedPublicBody

    mapping = [
        (PublicBody, '_created_by'),
        (PublicBody, '_updated_by'),
        (ProposedPublicBody, '_created_by'),
        (ProposedPublicBody, '_updated_by'),
    ]

    for model, attr in mapping:
        move_ownership(model, attr, old_user, new_user)
