# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool


def register():
    Pool.register(
        module='edocument_unedifact', type_='model')
