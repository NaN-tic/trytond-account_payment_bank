# This file is part of the account_payment_bank module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class AccountPaymentBankTestCase(ModuleTestCase):
    'Test Account Payment Bank module'
    module = 'account_payment_bank'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountPaymentBankTestCase))
    return suite