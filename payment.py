# This file is part of account_payment_bank module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['Journal', 'Group', 'Payment', 'PayLine']
__metaclass__ = PoolMeta

_ZERO = Decimal('0.0')


class Journal:
    __name__ = 'account.payment.journal'

    bank_account = fields.Many2One('bank.account', 'Bank Account',
        domain=['OR',
            [('owners', '=', Eval('company'))],
            [('owners', '=', Eval('party'))],
            ],
        depends=['party', 'company'],
        help='It is the bank account of the company or the party.')
    payment_type = fields.Many2One('account.payment.type', 'Payment Type',
        required=True)
    party = fields.Many2One('party.party', 'Party',
        help=('The party who sends the payment order, if it is different from '
        'the company.'))


class Group:
    __name__ = 'account.payment.group'

    payment_type = fields.Function(fields.Many2One('account.payment.type',
            'Payment Type', on_change_with=['journal']),
        'on_change_with_payment_type')
    currency_digits = fields.Function(fields.Integer('Currency Digits',
            on_change_with=['journal']), 'on_change_with_currency_digits')
    amount = fields.Function(fields.Numeric('Total', digits=(16,
                Eval('currency_digits', 2)), depends=['currency_digits']),
        'get_amount')

    def on_change_with_payment_type(self, name=None):
        if self.journal and self.journal.payment_type:
            return self.journal.payment_type.id

    def on_change_with_currency_digits(self, name=None):
        if self.journal and self.journal.currency:
            return self.journal.currency.digits
        return 2

    def get_amount(self, name):
        amount = _ZERO
        for payment in self.payments:
            amount += payment.amount
        if self.journal and self.journal.currency:
            return self.journal.currency.round(amount)
        else:
            return amount


class Payment:
    __name__ = 'account.payment'
    bank_account = fields.Many2One('bank.account', 'Bank Account',
        states={
            'readonly': Eval('state') != 'draft',
            },
        domain=[
            ('owners', '=', Eval('party'))
            ],
        depends=['party', 'kind'])

    @classmethod
    def __setup__(cls):
        super(Payment, cls).__setup__()
        if 'party' not in cls.kind.on_change:
            cls.kind.on_change.append('party')
        if 'kind' not in cls.party.on_change:
            cls.party.on_change.append('kind')
        if 'kind' not in cls.line.on_change:
            cls.line.on_change.append('kind')
        if 'party' not in cls.line.on_change:
            cls.line.on_change.append('party')

    def on_change_kind(self):
        res = super(Payment, self).on_change_kind()
        res['bank_account'] = None
        party = self.party
        if self.kind and party:
            Party = Pool().get('party.party')
            default_bank_account = getattr(Party,
                'get_' + self.kind + '_bank_account')
            res['bank_account'] = default_bank_account(party).id
        return res

    def on_change_party(self):
        res = super(Payment, self).on_change_party()
        res['bank_account'] = None
        party = self.party
        if party and self.kind:
            Party = Pool().get('party.party')
            default_bank_account = getattr(Party,
                'get_' + self.kind + '_bank_account')
            res['bank_account'] = default_bank_account(party).id
        return res

    def on_change_line(self):
        res = super(Payment, self).on_change_line()
        res['bank_account'] = None
        party = self.party
        if self.line and self.line.bank_account:
            res['bank_account'] = self.line.bank_account.id
        elif party and self.kind:
            Party = Pool().get('party.party')
            default_bank_account = getattr(Party,
                'get_' + self.kind + '_bank_account')
            res['bank_account'] = default_bank_account(party).id
        return res


class PayLine:
    __name__ = 'account.move.line.pay'

    def get_payment(self, line):
        payment = super(PayLine, self).get_payment(line)
        payment.bank_account = line.bank_account
        return payment
