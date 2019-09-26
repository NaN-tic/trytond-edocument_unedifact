# encoding: utf-8
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime
from edifact.message import Message
from edifact.control import Characters
from edifact.serializer import Serializer
from edifact.utils import (with_segment_check, validate_segment,
    separate_section, RewindIterator, DO_NOTHING, NO_ERRORS)
from trytond.pool import Pool
from trytond.transaction import Transaction
from unidecode import unidecode
import os
import oyaml as yaml
import copy
from io import open

__all__ = ['EdifactMixin', 'EdiTemplate']

UOMS_EDI_TO_TRYTON = {
    'KGM': 'kg',
    'PCE': 'u',
    'LTR': 'l',
    'GRM': 'g',
    'MTR': 'm',
    }

UOMS_TRYTON_TO_EDI = {
    'kg': 'KGM',
    'u': 'PCE',
    'l': 'LTR',
    'g': 'GRM',
    'm': 'MTR',
    }

CM_TYPES = {
    'phone': 'TE',
    'mobile': 'TE',
    'fax': 'FX',
    'email': 'EM'
    }

DATE_FORMAT = '%Y%m%d'
KNOWN_EXTENSIONS = ['.txt', '.edi', '.pla']


class EdifactMixin(object):

    @staticmethod
    def get_datetime_obj_from_edi_date(edi_date):
        return datetime.strptime(edi_date, DATE_FORMAT) if edi_date else None

    def add_attachment(self, attachment, filename=None):
        pool = Pool()
        Attachment = pool.get('ir.attachment')
        if not filename:
            filename = datetime.now().strftime("%y/%m/%d %H:%M:%S")
        attach = Attachment(
            name=filename,
            type='data',
            data=unidecode(attachment),
            resource=str(self))
        attach.save()

    @staticmethod
    def set_control_chars(template_control_chars):
        cc = Characters()
        cc.data_separator = template_control_chars.get('data_separator',
            cc.data_separator)
        cc.segment_terminator = template_control_chars.get(
            'segment_terminator', cc.segment_terminator)
        cc.component_separator = template_control_chars.get(
            'component_separator', cc.component_separator)
        cc.decimal_point = template_control_chars.get('decimal_point',
            cc.decimal_point)
        cc.escape_character = template_control_chars.get('escape_character',
            cc.escape_character)
        cc.reserved_character = template_control_chars.get(
            'reserved_character', cc.reserved_character)
        return cc

    @classmethod
    def process_edi_inputs(cls, source_path, errors_path, template):
        files = [os.path.join(source_path, fp) for fp in
                 os.listdir(source_path) if os.path.isfile(os.path.join(
                     source_path, fp))]
        files_to_delete = []
        to_write = []
        result = []
        for fname in files:
            extension = fname[-4:].lower()
            if extension not in KNOWN_EXTENSIONS:
                continue
            with open(fname, 'r', encoding='utf-8') as fp:
                input = fp.read()
            try:
                record, errors = cls.import_edi_input(input,
                    copy.deepcopy(template.lines))
            except (RuntimeError, AssertionError):
                continue

            basename = os.path.basename(fname)
            record_has_detail = (hasattr(record, 'moves')
                or hasattr(record, 'lines'))
            if record and record_has_detail:
                with Transaction().set_user(0, set_context=True):
                    record.add_attachment(input, basename)
                to_write.extend(([record], record._save_values))
                files_to_delete.append(fname)
            if errors:
                error_fname = os.path.join(
                    errors_path,
                    'error_{}_EDI.log'.format(os.path.splitext(basename)[0]))
                with open(error_fname, 'w') as fp:
                    fp.write('\n'.join(errors))
        if to_write:
            cls.write(*to_write)
            result = to_write[0]
        if files_to_delete:
            for file in files_to_delete:
                os.remove(file)

        return result

    @classmethod
    def import_edi_input(cls, input, template):
        raise NotImplementedError


class EdiTemplate(object):

    def __init__(self, name, path=None, format='yaml'):
        self.name = name
        self.path = path or os.getcwd()
        self.format = format
        self.lines = self.get_content()

    def get_content(self):
        content = None
        if self.format == 'yaml':
            with open(self.path, encoding='utf-8') as fp:
                content = yaml.load(fp.read())
        else:
            # TODO: raise a friendly UserError
            raise NotImplementedError
        return content
