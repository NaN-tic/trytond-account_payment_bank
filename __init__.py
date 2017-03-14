# This file is part of account_payment_bank module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import payment


def register():
    Pool.register(
        payment.Journal,
        payment.Group,
        payment.Payment,
        module='account_payment_bank', type_='model')
    Pool.register(
        payment.PayLine,
        module='account_payment_bank', type_='wizard')
