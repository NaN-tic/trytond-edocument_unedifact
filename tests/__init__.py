# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
try:
    from trytond.modules.edocument_unedifact.tests.test_edocument_unedifact import suite
except ImportError:
    from .test_edocument_unedifact import suite

__all__ = ['suite']
