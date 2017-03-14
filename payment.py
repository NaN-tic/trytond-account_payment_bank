# This file is part of account_payment_bank module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond import backend
from decimal import Decimal
from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.modules.account_bank.account import BankMixin

__all__ = [
    'Journal',
    'Group',
    'Payment',
    'PayLine'
    ]

_ZERO = Decimal('0.0')


class Journal:
    __metaclass__ = PoolMeta
    __name__ = 'account.payment.journal'

    payment_type = fields.Many2One('account.payment.type', 'Payment Type',
        required=True)
    party = fields.Many2One('party.party', 'Party',
        help=('The party who sends the payment group, if it is different from '
        'the company.'))


class Group:
    __metaclass__ = PoolMeta
    __name__ = 'account.payment.group'

    payment_type = fields.Function(fields.Many2One('account.payment.type',
            'Payment Type'),
        'on_change_with_payment_type')
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'on_change_with_currency_digits')
    amount = fields.Function(fields.Numeric('Total', digits=(16,
                Eval('currency_digits', 2)), depends=['currency_digits']),
        'get_amount')

    @fields.depends('journal')
    def on_change_with_payment_type(self, name=None):
        if self.journal and self.journal.payment_type:
            return self.journal.payment_type.id

    @fields.depends('journal')
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


class Payment(BankMixin):
    __metaclass__ = PoolMeta
    __name__ = 'account.payment'
    _default_payment_type_from = 'party'

    payment_type = fields.Many2One('account.payment.type', 'Payment Type',
        states={
            'readonly': Eval('state') != 'draft',
            },
        depends=['state'])

    @classmethod
    def __setup__(cls):
        super(Payment, cls).__setup__()
        if 'party' not in cls.kind.on_change:
            cls.kind.on_change.add('party')
        if 'kind' not in cls.party.on_change:
            cls.party.on_change.add('kind')
        if 'kind' not in cls.line.on_change:
            cls.line.on_change.add('kind')
        if 'party' not in cls.line.on_change:
            cls.line.on_change.add('party')
        if 'line' not in cls.account_bank_from.on_change_with:
            cls.account_bank_from.on_change_with.add('line')

        readonly = Eval('state') != 'draft'
        previous_readonly = cls.bank_account.states.get('readonly')
        if previous_readonly:
            readonly = readonly | previous_readonly
        cls.bank_account.states.update({
                'readonly': readonly,
                })
        if not 'state' in cls.bank_account.depends:
            cls.bank_account.depends.append('state')

    @classmethod
    def __register__(cls, module_name):
        pool = Pool()
        MoveLine = pool.get('account.move.line')
        TableHandler = backend.get('TableHandler')

        cursor = Transaction().cursor
        table = TableHandler(cursor, cls, module_name)
        sql_table = cls.__table__()
        move_line_table = MoveLine.__table__()

        exist_payment_type = table.column_exist('payment_type')

        super(Payment, cls).__register__(module_name)

        # Migration: copy payment_type from line
        if not exist_payment_type:
            cursor.execute(*sql_table.update(
                    columns=[sql_table.payment_type],
                    values=[move_line_table.payment_type],
                    from_=[move_line_table],
                    where=sql_table.line == move_line_table.id))

    def on_change_kind(self):
        res = super(Payment, self).on_change_kind()
        res['bank_account'] = None
        party = self.party
        if self.kind and party:
            default_bank_account = getattr(party, self.kind + '_bank_account')
            res['bank_account'] = (default_bank_account and
                default_bank_account.id or None)
        return res

    def on_change_party(self):
        res = super(Payment, self).on_change_party()
        res['bank_account'] = None
        party = self.party
        if party and self.kind:
            default_bank_account = getattr(party, self.kind + '_bank_account')
            res['bank_account'] = (default_bank_account and
                default_bank_account.id or None)
        return res

    def on_change_line(self):
        res = super(Payment, self).on_change_line()
        res['bank_account'] = None
        party = self.party
        if self.line and self.line.bank_account:
            res['bank_account'] = self.line.bank_account.id
        elif party and self.kind:
            default_bank_account = getattr(party, self.kind + '_bank_account')
            res['bank_account'] = (default_bank_account and
                default_bank_account.id or None)
        return res

    @classmethod
    def get_sepa_mandates(cls, payments):
        mandates = super(Payment, cls).get_sepa_mandates(payments)
        mandates2 = []
        for payment, mandate in zip(payments, mandates):
            if mandate and payment.bank_account != mandate.account_number.account:
                mandate = None
                for mandate2 in payment.party.sepa_mandates:
                    if (mandate2.is_valid and
                        mandate2.account_number.account == payment.bank_account
                        ):
                        mandate = mandate2
                        break
            mandates2.append(mandate)
        return mandates2


class PayLine:
    __metaclass__ = PoolMeta
    __name__ = 'account.move.line.pay'

    def get_payment(self, line):
        payment = super(PayLine, self).get_payment(line)
        payment.bank_account = line.bank_account
        payment.payment_type = line.payment_type
        return payment
